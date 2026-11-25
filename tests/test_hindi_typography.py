import io
import json
import os
from pathlib import Path
import unicodedata
import pytest
from PIL import Image, features
from tools import hindi_typography as h

FONT=b"owner font fixture"
PIN=h.sha(FONT)


def request():
    return {"schema":h.SCHEMA,"locale":"hi-IN","format":"SHORT","font_sha256":PIN,
            "font_rights_attested":True,"license_reference":"owner declaration",
            "title":"हिन्दी दृश्य परीक्षण","lines":["यह एक परीक्षण है"]}


def check(obj):
    raw=json.dumps(obj,ensure_ascii=False).encode()
    return h.validate(raw,h.sha(raw),PIN)


@pytest.mark.parametrize("field,value",[
    ("schema","bad"),("locale","en-IN"),("format","OTHER"),("font_sha256","0"*64),
    ("font_rights_attested",False),("font_rights_attested",1),("font_rights_attested","yes"),
    ("license_reference",""),("license_reference","ab"),("license_reference","a"*301),
    ("license_reference","abc\nxyz"),("license_reference",None),("extra",1),
    ("lines",[]),("lines",None),("lines","हिन्दी"),("lines",["हिन्दी"]*4),
    ("title","English title"),("title",""),("title"," हिंदी"),("title","हिंदी "),
    ("title","हिन्दी\nपरीक्षण"),("title","हिन्दी\u202eपरीक्षण"),
    ("title","हिन्दी\u2028परीक्षण"),("title","हिन्दी\u2029परीक्षण"),
    ("title","हिन्दी"*30),("title",True),("title",None),
    ("lines",["हिन्दी"*40]),("lines",[None]),("lines",["English"]),
])
def test_reject(field,value):
    obj=request()
    obj[field]=value
    with pytest.raises(ValueError):
        check(obj)


@pytest.mark.parametrize("fmt",["SHORT","LONG"])
def test_valid(fmt):
    obj=request()
    obj["format"]=fmt
    assert check(obj)==obj


@pytest.mark.parametrize("pin",["","0"*64,"A"*64,"x"*64])
def test_request_pin(pin):
    raw=json.dumps(request()).encode()
    with pytest.raises(ValueError):
        h.validate(raw,pin,PIN)


def test_raqm_required(monkeypatch):
    raw=json.dumps(request()).encode()
    monkeypatch.setattr(h.features,"check_feature",lambda name:False)
    with pytest.raises(ValueError,match="RAQM_REQUIRED"):
        h.render(FONT,PIN,raw,h.sha(raw))


def test_font_pin():
    raw=json.dumps(request()).encode()
    with pytest.raises(ValueError,match="INPUT_PIN"):
        h.render(FONT,"0"*64,raw,h.sha(raw))


@pytest.mark.parametrize("fmt,dims",[("SHORT",(720,1280)),("LONG",(1280,720))])
def test_real_font_preview(fmt,dims):
    font=Path(os.environ.get("VIRALOS_CI_HINDI_FONT","/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"))
    required=os.environ.get("VIRALOS_REQUIRE_HINDI_PREVIEW")=="1"
    if not font.is_file() or not features.check_feature("raqm"):
        if required:
            pytest.fail("required CI Devanagari font or RAQM missing")
        pytest.skip("local Devanagari font and RAQM needed")
    data=font.read_bytes()
    obj=request()
    obj.update(format=fmt,font_sha256=h.sha(data))
    raw=json.dumps(obj,ensure_ascii=False).encode()
    png,report=h.render(data,h.sha(data),raw,h.sha(raw))
    assert Image.open(io.BytesIO(png)).size==dims
    assert report["raqm_used"] and report["cmap_and_gsub_checked"]
    assert report["png_sha256"]==h.sha(png)
    assert not report["native_typography_accepted"]
    assert not report["publication_eligible"]
