"""Paired pilot input contracts, receipt binding, and a real synthetic CPU render."""
import copy
import json
import shutil
import pytest

from tools import bilingual_pilot as p
from tools import bilingual_compose as b
from tools.domain_storyboard import demo_spec
from test_bilingual_compose import inputs, args, save


@pytest.fixture
def pair_inputs(inputs,tmp_path):
    saved = save(inputs)
    root,req,rp,cap,cp = args(inputs)
    bundle = inputs[3]
    rows=[]
    for i in (1,2):
        h=demo_spec("technology","SHORT").model_dump()
        e=copy.deepcopy(h)
        h["title"]="Hindi narration draft"
        e["title"]="English narration draft"
        rows.append({"scene":i,"hindi":h,"english":e,"rights_attested":{"hindi":True,"english":True}})
    data={"schema":p.BOARD_SCHEMA,"bundle_manifest_sha256":saved["manifest_sha256"],"scenes":rows}
    return (root,req,rp,cap,cp,bundle,saved["manifest_sha256"]),data,tmp_path/"pair"


def values(pair_inputs):
    a,data,out=pair_inputs
    raw=p.json_bytes(data)
    return (*a,raw,p.sha(raw),out)


def prepare(pair_inputs):
    return p.prepare(*values(pair_inputs)[:-1])


def test_plans(pair_inputs):
    outputs,audio,plans=prepare(pair_inputs)
    assert len(plans["hindi"].scenes)==len(plans["english"].scenes)==2
    assert plans["hindi"].scenes[0].narration_text=="यह एक परीक्षण है"
    assert plans["english"].scenes[0].narration_text=="This is a test"
    assert plans["hindi"].scenes[0].narration_sha256==p.sha(outputs["hindi_01.wav"])
    assert audio["duration_ms"]==2080


@pytest.mark.parametrize("field,value",[
    ("schema","wrong"),("bundle_manifest_sha256","0"*64),("scenes",None),
    ("scenes",[]),("scenes",{}),("extra",True)])
def test_bad_request(pair_inputs,field,value):
    pair_inputs[1][field]=value
    with pytest.raises(ValueError):
        prepare(pair_inputs)


@pytest.mark.parametrize("field,value",[
    ("scene",0),("scene",2),("scene",True),("scene",1.0),("extra",1),
    ("rights_attested",True),("rights_attested",None),("rights_attested",{}),
    ("rights_attested",{"hindi":False,"english":True}),
    ("rights_attested",{"hindi":True,"english":1}),
    ("rights_attested",{"hindi":True,"english":True,"extra":True}),
    ("hindi",None),("english",[])])
def test_bad_row(pair_inputs,field,value):
    pair_inputs[1]["scenes"][0][field]=value
    with pytest.raises(ValueError):
        prepare(pair_inputs)


@pytest.mark.parametrize("field,value",[
    ("synthetic_demo","true"),("synthetic_demo",1),("synthetic_demo",None),
    ("format","LONG"),("format","OTHER"),("domain","unknown"),
    ("title","हिंदी शीर्षक"),("title","x"),("title","x"*63),
    ("claims",[]),("sources",[]),("specialist_facts",{}),("extra",1)])
def test_bad_board(pair_inputs,field,value):
    pair_inputs[1]["scenes"][0]["hindi"][field]=value
    with pytest.raises(ValueError):
        prepare(pair_inputs)


@pytest.mark.parametrize("language",["hindi","english"])
def test_source_change(pair_inputs,language):
    pair_inputs[1]["scenes"][0][language]["sources"][0]["publisher"]="Different publisher"
    with pytest.raises(ValueError,match="PAIR_SOURCE_DECLARATIONS"):
        prepare(pair_inputs)


def test_link_change(pair_inputs):
    pair_inputs[1]["scenes"][0]["hindi"]["claims"][0]["links"][0]["locator"]="different locator"
    with pytest.raises(ValueError,match="PAIR_CLAIM_LINKS"):
        prepare(pair_inputs)


