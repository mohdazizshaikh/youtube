import io
import json
import os
from pathlib import Path
import pytest
from PIL import Image,features
from tools import paired_mix_snapshot as s,native_flow_diagram as d

PIN="a"*64
FONT=b"fixture"
FP=d.sha(FONT)


def receipt():
    return s.pm.receipt(PIN,None,"b"*64,4000,{
        l:{"mix_sha256":("c" if l=="hindi" else "d")*64,
           "manifest_sha256":("e" if l=="hindi" else "f")*64,
           "video_sha256":("1" if l=="hindi" else "2")*64,"duration_ms":4000}
        for l in s.LANGS})


def rec(obj):
    raw=json.dumps(obj).encode()
    return s.pair_records(raw,s.sha(raw))


@pytest.mark.parametrize("field,value",[
    ("schema","bad"),("pair_sha256","bad"),("native_sha256","bad"),("request_sha256",None),
    ("duration_ms",2999),("duration_ms",4001),("duration_ms",True),("duration_ms",120040),
    ("tracks",None),("tracks",{}),("tracks",[]),("human_listening_required",False),
    ("translation_verified",True),("human_review_verified",True),("publication_eligible",True),
    ("extra",1)])
def test_pair_fields(field,value):
    obj=receipt()
    obj[field]=value
    with pytest.raises(ValueError):rec(obj)


@pytest.mark.parametrize("field,value",[("mix_sha256","d"*64),("manifest_sha256","f"*64),
    ("video_sha256","bad"),("duration_ms",3999),("duration_ms",4000.0),("extra",1)])
def test_pair_track(field,value):
    obj=receipt()
    obj["tracks"]["hindi"][field]=value
    with pytest.raises(ValueError):rec(obj)


def test_receipt():
    assert rec(receipt())==receipt()


def test_track_binding():
    row=receipt()["tracks"]["hindi"]
    obj={"schema":s.pm.pm.SCHEMA,"publication_eligible":False,
         "manifest_sha256":row["manifest_sha256"],"video_sha256":row["video_sha256"],
         "duration_ms":4000}
    raw=json.dumps(obj).encode()
    assert s.track_record(raw,{**row,"mix_sha256":s.sha(raw)})==obj
    obj["duration_ms"]=3999
    raw=json.dumps(obj).encode()
    with pytest.raises(ValueError,match="TRACK_BINDING"):
        s.track_record(raw,{**row,"mix_sha256":s.sha(raw)})


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="SNAPSHOT_INVENTORY"):
        s.inspect(tmp_path,PIN,PIN)


def diagram():
    return {"schema":d.SCHEMA,"locale":"hi-IN","format":"SHORT","font_sha256":FP,
            "font_rights_attested":True,"license_reference":"owner declaration",
            "source_declaration_sha256":PIN,"title":"ज्ञान की प्रक्रिया",
            "nodes":[{"step":i,"label":t} for i,t in enumerate(
                ["जानकारी एकत्र करें","तथ्य जाँच करें","परिणाम समझाएँ"],1)]}


def validate(obj):
    raw=json.dumps(obj,ensure_ascii=False).encode()
    return d.validate(raw,d.sha(raw),FP)


@pytest.mark.parametrize("field,value",[
    ("schema","bad"),("locale","en-IN"),("format","OTHER"),("font_sha256",PIN),
    ("font_rights_attested",False),("font_rights_attested",1),("license_reference",""),
    ("source_declaration_sha256","bad"),("title","English"),("title","हिन्दी\nशीर्षक"),
    ("nodes",[]),("nodes",None),("nodes",{}),("extra",1)])
def test_diagram_fields(field,value):
    obj=diagram()
    obj[field]=value
    with pytest.raises(ValueError):validate(obj)


@pytest.mark.parametrize("field,value",[
    ("step",0),("step",True),("step",1.0),("step",2),("label",""),
    ("label","English"),("label","हिन्दी"*20),("label","हिन्दी\u202eलेख"),
    ("label",None),("extra",1)])
def test_diagram_node(field,value):
    obj=diagram()
    obj["nodes"][0][field]=value
    with pytest.raises(ValueError):validate(obj)


def test_duplicate_label():
    obj=diagram()
    obj["nodes"][1]["label"]=obj["nodes"][0]["label"]
    with pytest.raises(ValueError,match="DUPLICATE_LABEL"):validate(obj)


def test_diagram_valid():
    assert validate(diagram())==diagram()


@pytest.mark.parametrize("fmt,dims",[("SHORT",(720,1280)),("LONG",(1280,720))])
def test_real_diagram(fmt,dims):
    font=Path(os.environ.get("VIRALOS_CI_HINDI_FONT","/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"))
    if not font.is_file() or not features.check_feature("raqm"):
        if os.environ.get("VIRALOS_REQUIRE_HINDI_PREVIEW")=="1":pytest.fail("required font or RAQM missing")
        pytest.skip("local font and RAQM required")
    raw_font=font.read_bytes()
    obj=diagram()
    obj.update(format=fmt,font_sha256=d.sha(raw_font))
    raw=json.dumps(obj,ensure_ascii=False).encode()
    png,report=d.render(raw_font,d.sha(raw_font),raw,d.sha(raw))
    assert Image.open(io.BytesIO(png)).size==dims
    assert report["png_sha256"]==d.sha(png)
    assert not report["publication_eligible"] and not report["native_visual_accepted"]
    for area,bounds in zip(report["node_boxes"],report["node_glyph_bounds"]):
        for box in bounds:
            assert area[0]<=box[0]<=box[2]<=area[2] and area[1]<=box[1]<=box[3]<=area[3]
    assert d.render(raw_font,d.sha(raw_font),raw,d.sha(raw))[0]==png
