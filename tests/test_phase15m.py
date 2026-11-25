import json
import re
import pytest
from fastapi.testclient import TestClient
from tools import native_hindi_pilot as n, mixed_review_dashboard as m
from tools import bilingual_review_dashboard as dash, bilingual_pilot as p
from test_native_hindi_pilot import plan, request, PAIR, FONT


def flow_req():
    obj=request()
    obj["schema"]=n.FLOW_REQUEST
    for row,scene in zip(obj["scenes"],plan().scenes):
        del row["claims"]
        row["source_declaration_sha256"]=n.sha(json.dumps(scene.board.model_dump(),sort_keys=True,ensure_ascii=False).encode())
        row["nodes"]=[{"step":1,"label":"जानकारी एकत्र करें"},{"step":2,"label":"तथ्य जाँच करें"},{"step":3,"label":"परिणाम समझाएँ"}]
    return obj


def rows(obj):
    raw=p.json_bytes(obj)
    return n.request_rows(raw,n.sha(raw),PAIR,FONT,plan())


@pytest.mark.parametrize("field,value",[
    ("schema","bad"),("pair_sha256","0"*64),("font_sha256","0"*64),
    ("font_rights_attested",False),("font_rights_attested",1),("license_reference",""),
    ("license_reference",None),("scenes",None),("scenes",[]),("scenes",{}),("extra",1)])
def test_flow_request_fields(field,value):
    obj=flow_req()
    obj[field]=value
    with pytest.raises(ValueError):rows(obj)


@pytest.mark.parametrize("field,value",[
    ("scene",0),("scene",True),("scene",1.0),("scene",2),("title","English"),
    ("title",""),("title",None),("source_declaration_sha256","0"*64),
    ("source_declaration_sha256",None),("nodes",None),("nodes",[]),("nodes",{}),
    ("nodes",[{"step":1,"label":"हिन्दी"}]),("extra",1),("claims",["हिन्दी"])])
def test_flow_scene_fields(field,value):
    obj=flow_req()
    obj["scenes"][0][field]=value
    with pytest.raises(ValueError):rows(obj)


@pytest.mark.parametrize("field,value",[
    ("step",0),("step",True),("step",1.0),("step",3),("label",""),
    ("label",None),("label","English"),("label","हिन्दी"*20),("extra",True)])
def test_flow_node_fields(field,value):
    obj=flow_req()
    obj["scenes"][0]["nodes"][0][field]=value
    with pytest.raises(ValueError):rows(obj)


def test_flow_valid():
    visual=rows(flow_req())
    assert len(visual)==2
    for raw in visual:
        assert n.pv.decode(raw)["schema"]==n.flow.SCHEMA


def test_flow_pin():
    raw=p.json_bytes(flow_req())
    with pytest.raises(ValueError):n.request_rows(raw,"0"*64,PAIR,FONT,plan())


def test_mixed_visual_modes():
    pl=plan()
    for scene,raw in zip(pl.scenes,rows(flow_req())):
        scene.board.specialist_facts[n.KEY]=raw.decode()
    assert n.visual_mode(pl)==n.FLOW_MODE
    raw=p.json_bytes({"schema":n.ht.SCHEMA})
    pl.scenes[0].board.specialist_facts[n.KEY]=raw.decode()
    with pytest.raises(ValueError,match="MIXED_VISUAL_MODE"):n.visual_mode(pl)


def test_mixed_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="MIXED_INVENTORY"):m.select_runs(tmp_path,PAIR)


@pytest.fixture
def client(tmp_path,monkeypatch):
    runs={"hindi":(tmp_path/"hi","a"*64,"b"*64),
          "english":(tmp_path/"en","c"*64,"d"*64)}
    monkeypatch.setattr(m,"select_runs",lambda *args:(runs,4000))
    monkeypatch.setattr(dash,"snapshot",lambda r,duration,fresh=False:{"duration_ms":duration,
        "languages":{},"publication_eligible":False,"read_only":True,"fresh_media_audit":fresh})
    c=TestClient(m.create_app(tmp_path,PAIR))
    token=re.search(r'name="review-session" content="([0-9a-f]{64})"',c.get("/").text).group(1)
    return c,{"X-Review-Session":token}


def test_mixed_page(client):
    c,headers=client
    assert "Mixed-production editorial review" in c.get("/").text
    assert c.get("/api/status",headers=headers).json()["read_only"]


@pytest.mark.parametrize("path",["/api/status","/api/video/hindi","/api/video/english"])
def test_mixed_no_session(client,path):
    c,_=client
    assert c.get(path).status_code==403


@pytest.mark.parametrize("path",["/api/status","/api/submit","/api/register","/api/video/hindi"])
def test_mixed_no_mutation(client,path):
    c,h=client
    assert c.post(path,headers=h,json={}).status_code in (404,405)


@pytest.mark.parametrize("header,value",[("host","evil.example"),("origin","https://evil.example"),
    ("sec-fetch-site","cross-site"),("sec-fetch-site","same-site")])
def test_mixed_origin(client,header,value):
    c,h=client
    assert c.get("/api/status",headers={**h,header:value}).status_code==403


def test_selector_change(client,monkeypatch):
    c,h=client
    monkeypatch.setattr(m,"select_runs",lambda *args:({},4000))
    assert c.get("/api/status",headers=h).status_code==409
