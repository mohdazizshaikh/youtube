"""Portable DAG/receipt contracts and real stopped-pilot orchestration."""
import shutil
import pytest
from tools import production_workflow as w
from test_pilot_run_verify import run
from test_pilot_pipeline import inputs as media_inputs
from tools import pilot_pipeline as pp

PIN="a"*64


def plan(pin=PIN):
    return {"schema":w.PLAN,"jobs":[
        {"id":"verify","kind":"SNAPSHOT_AUDIT","depends_on":["backup"],"input":{"job":"backup"}},
        {"id":"backup","kind":"PILOT_BACKUP","depends_on":["audit"],"input":{"job":"audit"}},
        {"id":"audit","kind":"PILOT_AUDIT","depends_on":[],"input":{"run":"pilot","manifest_sha256":pin}}]}


def check(obj):
    raw=w.json_bytes(obj)
    return w.validate(raw,w.sha(raw))


def test_topological_order():
    assert [j["id"] for j in check(plan())]==["audit","backup","verify"]


@pytest.mark.parametrize("value",["",None,True,"../a","a/b","a\\b","C:","A","con","prn","aux","nul",
                                  "com1","lpt9","x"*49,"a.","a ","a:b","/a"])
def test_leaf(value):
    with pytest.raises(ValueError):w.leaf(value)


@pytest.mark.parametrize("key,value",[("schema","bad"),("jobs",None),("jobs",[]),("jobs",{}),("extra",1)])
def test_plan_fields(key,value):
    obj=plan()
    obj[key]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("key,value",[("id","backup"),("id","../a"),("kind","UPLOAD"),
    ("kind",[]),("depends_on",None),("depends_on",["audit"]),("depends_on",["missing"]),
    ("depends_on",["backup","backup"]),("depends_on",["verify"]),("input",None),
    ("input",{"run":"pilot","manifest_sha256":"bad"}),
    ("input",{"run":"../pilot","manifest_sha256":PIN}),("extra",1)])
def test_bad_job(key,value):
    obj=plan()
    obj["jobs"][2][key]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("value",[{},{"job":"audit"},{"job":"backup","extra":1},{"job":"missing"}])
def test_dependency_input(value):
    obj=plan()
    obj["jobs"][0]["input"]=value
    with pytest.raises(ValueError):check(obj)


def test_budget():
    obj=plan()
    job=obj["jobs"][-1]
    obj["jobs"]=[{**job,"id":f"a{i}"} for i in range(33)]
    with pytest.raises(ValueError):check(obj)


@pytest.fixture
def local(run,monkeypatch):
    # Use genuine byte-level pilot/SQLite fixtures. Only media decode is mocked.
    root,pin=run
    source=root.parent/(root.name+"-sources")
    source.mkdir()
    pilot=source/"pilot"
    shutil.copytree(root,pilot)
    catalog=pilot/"catalog.json"
    catalog.write_bytes(w.json_bytes([{"manifest_sha256":pin,"draft":str(pilot/"draft"),
                                       "assets":str(pilot/"assets")}]))
    original=w.pv.verify
    def verify(path,pin,fresh=False):
        return {**original(path,pin,fresh=False),"fresh_media_audit":fresh}
    monkeypatch.setattr(w.pv,"verify",verify)
    monkeypatch.setattr(w.ps,"verify",verify)
    raw=w.json_bytes(plan(pin))
    workspace=root.parent/(root.name+"-workflow")
    w.initialize(source,workspace,raw,w.sha(raw))
    return source,workspace,w.sha(raw)


def finish(local):
    pin=None
    for _ in range(3):
        result=w.step(*local,pin)
        pin=result["checkpoint_sha256"]
    return pin


def test_roundtrip(local):
    assert w.status(*local)["next_job"]=="audit"
    pin=finish(local)
    result=w.status(*local,pin)
    assert result["workflow_complete"] and result["completed"]==3
    assert w.step(*local,pin)==result
    assert not result["publication_eligible"]


def test_stale_checkpoint(local):
    first=w.step(*local)
    pin=first["checkpoint_sha256"]
    w.step(*local,pin)
    with pytest.raises(ValueError):w.step(*local,pin)
    assert not (local[1]/"ACTIVE_JOB.json").exists()


def test_source_changed(local):
    pin=w.step(*local)["checkpoint_sha256"]
    (local[0]/"pilot"/"draft"/"draft.mp4").write_bytes(b"changed")
    with pytest.raises(ValueError):w.step(*local,pin)
    assert not list((local[1]/"artifacts").iterdir())


def test_receipt_changed(local):
    pin=w.step(*local)["checkpoint_sha256"]
    path=local[1]/"receipts"/"01.json"
    obj=w.pv.document(path)
    obj["report"]["queue_revision"]=123
    path.write_bytes(w.json_bytes(obj))
    with pytest.raises(ValueError):w.status(*local,pin)


def test_snapshot_changed(local):
    pin=finish(local)
    (local[1]/"artifacts"/"backup"/"payload"/"draft"/"draft.mp4").write_bytes(b"changed")
    with pytest.raises(ValueError):w.status(*local,pin)


def test_interrupted(local,monkeypatch):
    pin=w.step(*local)["checkpoint_sha256"]
    def fail(*args):raise RuntimeError("simulated interruption")
    monkeypatch.setattr(w.ps,"backup",fail)
    with pytest.raises(RuntimeError):w.step(*local,pin)
    assert (local[1]/"ACTIVE_JOB.json").exists()
    with pytest.raises(ValueError):w.step(*local,pin)
    assert len(list((local[1]/"receipts").iterdir()))==1


def test_extra_artifact(local):
    (local[1]/"artifacts"/"unexpected").mkdir()
    with pytest.raises(ValueError):w.status(*local)


def test_initial_checkpoint(local):
    with pytest.raises(ValueError):w.step(*local,PIN)


def test_overlap(local):
    source,workspace,pin=local
    with pytest.raises(ValueError):w.initialize(source,source/"nested",
                                                 (workspace/"plan.json").read_bytes(),pin)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media required")
def test_real_workflow(tmp_path):
    plan_path,assets=media_inputs(tmp_path)
    source=tmp_path/"sources"
    source.mkdir()
    result=pp.build(plan_path,assets,source/"pilot")
    raw=w.json_bytes(plan(result["manifest_sha256"]))
    dest=tmp_path/"workflow"
    pin=w.sha(raw)
    w.initialize(source,dest,raw,pin)
    tip=finish((source,dest,pin))
    assert w.status(source,dest,pin,tip)["workflow_complete"]
    assert not (dest/"ACTIVE_JOB.json").exists()
