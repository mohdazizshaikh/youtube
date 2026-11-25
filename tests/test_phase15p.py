import io
import os
from pathlib import Path
import pytest
from PIL import Image,features
from tools import bilingual_data_chart as c

SOURCE=b"owner synthetic source fixture"
SP=c.sha(SOURCE)
FONTS={"hindi":b"hi fixture","english":b"en fixture"}
PINS={l:c.sha(v) for l,v in FONTS.items()}


def data(kind="BAR"):
    return {"schema":c.DATA,"source_sha256":SP,"source_reference":"synthetic example",
            "as_of":"2026-11-26","kind":kind,"unit":"kg","decimals":2,
            "x_unit":"s" if kind=="LINE" else None,"x_decimals":1 if kind=="LINE" else None,
            "rows":[{"id":i,"value":v,"x":x if kind=="LINE" else None}
                    for i,(v,x) in enumerate([(-125,0),(0,15),(250,40)],1)]}


def check(obj):
    raw=c.json_bytes(obj)
    return c.validate_data(raw,c.sha(raw),SOURCE,SP)


def request(dp,pins=PINS,fmt="SHORT"):
    return {"schema":c.REQUEST,"data_sha256":dp,"format":fmt,"languages":{
        "hindi":{"font_sha256":pins["hindi"],"font_rights_attested":True,
            "license_reference":"owner license","title":"मापन परिणाम","labels":["पहला नमूना","दूसरा नमूना","तीसरा नमूना"]},
        "english":{"font_sha256":pins["english"],"font_rights_attested":True,
            "license_reference":"owner license","title":"Measurement results","labels":["First sample","Second sample","Third sample"]}}}


@pytest.mark.parametrize("kind",c.KINDS)
def test_data_valid(kind):
    assert check(data(kind))==data(kind)


@pytest.mark.parametrize("field,value",[
    ("schema","bad"),("source_sha256","0"*64),("source_reference",""),("source_reference",None),
    ("source_reference","a"*301),("source_reference","x\u202e"),("as_of","2026-02-30"),
    ("as_of","2026-1-1"),("as_of",True),("kind","PIE"),("unit",""),("unit","₹"),
    ("unit"," kg"),("decimals",True),("decimals",-1),("decimals",4),
    ("x_unit","s"),("x_decimals",0),("rows",[]),("rows",{}),("rows",None),("extra",1)])
