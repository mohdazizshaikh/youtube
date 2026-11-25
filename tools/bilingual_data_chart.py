"""Pinned bilingual quantitative chart preview. Not source transcription or fact verification."""
from __future__ import annotations
import argparse
import io
import json
import os
import re
import unicodedata
from datetime import date
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,features
from fontTools.ttLib import TTFont,TTLibError
from tools import hindi_typography as ht,pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file
from tools.bilingual_pilot import json_bytes

DATA="VIRALOS_CHART_DATA_V1"
REQUEST="VIRALOS_BILINGUAL_CHART_REQUEST_V1"
SCHEMA="VIRALOS_BILINGUAL_CHART_PREVIEW_V1"
MAX_SOURCE=16*1024*1024
MAX_JSON=48000
MAX_PNG=8*1024*1024
LANGS=("hindi","english")
COLORS=("#74d9c6","#ffd166","#90b8ff","#ff9eaa","#cbb1ff")
KINDS=("BAR","LINE")


def text_ok(value,limit,lang=None):
    if not (type(value) is str and 1<=len(value)<=limit and value==value.strip()
            and unicodedata.normalize("NFC",value)==value):
        return False
    if any(unicodedata.category(c)[0]=="C" and c not in "\u200c\u200d"
           or unicodedata.category(c) in ("Zl","Zp") for c in value):
        return False
    if lang=="english":
        return value.isascii() and all(32<=ord(c)<=126 for c in value) and any(c.isalpha() for c in value)
    if lang=="hindi":
        return any("\u0900"<=c<="\u097f" and c.isalpha() for c in value)
    return True


def unit_ok(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z%][A-Za-z0-9 %/._-]{0,15}",value) is not None and value==value.strip()


def validate_data(raw,data_pin,source,source_pin):
    pinned(source,source_pin,MAX_SOURCE)
    obj=pv.decode(pinned(raw,data_pin,MAX_JSON))
    pv.require(type(obj) is dict and set(obj)=={"schema","source_sha256","source_reference",
               "as_of","kind","unit","decimals","x_unit","x_decimals","rows"}
               and obj["schema"]==DATA and obj["source_sha256"]==source_pin,"DATA_BINDING")
    pv.require(text_ok(obj["source_reference"],300),"SOURCE_REFERENCE")
    stamp=obj["as_of"]
    pv.require(type(stamp) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}",stamp) is not None,"SOURCE_DATE")
    pv.require(date.fromisoformat(stamp).isoformat()==stamp,"SOURCE_DATE")
    pv.require(obj["kind"] in KINDS and unit_ok(obj["unit"])
               and pv.exact_int(obj["decimals"],0,3),"DATA_UNITS")
    line=obj["kind"]=="LINE"
    pv.require((unit_ok(obj["x_unit"]) and pv.exact_int(obj["x_decimals"],0,3)) if line
               else obj["x_unit"] is None and obj["x_decimals"] is None,"X_UNITS")
    rows=obj["rows"]
    pv.require(type(rows) is list and 3<=len(rows)<=5,"ROW_COUNT")
    for i,row in enumerate(rows,1):
        pv.require(type(row) is dict and set(row)=={"id","value","x"}
                   and type(row["id"]) is int and row["id"]==i
                   and pv.exact_int(row["value"],-999999,999999),"ROW_FIELDS")
        pv.require(pv.exact_int(row["x"],-999999,999999) if line else row["x"] is None,"X_VALUE")
    pv.require(any(row["value"]!=0 for row in rows),"ZERO_RANGE")
    if line:
        pv.require(all(a["x"]<b["x"] for a,b in zip(rows,rows[1:])),"X_ORDER")
    return obj


