"""Owner-local Devanagari three-step flow diagram preview; no factual certification."""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, features
from fontTools.ttLib import TTLibError
from tools import hindi_typography as ht, pilot_run_verify as pv
from tools.narration_prepare import pinned, sha, private_root
from tools.narration_qc import private_file

SCHEMA="VIRALOS_NATIVE_FLOW_DIAGRAM_REQUEST_V1"
MAX_REQUEST=32000


def validate(raw,request_pin,font_pin):
    pv.pin(font_pin)
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","locale","format","font_sha256",
                "font_rights_attested","license_reference","title","nodes","source_declaration_sha256"}
                and obj["schema"]==SCHEMA,"DIAGRAM_FIELDS")
    pv.pin(obj["source_declaration_sha256"])
    pv.require(type(obj["nodes"]) is list and len(obj["nodes"])==3,"NODE_COUNT")
    labels=[]
    for i,row in enumerate(obj["nodes"],1):
        pv.require(type(row) is dict and set(row)=={"step","label"}
                   and type(row["step"]) is int and row["step"]==i,"NODE_ORDER")
        label=row["label"]
        pv.require(type(label) is str and 3<=len(label)<=48,"NODE_LABEL")
        labels.append(label)
    pv.require(len(set(labels))==3,"DUPLICATE_LABEL")
    base={k:obj[k] for k in ("locale","format","font_sha256","font_rights_attested",
                            "license_reference","title")}
    base.update(schema=ht.SCHEMA,lines=labels)
    req=json.dumps(base,ensure_ascii=False).encode()
    ht.validate(req,sha(req),font_pin)
    return obj


def label(draw,text,font,area,max_lines,fill):
    x0,y0,x1,y1=area
    lines=ht.wrap(draw,text,font,x1-x0-20,max_lines)
    # Shape each row, then center the real pixel bounds, including marks.
    boxes=[draw.textbbox((0,0),line,font=font,language="hi",direction="ltr") for line in lines]
    heights=[b[3]-b[1] for b in boxes]
    total=sum(heights)+10*(len(lines)-1)
    pv.require(total<=y1-y0-16,"LABEL_HEIGHT")
    y=y0+(y1-y0-total)//2
    actual=[]
    for line,b,height in zip(lines,boxes,heights):
        w=b[2]-b[0]
        x=x0+(x1-x0-w)//2
        xy=(x-b[0],y-b[1])
        bound=draw.textbbox(xy,line,font=font,language="hi",direction="ltr")
        pv.require(x0<=bound[0]<=bound[2]<=x1 and y0<=bound[1]<=bound[3]<=y1,"GLYPH_BOUNDS")
        draw.text(xy,line,font=font,language="hi",direction="ltr",fill=fill)
        actual.append(list(bound))
        y+=height+10
    return actual


def render(font,font_pin,request,request_pin):
    pinned(font,font_pin,ht.MAX_FONT)
    obj=validate(request,request_pin,font_pin)
    pv.require(features.check_feature("raqm"),"RAQM_REQUIRED")
    texts=[obj["title"],*[r["label"] for r in obj["nodes"]]]
    ht.coverage(font,texts)
    short=obj["format"]=="SHORT"
    w,h=(720,1280) if short else (1280,720)
    im=Image.new("RGB",(w,h),"#101e31")
    draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,w,12),fill="#74d9c6")
    font_for=lambda size:ImageFont.truetype(io.BytesIO(font),size,layout_engine=ImageFont.Layout.RAQM)
    title_area=(48,42,w-48,190)
    title_bounds=label(draw,obj["title"],font_for(40),title_area,2,"#ecf5ff")
    areas=([(84,240+i*290,636,440+i*290) for i in range(3)] if short else
           [(48+i*408,250,416+i*408,500) for i in range(3)])
    bounds=[]
    for i,(row,area) in enumerate(zip(obj["nodes"],areas)):
        draw.rounded_rectangle(area,radius=22,fill="#20374d",outline="#74d9c6",width=3)
        bounds.append(label(draw,row["label"],font_for(34 if short else 30),area,3,"#ecf5ff"))
        if i==2:continue
        x0,y0,x1,y1=area
        nx0,ny0,_,_=areas[i+1]
        if short:
            cx=(x0+x1)//2
            draw.line((cx,y1+12,cx,ny0-26),fill="#74d9c6",width=6)
            draw.polygon([(cx-12,ny0-30),(cx+12,ny0-30),(cx,ny0-10)],fill="#74d9c6")
        else:
            cy=(y0+y1)//2
            draw.line((x1+4,cy,nx0-13,cy),fill="#74d9c6",width=4)
            draw.polygon([(nx0-15,cy-9),(nx0-15,cy+9),(nx0-3,cy)],fill="#74d9c6")
    draw.rectangle((0,h-64,w,h),fill="#5f2a35")
    draw.text((48,h-45),"PREVIEW - HUMAN VISUAL REVIEW REQUIRED",fill="white",
              font=ImageFont.load_default(size=18))
    out=io.BytesIO()
    im.save(out,format="PNG")
    raw=out.getvalue()
    return raw,{"schema":"VIRALOS_NATIVE_FLOW_DIAGRAM_PREVIEW_V1","request_sha256":request_pin,
                "font_sha256":font_pin,"source_declaration_sha256":obj["source_declaration_sha256"],
                "png_sha256":sha(raw),"dimensions":[w,h],"node_boxes":[list(x) for x in areas],
                "title_glyph_bounds":title_bounds,"node_glyph_bounds":bounds,
                "layout":"VERTICAL" if short else "HORIZONTAL","raqm_used":True,
                "font_rights_self_attested":True,"human_visual_review_required":True,
                "source_truth_verified":False,"native_visual_accepted":False,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("font","request","output"):p.add_argument("--"+name,type=Path,required=True)
    for name in ("font","request"):p.add_argument("--"+name+"-sha256",required=True)
    a=p.parse_args()
    try:
        pv.require(a.font.suffix.lower() in (".ttf",".otf") and a.output.suffix==".png","EXTENSION")
        raw,report=render(private_file(a.font,ht.MAX_FONT),a.font_sha256,
                          private_file(a.request,MAX_REQUEST),a.request_sha256)
        target=private_root(a.output.absolute().parent)/a.output.name
        with target.open("xb") as f:f.write(raw)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(report,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
