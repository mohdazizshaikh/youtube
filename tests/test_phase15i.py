import json
import shutil
import pytest
from tools import bilingual_review_transaction as t, narration_duck as d
from tools import bilingual_pilot as p
from test_bilingual_compose import inputs
from test_bilingual_pilot import pair_inputs,values
from test_narration_prepare import tone
from test_phase15h import mix_request

PAIR="a"*64
REQ="b"*64


def txn():
    return {"schema":t.SCHEMA,"pair_sha256":PAIR,"native_sha256":None,
            "request_sha256":REQ,"publication_eligible":False,
            "languages":{lang:{"manifest_sha256":("c" if lang=="hindi" else "d")*64,
                "expected_revision":0,"review_sha256":"e"*64,"proposed_state":"DEMO_BLOCKED",
                "blocker_count":1,"history_sha256":t.pv.canonical([])} for lang in t.LANGS}}


def validate(obj):
    raw=p.json_bytes(obj)
    return t.validate_plan(raw,p.sha(raw),REQ,PAIR,None)


@pytest.mark.parametrize("key,value",[
    ("schema","bad"),("request_sha256","0"*64),("pair_sha256","0"*64),("native_sha256","f"*64),
    ("publication_eligible",True),("publication_eligible",0),("languages",None),
    ("languages",{}),("extra",1)])
def test_plan_invalid(key,value):
    obj=txn()
    obj[key]=value
    with pytest.raises(ValueError):validate(obj)


@pytest.mark.parametrize("key,value",[
    ("manifest_sha256","bad"),("review_sha256","A"*64),("history_sha256",None),
    ("expected_revision",-1),("expected_revision",100000),("expected_revision",True),
    ("expected_revision",0.0),("blocker_count",-1),("blocker_count",True),
    ("blocker_count",10001),("proposed_state","PENDING"),("extra",1)])
def test_plan_row(key,value):
    obj=txn()
    obj["languages"]["hindi"][key]=value
    with pytest.raises(ValueError):validate(obj)


def test_plan_valid():
    assert validate(txn())==txn()


@pytest.mark.parametrize("pin",["","0"*64,"A"*64,"x"*64])
def test_plan_pin(pin):
    raw=p.json_bytes(txn())
    with pytest.raises(ValueError):t.validate_plan(raw,pin,REQ,PAIR,None)


def test_classification():
    row=txn()["languages"]["hindi"]
    assert t.classify([],0,"PENDING",row)=="PENDING"
    assert t.classify([[1,"e"*64,"DEMO_BLOCKED",1]],1,"DEMO_BLOCKED",row)=="RECORDED"


@pytest.mark.parametrize("hist,rev,state",[
    ([],1,"DEMO_BLOCKED"),([[1,"f"*64,"DEMO_BLOCKED",1]],1,"DEMO_BLOCKED"),
    ([[1,"e"*64,"INCOMPLETE",1]],1,"INCOMPLETE"),
    ([[1,"e"*64,"DEMO_BLOCKED",2]],1,"DEMO_BLOCKED"),
    ([[1,"e"*64,"DEMO_BLOCKED",1]],1,"INCOMPLETE"),
    ([[1,"e"*64,"DEMO_BLOCKED",1],[2,"f"*64,"DEMO_BLOCKED",1]],2,"DEMO_BLOCKED")])
def test_classify_conflict(hist,rev,state):
    with pytest.raises(ValueError):t.classify(hist,rev,state,txn()["languages"]["hindi"])


def test_history_prefix():
    row=txn()["languages"]["hindi"]
    row.update(expected_revision=1,history_sha256=t.pv.canonical([[1,"a"*64,"DEMO_BLOCKED",3]]))
    with pytest.raises(ValueError,match="HISTORY_PREFIX"):
        t.classify([[1,"b"*64,"DEMO_BLOCKED",3]],1,"DEMO_BLOCKED",row)


def duck_request(v=b"voice",m=b"music"):
    return {"schema":d.SCHEMA,"mix":mix_request(v,m),"threshold_dbfs":-35,
            "duck_db":9,"attack_ms":20,"release_ms":200,"hold_ms":40}