def validate_request(raw,request_pin,data_pin,font_pins):
    pv.pin(data_pin)
    obj=pv.decode(pinned(raw,request_pin,MAX_JSON))
    pv.require(type(obj) is dict and set(obj)=={"schema","data_sha256","format","languages"}
               and obj["schema"]==REQUEST and obj["data_sha256"]==data_pin
               and obj["format"] in ("SHORT","LONG"),"REQUEST_BINDING")
    pv.require(type(obj["languages"]) is dict and set(obj["languages"])==set(LANGS)
               and type(font_pins) is dict and set(font_pins)==set(LANGS),"LANGUAGES")
    for lang in LANGS:
        row=obj["languages"][lang]
        pv.pin(font_pins[lang])
        pv.require(type(row) is dict and set(row)=={"font_sha256","font_rights_attested",
                   "license_reference","title","labels"} and row["font_sha256"]==font_pins[lang]
                   and row["font_rights_attested"] is True,"FONT_BINDING")
        pv.require(text_ok(row["license_reference"],300) and len(row["license_reference"])>=3,
                   "FONT_LICENSE")
        pv.require(text_ok(row["title"],70,lang),"TITLE")
        labels=row["labels"]
        pv.require(type(labels) is list and 3<=len(labels)<=5 and
                   all(text_ok(x,42,lang) for x in labels),"LABELS")
        pv.require(len({x.casefold() for x in labels})==len(labels),"DUPLICATE_LABELS")
    return obj


def fixed(value,decimals):
    """Display exact fixed-point input, never scientific notation or float rounding."""
    pv.require(pv.exact_int(value,-999999,999999) and pv.exact_int(decimals,0,3),"FIXED_VALUE")
    digits=str(abs(value)).zfill(decimals+1)
    if decimals:digits=digits[:-decimals]+"."+digits[-decimals:]
    return ("-" if value<0 else "")+digits


