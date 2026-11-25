import pytest
from tools import chart_review_transaction as t
from tools import bilingual_review_transaction as tx
from tools import mixed_review_transaction as mt

PIN="a"*64
REQ="b"*64


def request():
    return {"schema":t.REQUEST,"chart_pair_sha256":PIN,
            "reviews":{l:{"revision":0,"review":{}} for l in tx.LANGS}}


def validate(obj):
    raw=tx.bp.json_bytes(obj)
    return t.validate(raw,t.sha(raw),PIN)


@pytest.mark.parametrize("key,value",[("schema","bad"),("schema",mt.REQUEST),
    ("chart_pair_sha256","0"*64),("chart_pair_sha256",None),("reviews",None),
    ("reviews",[]),("reviews",{}),("reviews",{"hindi":{}}),("extra",True)])
def test_request_fields(key,value):
    obj=request()
    obj[key]=value
    with pytest.raises(ValueError):validate(obj)


@pytest.mark.parametrize("lang",tx.LANGS)
@pytest.mark.parametrize("key,value",[("revision",-1),("revision",True),("revision",0.0),
    ("revision",100000),("revision","0"),("review",None),("review",[]),("extra",1)])
def test_envelope(lang,key,value):
    obj=request()
    obj["reviews"][lang][key]=value
    with pytest.raises(ValueError):validate(obj)


def test_valid():
    assert validate(request())==request()["reviews"]


def plan():
    return {"schema":t.SCHEMA,"chart_pair_sha256":PIN,"request_sha256":REQ,
            "native_sha256":None,"publication_eligible":False,"languages":{
        l:{"manifest_sha256":("c" if l=="hindi" else "d")*64,
           "expected_revision":0,"review_sha256":"e"*64,"proposed_state":"DEMO_BLOCKED",
           "blocker_count":1,"history_sha256":tx.pv.canonical([])} for l in tx.LANGS}}


@pytest.mark.parametrize("key,value",[("schema",tx.SCHEMA),("schema",mt.SCHEMA),
    ("chart_pair_sha256","0"*64),("request_sha256","0"*64),("native_sha256","f"*64),
    ("publication_eligible",True),("languages",{}),("extra",1)])
def test_plan_fields(key,value):
    obj=plan()
    obj[key]=value
    raw=tx.bp.json_bytes(obj)
    with pytest.raises(ValueError):t.checked_plan(raw,t.sha(raw),REQ,PIN)


def test_schema_separation():
    raw=tx.bp.json_bytes(plan())
    assert t.checked_plan(raw,t.sha(raw),REQ,PIN)==plan()
    with pytest.raises(ValueError):tx.validate_plan(raw,t.sha(raw),REQ,PIN,None)
    with pytest.raises(ValueError):mt.checked_plan(raw,t.sha(raw),REQ,PIN)


@pytest.fixture
def selection(tmp_path,monkeypatch):
    runs={l:(tmp_path/l,("c" if l=="hindi" else "d")*64,"e"*64) for l in tx.LANGS}
    states={l:{"revision":0,"state":"PENDING"} for l in tx.LANGS}
    audit={"fresh_media_audit":True,"publication_eligible":False,"chart_pair_sha256":PIN,
           "duration_ms":2000,"review_states":states}
    monkeypatch.setattr(t.cp,"verify",lambda *a:audit)
    monkeypatch.setattr(t.dash,"select_runs",lambda *a:(runs,2000))
    monkeypatch.setattr(t.dash.dash,"snapshot",lambda *a:{"languages":states})
    return audit,runs,states


@pytest.mark.parametrize("key,value",[("fresh_media_audit",False),("publication_eligible",True),
    ("chart_pair_sha256","0"*64),("duration_ms",2040),("review_states",{})])
def test_audit_binding(selection,key,value):
    audit,_,_=selection
    audit[key]=value
    with pytest.raises(ValueError):t.verified_selector((),None,PIN)


def test_selection_changed(selection,monkeypatch):
    _,runs,_=selection
    select=t.verified_selector((),None,PIN)
    assert select()==(runs,2000)
    monkeypatch.setattr(t.dash,"select_runs",lambda *a:(runs,2040))
    with pytest.raises(ValueError,match="CHART_SELECTION_CHANGED"):select()


@pytest.mark.parametrize("mode",["prepare","reconcile","apply"])
def test_original_source_failure_before_transaction(monkeypatch,mode):
    raw=tx.bp.json_bytes(request())
    plan_obj=plan()
    plan_obj["request_sha256"]=t.sha(raw)
    plan_raw=tx.bp.json_bytes(plan_obj)
    def fail(*a):raise ValueError("SOURCE_CHANGED")
    def forbidden(*a):pytest.fail("transaction reached after failed source audit")
    monkeypatch.setattr(t.cp,"verify",fail)
    for name in ("prepare_selected","reconcile_selected","apply_selected"):
        monkeypatch.setattr(tx,name,forbidden)
    args=((),None,PIN,raw,t.sha(raw))
    if mode!="prepare":args+= (plan_raw,t.sha(plan_raw))
    with pytest.raises(ValueError,match="SOURCE_CHANGED"):getattr(t,mode)(*args)


def test_plan_location(tmp_path):
    parent=tmp_path/"parent"
    source=tmp_path/"source"
    chart=tmp_path/"chart"
    for p in (parent,source,chart):p.mkdir()
    inputs=(parent,None,source)
    assert t.plan_path(tmp_path/"plan.json",inputs,chart)==tmp_path/"plan.json"
    for p in (parent,source,chart):
        with pytest.raises(ValueError):t.plan_path(p/"plan.json",inputs,chart)