def test_data_fields(field,value):
    obj=data()
    obj[field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("field,value",[("id",0),("id",True),("id",1.0),("id",2),
    ("value",True),("value",1.0),("value",1000000),("value",-1000000),("value","1"),
    ("value",None),("x",0),("extra",True)])
def test_row_fields(field,value):
    obj=data()
    obj["rows"][0][field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("value",[0,-1,True,1.0,None])
def test_line_x(value):
    obj=data("LINE")
    obj["rows"][1]["x"]=value
    with pytest.raises(ValueError):check(obj)


def test_zero_range():
    obj=data()
    for row in obj["rows"]:row["value"]=0
    with pytest.raises(ValueError,match="ZERO_RANGE"):check(obj)


def test_source_pin():
    raw=c.json_bytes(data())
    with pytest.raises(ValueError,match="INPUT_PIN"):
        c.validate_data(raw,c.sha(raw),b"changed",SP)


@pytest.mark.parametrize("value,decimals,expected",[(0,0,"0"),(0,3,"0.000"),(-1,3,"-0.001"),
    (-125,2,"-1.25"),(250,2,"2.50"),(999999,3,"999.999"),(-999999,0,"-999999")])
def test_fixed(value,decimals,expected):
    assert c.fixed(value,decimals)==expected


@pytest.mark.parametrize("fmt",["SHORT","LONG"])
@pytest.mark.parametrize("kind",c.KINDS)
def test_geometry(fmt,kind):
    g=c.geometry(data(kind),fmt)
    assert g["y_range"]==[-250,250]
    assert g["points"][0][1]>g["zero_y"]==g["points"][1][1]>g["points"][2][1]
    if kind=="BAR":
        assert g["bars"][0][1]==g["zero_y"]==g["bars"][2][3]
    else:
        a,b,d=[p[0] for p in g["points"]]
        assert abs((b-a)/(d-a)-.375)<.005


@pytest.mark.parametrize("fmt",["SHORT","LONG"])
def test_close_points(fmt):
    obj=data("LINE")
    obj["rows"][1]["x"]=1
    obj["rows"][2]["x"]=999999
    with pytest.raises(ValueError,match="X_POINTS_TOO_CLOSE"):c.geometry(obj,fmt)


@pytest.mark.parametrize("lang",c.LANGS)
@pytest.mark.parametrize("field,value",[("font_sha256","0"*64),("font_rights_attested",1),
    ("font_rights_attested",False),("license_reference",""),("title",""),
    ("title","bad\u202e"),("labels",[]),("labels",None),("extra",1)])
def test_request_language(lang,field,value):
    dp=c.sha(c.json_bytes(data()))
    obj=request(dp)
    obj["languages"][lang][field]=value
    raw=c.json_bytes(obj)
    with pytest.raises(ValueError):c.validate_request(raw,c.sha(raw),dp,PINS)


@pytest.mark.parametrize("lang",c.LANGS)
def test_duplicate_label(lang):
    dp=c.sha(c.json_bytes(data()))
    obj=request(dp)
    labels=obj["languages"][lang]["labels"]
    labels[1]=labels[0]
    raw=c.json_bytes(obj)
    with pytest.raises(ValueError,match="DUPLICATE_LABELS"):
        c.validate_request(raw,c.sha(raw),dp,PINS)


@pytest.mark.parametrize("fmt",["SHORT","LONG"])
@pytest.mark.parametrize("kind",c.KINDS)
def test_real_chart(fmt,kind,tmp_path):
    hi=Path(os.environ.get("VIRALOS_CI_HINDI_FONT","/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"))
    en=Path(os.environ.get("VIRALOS_CI_ENGLISH_FONT","/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"))
    if not hi.is_file() or not en.is_file() or not features.check_feature("raqm"):
        if os.environ.get("VIRALOS_REQUIRE_HINDI_PREVIEW")=="1":
            pytest.fail("required chart fonts or RAQM missing")
        pytest.skip("owner fonts and RAQM required")
    fonts={"hindi":hi.read_bytes(),"english":en.read_bytes()}
    pins={l:c.sha(v) for l,v in fonts.items()}
    raw=c.json_bytes(data(kind))
    req=c.json_bytes(request(c.sha(raw),pins,fmt))
    inputs=(SOURCE,SP,raw,c.sha(raw),req,c.sha(req),fonts,pins)
    dest=tmp_path/"chart"
    report=c.build(inputs,dest)
    check=c.verify(inputs,dest,report["chart_sha256"])
    assert check["deterministic_rerender_verified"] and not check["publication_eligible"]
    receipt=c.pv.document(dest/"chart.json")
    assert receipt["languages"]["hindi"]["geometry"]==receipt["languages"]["english"]["geometry"]
    assert not receipt["source_transcription_verified"]
    for lang in c.LANGS:
        png=(dest/(lang+".png")).read_bytes()
        dims=(720,1280) if fmt=="SHORT" else (1280,720)
        assert Image.open(io.BytesIO(png)).size==dims
        assert c.sha(png)==receipt["languages"][lang]["png_sha256"]
    with pytest.raises(ValueError):c.build(inputs,dest)
    (dest/"english.png").write_bytes(b"tampered")
    with pytest.raises(ValueError):c.verify(inputs,dest,report["chart_sha256"])


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="CHART_INVENTORY"):c.verify((),tmp_path,"0"*64)