def test_missing_demo_flag(pair_inputs):
    del pair_inputs[1]["scenes"][0]["hindi"]["synthetic_demo"]
    with pytest.raises(ValueError,match="BOARD_DEMO_TYPE"):
        prepare(pair_inputs)


@pytest.mark.parametrize("name",["hindi.wav","english.wav","hindi.vtt","english.vtt",
    "hindi_01.wav","english_01.wav","hindi_02.wav","english_02.wav","manifest.json"])
def test_bundle_changed(pair_inputs,name):
    path=pair_inputs[0][5]/name
    path.write_bytes(b"tamper")
    with pytest.raises(ValueError):
        prepare(pair_inputs)


@pytest.mark.parametrize("bad",["","0"*64,"A"*64,"x"*64])
def test_board_pin(pair_inputs,bad):
    a,data,out=pair_inputs
    with pytest.raises(ValueError):
        p.prepare(*a,p.json_bytes(data),bad)


def test_existing_output(pair_inputs):
    pair_inputs[2].mkdir()
    with pytest.raises(ValueError,match="OUTPUT_EXISTS"):
        p.build(*values(pair_inputs))


def test_input_output_overlap(pair_inputs):
    v=values(pair_inputs)
    with pytest.raises(ValueError,match="OVERLAPPING_OUTPUT"):
        p.build(*v[:-1],pair_inputs[0][0]/"nested")


def test_bundle_output_overlap(pair_inputs):
    v=values(pair_inputs)
    with pytest.raises(ValueError,match="OVERLAPPING_OUTPUT"):
        p.build(*v[:-1],pair_inputs[0][5]/"nested")


def test_incomplete_pair_refused(pair_inputs):
    out=pair_inputs[2]
    out.mkdir()
    (out/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="PAIR_INVENTORY"):
        p.verify(*values(pair_inputs),"0"*64)


def test_invalid_plan_no_output(pair_inputs):
    pair_inputs[1]["schema"]="bad"
    with pytest.raises(ValueError):
        p.build(*values(pair_inputs))
    assert not pair_inputs[2].exists()


def test_missing_tools_no_output(pair_inputs,monkeypatch):
    monkeypatch.setattr(p.shutil,"which",lambda name:None)
    with pytest.raises(ValueError,match="LOCAL_MEDIA_TOOLS_REQUIRED"):
        p.build(*values(pair_inputs))
    assert not pair_inputs[2].exists()


def test_failed_render_marker(pair_inputs,monkeypatch):
    monkeypatch.setattr(p.shutil,"which",lambda name:name)
    def fail(*args,**kwargs):
        raise RuntimeError("simulated render failure")
    monkeypatch.setattr(p.pp,"build",fail)
    with pytest.raises(RuntimeError):
        p.build(*values(pair_inputs))
    assert (pair_inputs[2]/"INCOMPLETE").exists()
    assert not (pair_inputs[2]/"pair.json").exists()


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="real local FFmpeg and ffprobe required")
def test_real_bilingual_pilot(pair_inputs):
    v=values(pair_inputs)
    r=p.build(*v)
    assert r["duration_ms"]==2080 and not r["publication_eligible"]
    out=pair_inputs[2]
    for lang in p.LANGS:
        assert (out/lang/"draft"/"draft.mp4").stat().st_size>0
        assert (out/lang/"reviews.sqlite").is_file()
    verified=p.verify(*v,r["pair_sha256"])
    assert verified["fresh_media_audit"]
    assert all(x=={"revision":0,"state":"PENDING"} for x in verified["review_states"].values())
    assert not verified["human_review_verified"]
    assert not verified["publication_eligible"]
    with pytest.raises(ValueError):
        p.verify(*v,"0"*64)
    (out/"extra").touch()
    with pytest.raises(ValueError,match="PAIR_INVENTORY"):
        p.verify(*v,r["pair_sha256"])
