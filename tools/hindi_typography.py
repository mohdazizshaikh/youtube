"""Private Devanagari typography preview, with explicitly pinned font and RAQM shaping.

Standalone visual proof, not an accepted storyboard renderer or publication gate.
"""
from __future__ import annotations
import argparse
import io
import json
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features
from fontTools.ttLib import TTFont, TTLibError
from tools.narration_prepare import pinned, sha, private_root
from tools.narration_qc import private_file
from tools.pilot_run_verify import decode, require

MAX_FONT=24*1024*1024
MAX_REQUEST=32000
SCHEMA="VIRALOS_HINDI_TYPOGRAPHY_REQUEST_V1"


def validate(raw,request_pin,font_pin):
    pinned(raw,request_pin,MAX_REQUEST)
    obj=decode(raw)
    require(type(obj) is dict and set(obj)=={"schema","locale","format","font_sha256",
            "font_rights_attested","license_reference","title","lines"},"REQUEST_FIELDS")
    require(obj["schema"]==SCHEMA and obj["locale"]=="hi-IN"
            and obj["format"] in ("SHORT","LONG"),"REQUEST_SCHEMA")
    require(obj["font_sha256"]==font_pin and obj["font_rights_attested"] is True,"FONT_RIGHTS_PIN")
    license_ref=obj["license_reference"]
    require(type(license_ref) is str and 3<=len(license_ref.strip())<=300
            and all(unicodedata.category(c)[0]!="C" for c in license_ref),"LICENSE_REFERENCE")
    require(type(obj["lines"]) is list and 1<=len(obj["lines"])<=3,"LINE_COUNT")
    for text,limit in [(obj["title"],100),*((x,180) for x in obj["lines"])]:
        require(type(text) is str and 3<=len(text)<=limit and text==text.strip(),"TEXT_LENGTH")
        require(unicodedata.normalize("NFC",text)==text,"TEXT_NFC_REQUIRED")
        require(not any(unicodedata.category(c)[0]=="C" and c not in "\u200c\u200d"
                        or unicodedata.category(c) in {"Zl","Zp"} for c in text),"TEXT_CONTROL")
        require(any("\u0900"<=c<="\u097f" and c.isalpha() for c in text),"DEVANAGARI_REQUIRED")
    return obj


def coverage(font_bytes,texts):
    # Never guess from a fallback glyph. Require a Unicode cmap mapping for
    # each non-space, non-joiner code point and a Devanagari GSUB script table.
    with TTFont(io.BytesIO(font_bytes),lazy=True) as font:
        cmap=font.getBestCmap() or {}
        scripts=set()
        if "GSUB" in font and font["GSUB"].table.ScriptList:
            scripts={r.ScriptTag for r in font["GSUB"].table.ScriptList.ScriptRecord}
        require(bool(scripts & {"deva","dev2"}),"DEVANAGARI_GSUB_REQUIRED")
        missing={ord(c) for text in texts for c in text if not c.isspace()
                 and c not in "\u200c\u200d" and cmap.get(ord(c)) in (None,".notdef")}
        require(not missing,"MISSING_GLYPH")
    return True


def wrap(draw,text,font,width,max_lines):
    rows=[]
    current=""
    for word in text.split():
        require(draw.textlength(word,font=font,language="hi",direction="ltr")<=width,"WORD_OVERFLOW")
        trial=(current+" "+word).strip()
        if current and draw.textlength(trial,font=font,language="hi",direction="ltr")>width:
            rows.append(current)
            current=word
        else:
            current=trial
    rows.append(current)
    require(len(rows)<=max_lines,"LINE_OVERFLOW")
    return rows


def render(font_bytes,font_pin,request,request_pin):
    pinned(font_bytes,font_pin,MAX_FONT)
    data=validate(request,request_pin,font_pin)
    require(features.check_feature("raqm"),"RAQM_REQUIRED")
    coverage(font_bytes,[data["title"],*data["lines"],"हिन्दी दृश्य परीक्षण"])
    w,h=(720,1280) if data["format"]=="SHORT" else (1280,720)
    img=Image.new("RGB",(w,h),"#101e31")
    draw=ImageDraw.Draw(img)
    draw.rectangle((0,0,w,12),fill="#74d9c6")
    margin=48
    y=48
    bounds=[]
    for text,size,limit in [("हिन्दी दृश्य परीक्षण",24,1),(data["title"],42,3),
                            *((t,30,3) for t in data["lines"])]:
        font=ImageFont.truetype(io.BytesIO(font_bytes),size,layout_engine=ImageFont.Layout.RAQM)
        for line in wrap(draw,text,font,w-2*margin,limit):
            box=draw.textbbox((margin,y),line,font=font,language="hi",direction="ltr")
            # Include marks and descenders in the actual pixel safe area.
            require(box[0]>=margin and box[1]>=0 and box[2]<=w-margin and box[3]<=h-100,
                    "GLYPH_BOUNDS")
            draw.text((margin,y),line,font=font,fill="#ecf5ff",language="hi",direction="ltr")
            bounds.append(list(box))
            y=max(y+size+12,box[3]+12)
        y+=18
    draw.rectangle((0,h-64,w,h),fill="#5f2a35")
    # Use Pillow default ASCII font only for explicit warning, never for Hindi.
    draw.text((margin,h-45),"PREVIEW - HUMAN VISUAL REVIEW REQUIRED",fill="white",
              font=ImageFont.load_default(size=18))
    out=io.BytesIO()
    img.save(out,format="PNG")
    raw=out.getvalue()
    return raw,{"schema":"VIRALOS_HINDI_TYPOGRAPHY_PREVIEW_V1","font_sha256":font_pin,
                "request_sha256":request_pin,"png_sha256":sha(raw),"dimensions":[w,h],
                "glyph_bounds":bounds,"raqm_used":True,"cmap_and_gsub_checked":True,
                "font_rights_self_attested":True,"human_visual_review_required":True,
                "native_typography_accepted":False,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("font","request","output"):
        p.add_argument("--"+name,type=Path,required=True)
    for name in ("font","request"):
        p.add_argument("--"+name+"-sha256",required=True)
    args=p.parse_args()
    try:
        require(args.font.suffix.lower() in (".ttf",".otf"),"FONT_EXTENSION")
        raw,report=render(private_file(args.font,MAX_FONT),args.font_sha256,
                          private_file(args.request,MAX_REQUEST),args.request_sha256)
        output=Path(args.output).absolute()
        parent=private_root(output.parent)
        require(output.suffix==".png","OUTPUT_EXTENSION")
        with (parent/output.name).open("xb") as f:
            f.write(raw)
        print(json.dumps(report,indent=2))
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