def geometry(data,fmt):
    pv.require(fmt in ("SHORT","LONG"),"FORMAT")
    short=fmt=="SHORT"
    plot=(126,250,662,670) if short else (122,220,620,570)
    x0,y0,x1,y1=plot
    rows=data["rows"]
    values=[r["value"] for r in rows]
    lo,hi=min(0,min(values)),max(0,max(values))
    if lo<0<hi:
        hi=max(-lo,hi)
        lo=-hi
    pv.require(lo<hi,"ZERO_RANGE")
    y=lambda val:y1-((val-lo)*(y1-y0)+(hi-lo)//2)//(hi-lo)
    zero=y(0)
    if data["kind"]=="BAR":
        step=(x1-x0)//len(rows)
        xs=[x0+step*i+step//2 for i in range(len(rows))]
        points=[[x,y(v)] for x,v in zip(xs,values)]
        width=step//2
        bars=[[x-width//2,min(y(v),zero),x+width//2,max(y(v),zero)]
              for x,v in zip(xs,values)]
        x_range=None
    else:
        low,high=rows[0]["x"],rows[-1]["x"]
        pv.require(low<high,"X_ORDER")
        xs=[x0+((r["x"]-low)*(x1-x0)+(high-low)//2)//(high-low) for r in rows]
        points=[[x,y(v)] for x,v in zip(xs,values)]
        pv.require(all(b-a>=18 for a,b in zip(xs,xs[1:])),"X_POINTS_TOO_CLOSE")
        bars=[]
        x_range=[low,high]
    return {"plot":list(plot),"y_range":[lo,hi],"zero_y":zero,"points":points,
            "bars":bars,"x_range":x_range}


def font_for(raw,pin,lang,texts):
    pinned(raw,pin,ht.MAX_FONT)
    if lang=="hindi":
        pv.require(features.check_feature("raqm"),"RAQM_REQUIRED")
        ht.coverage(raw,texts)
        layout=ImageFont.Layout.RAQM
    else:
        with TTFont(io.BytesIO(raw),lazy=True) as font:
            cmap=font.getBestCmap() or {}
            pv.require(all(c.isspace() or cmap.get(ord(c)) not in (None,".notdef")
                           for t in texts for c in t),"MISSING_GLYPH")
        layout=ImageFont.Layout.BASIC
    return lambda size:ImageFont.truetype(io.BytesIO(raw),size,layout_engine=layout)


def place(draw,text,font,area,*,lang=None,align="center",fill="#ecf5ff"):
    # Fixed bounded single-line label. Reject clipping, do not silently shrink.
    opts={"language":"hi","direction":"ltr"} if lang=="hindi" else {}
    a,b,c,d=area
    x0,y0,x1,y1=draw.textbbox((0,0),text,font=font,**opts)
    w,h=x1-x0,y1-y0
    pv.require(w<=c-a and h<=d-b,"CHART_LABEL_OVERFLOW")
    x=a if align=="left" else c-w if align=="right" else a+(c-a-w)//2
    y=b+(d-b-h)//2
    xy=(x-x0,y-y0)
    box=draw.textbbox(xy,text,font=font,**opts)
    pv.require(a<=box[0]<=box[2]<=c and b<=box[1]<=box[3]<=d,"CHART_GLYPH_BOUNDS")
    draw.text(xy,text,font=font,fill=fill,**opts)
    return list(box)


def render_one(data,request,lang,font,pin):
    spec=request["languages"][lang]
    pv.require(len(spec["labels"])==len(data["rows"]),"LABEL_COUNT")
    make=font_for(font,pin,lang,[spec["title"],*spec["labels"]])
    short=request["format"]=="SHORT"
    w,h=(720,1280) if short else (1280,720)
    im=Image.new("RGB",(w,h),"#101e31")
    draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,w,12),fill="#74d9c6")
    numeric=ImageFont.load_default(size=18)
    small=ImageFont.load_default(size=15)
    g=geometry(data,request["format"])
    x0,y0,x1,y1=g["plot"]
    bounds=[place(draw,spec["title"],make(34),(42,34,w-42,126),lang=lang)]
    bounds.append(place(draw,"Y: "+data["unit"],numeric,(x0,150,x1,190),align="left"))
    if data["kind"]=="LINE":
        bounds.append(place(draw,"X: "+data["x_unit"],numeric,(x0,190,x1,215),align="left"))
    draw.rectangle((x0,y0,x1,y1),outline="#52667e",width=2)
    lo,hi=g["y_range"]
    ticks=[(lo,y1),(hi,y0)]
    if lo<0<hi:ticks.append((0,g["zero_y"]))
    for val,y in ticks:
        draw.line((x0-6,y,x1,y),fill="#52667e",width=1)
        bounds.append(place(draw,fixed(val,data["decimals"]),small,(4,y-12,x0-10,y+12),align="right"))
    draw.line((x0,g["zero_y"],x1,g["zero_y"]),fill="#b4c7dc",width=3)
    if data["kind"]=="BAR":
        for i,box in enumerate(g["bars"]):
            if box[1]==box[3]:
                draw.line((box[0],box[1],box[2],box[3]),fill=COLORS[i],width=3)
            else:draw.rectangle(box,fill=COLORS[i])
            x=g["points"][i][0]
            bounds.append(place(draw,str(i+1),numeric,(x-18,y1+6,x+18,y1+35)))
    else:
        draw.line([tuple(p) for p in g["points"]],fill="#b4c7dc",width=3)
        for i,(x,y) in enumerate(g["points"]):
            draw.ellipse((x-7,y-7,x+7,y+7),fill=COLORS[i],outline="#101e31",width=1)
        a,b=g["x_range"]
        bounds.append(place(draw,fixed(a,data["x_decimals"]),small,(x0-35,y1+6,x0+100,y1+34),align="left"))
        bounds.append(place(draw,fixed(b,data["x_decimals"]),small,(x1-100,y1+6,x1+35,y1+34),align="right"))
    # Exact value table: IDs and colors identify the same plotted values.
    tx,ty,tw,th=(42,740,636,390) if short else (655,178,583,414)
    rh=th//len(data["rows"])
    for i,row in enumerate(data["rows"]):
        top=ty+i*rh
        draw.rounded_rectangle((tx,top,tx+tw,top+rh-6),radius=9,fill="#20374d")
        draw.ellipse((tx+12,top+rh//2-8,tx+28,top+rh//2+8),fill=COLORS[i])
        bounds.append(place(draw,str(row["id"]),small,(tx+33,top+5,tx+52,top+rh-8)))
        bounds.append(place(draw,spec["labels"][i],make(24),(tx+58,top+4,tx+tw-14,top+rh//2),lang=lang,align="left"))
        value="Y "+fixed(row["value"],data["decimals"])+" "+data["unit"]
        if data["kind"]=="LINE":value="X "+fixed(row["x"],data["x_decimals"])+" "+data["x_unit"]+"   |   "+value
        bounds.append(place(draw,value,small,(tx+58,top+rh//2,tx+tw-14,top+rh-8),align="left"))
    bounds.append(place(draw,"Source date: "+data["as_of"],small,(42,h-104,w-42,h-68),align="left"))
    draw.rectangle((0,h-60,w,h),fill="#5f2a35")
    bounds.append(place(draw,"UNVERIFIED DATA - HUMAN REVIEW REQUIRED",numeric,(20,h-52,w-20,h-6)))
    buf=io.BytesIO()
    im.save(buf,format="PNG")
    raw=buf.getvalue()
    return raw,{"png_sha256":sha(raw),"dimensions":[w,h],"glyph_bounds":bounds,
                "geometry":g,"font_sha256":pin,"raqm_used":lang=="hindi",
                "values_preserved_as_declared":True}


def prepare(source,source_pin,data,data_pin,request,request_pin,fonts,font_pins):
    dataset=validate_data(data,data_pin,source,source_pin)
    spec=validate_request(request,request_pin,data_pin,font_pins)
    pv.require(type(fonts) is dict and set(fonts)==set(LANGS),"FONTS")
    outputs,rows={},{}
    for lang in LANGS:
        raw,report=render_one(dataset,spec,lang,fonts[lang],font_pins[lang])
        pv.require(len(raw)<=MAX_PNG,"PNG_SIZE")
        outputs[lang+".png"]=raw
        rows[lang]=report
    pv.require(rows["hindi"]["geometry"]==rows["english"]["geometry"],"GEOMETRY_MISMATCH")
    receipt={"schema":SCHEMA,"source_sha256":source_pin,"data_sha256":data_pin,
             "request_sha256":request_pin,"source_reference":dataset["source_reference"],
             "as_of":dataset["as_of"],"kind":dataset["kind"],"format":spec["format"],
             "languages":rows,"font_rights_self_attested":True,"source_transcription_verified":False,
             "source_truth_verified":False,"translation_verified":False,
             "human_visual_review_required":True,"publication_eligible":False}
    outputs["chart.json"]=json_bytes(receipt)
    return outputs


def build(inputs,output):
    outputs=prepare(*inputs)
    output=Path(output).absolute()
    output=ps.local_dir(output.parent)/output.name
    pv.require(not output.exists() and not output.is_symlink(),"DESTINATION_EXISTS")
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    for name,raw in outputs.items():
        with (output/name).open("xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        pv.require(pv.read(output/name,len(raw))==raw,"OUTPUT_BYTES")
    marker.unlink()
    return {"chart_sha256":sha(outputs["chart.json"]),"publication_eligible":False}


def verify(inputs,output,chart_pin):
    root=ps.local_dir(output)
    pv.require({p.name for p in root.iterdir()}=={"hindi.png","english.png","chart.json"},"CHART_INVENTORY")
    raw=pinned(pv.read(root/"chart.json",MAX_JSON),chart_pin,MAX_JSON)
    expected=prepare(*inputs)
    pv.require(raw==expected["chart.json"],"CHART_RECEIPT")
    for name,data in expected.items():
        pv.require(pv.read(root/name,len(data))==data,"CHART_BYTES")
    return {"chart_sha256":chart_pin,"deterministic_rerender_verified":True,
            "publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("source","data","request","hindi-font","english-font"):
            a.add_argument("--"+name,type=Path,required=True)
            a.add_argument("--"+name+"-sha256",required=True)
        a.add_argument("--output",type=Path,required=True)
        if mode=="verify":a.add_argument("--chart-sha256",required=True)
    a=p.parse_args()
    try:
        fonts={l:private_file(getattr(a,l+"_font"),ht.MAX_FONT) for l in LANGS}
        pins={l:getattr(a,l+"_font_sha256") for l in LANGS}
        inputs=(private_file(a.source,MAX_SOURCE),a.source_sha256,private_file(a.data,MAX_JSON),
                a.data_sha256,private_file(a.request,MAX_JSON),a.request_sha256,fonts,pins)
        result=build(inputs,a.output) if a.mode=="build" else verify(inputs,a.output,a.chart_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