def validate_duck(obj):
    raw=p.json_bytes(obj)
    return d.validate(raw,p.sha(raw))


@pytest.mark.parametrize("key,value",[
    ("schema","bad"),("mix",None),("mix",{}),("threshold_dbfs",-51),("threshold_dbfs",-19),
    ("threshold_dbfs",True),("duck_db",2),("duck_db",19),("duck_db",None),
    ("attack_ms",9),("attack_ms",201),("attack_ms",True),("attack_ms",20.0),
    ("release_ms",79),("release_ms",1001),("hold_ms",-1),("hold_ms",501),
    ("hold_ms",False),("extra",1)])
def test_duck_request(key,value):
    obj=duck_request()
    obj[key]=value
    with pytest.raises(ValueError):validate_duck(obj)


def test_lookahead_hold():
    v=[0]*d.BLOCK+[10000]*d.BLOCK+[0]*(4*d.BLOCK)
    assert d.targets(v,-35,40)==[True,True,True,True,False,False]


def test_envelope():
    n=d.RATE*3
    v=[0]*n
    v[d.RATE:2*d.RATE]=[4000]*d.RATE
    m=[1000]*n
    out,stats=d.render_samples(v,m,0,duck_request())
    assert len(out)==n and out[0]==v[0] and out[-1]==v[-1]
    assert out[d.RATE//2]==1000
    assert 300<=out[d.RATE*3//2]-4000<=400
    assert out[5*d.RATE//2]>700
    assert 8.9<=stats["max_applied_duck_db"]<=9


def test_sample_clip():
    with pytest.raises(ValueError,match="DUCK_SAMPLE_CLIPPING"):
        d.render_samples([32000]*(3*d.RATE),[32000]*(3*d.RATE),0,duck_request())


def test_length():
    v,m=tone(seconds=3),tone(seconds=4,frequency=500)
    raw=p.json_bytes(duck_request(v,m))
    with pytest.raises(ValueError,match="DUCK_LENGTH"):d.duck(v,m,raw,p.sha(raw))


@pytest.mark.skipif(not shutil.which("ffmpeg"),reason="local FFmpeg required")
def test_real_duck():
    v,m=tone(seconds=4),tone(seconds=4,frequency=500,amplitude=2000)
    raw=p.json_bytes(duck_request(v,m))
    output,r=d.duck(v,m,raw,p.sha(raw))
    assert r["output"]["frames"]==64000 and r["output"]["true_peak_dbtp"]<=-3
    assert r["max_applied_duck_db"]>8
    assert not r["voice_compressed"] and not r["publication_eligible"]
    assert d.mix.samples(output)[-1]==d.mix.samples(v)[-1]


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media required")
def test_interrupted_transaction(pair_inputs,monkeypatch):
    v=values(pair_inputs)
    built=p.build(*v)
    root=v[-1]
    pin=built["pair_sha256"]
    obj={"schema":t.pre.SCHEMA,"pair_sha256":pin,"native_sha256":None,"reviews":{
        lang:{"revision":0,"review":t.pv.document(root/lang/"review_template.json")} for lang in t.LANGS}}
    req=p.json_bytes(obj)
    raw=t.prepare(root,pin,req,p.sha(req))
    args=(root,pin,req,p.sha(req),raw,p.sha(raw))
    assert t.reconcile(*args)=={"hindi":"PENDING","english":"PENDING"}
    original=t.queue.submit
    def interrupted(db,*args):
        if db.parent.name=="english":
            raise RuntimeError("simulated interruption")
        return original(db,*args)
    monkeypatch.setattr(t.queue,"submit",interrupted)
    with pytest.raises(RuntimeError):t.apply(*args)
    assert t.reconcile(*args)=={"hindi":"RECORDED","english":"PENDING"}
    monkeypatch.setattr(t.queue,"submit",original)
    result=t.apply(*args)
    assert result["completed"] and not result["cross_database_atomic"]
    assert t.apply(*args)==result
    for lang in t.LANGS:
        assert len(t.history(root/lang,built["runs"][lang]["manifest_sha256"]))==1
