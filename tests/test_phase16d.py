import pytest
from tools import production_workflow as w,workflow_resources as r,workflow_recovery as recovery
from test_phase16a import local,plan,PIN,check
from test_phase16c import policy,observed
from test_pilot_run_verify import run


def v2(obj):
    return {**obj,"schema":w.PLAN_V2,"resources":{
        k:v for k,v in policy().items() if k not in ("schema","plan_sha256")}}


def pair_plan():
    return v2({"jobs":[
        {"id":"master","kind":"MASTERED_PAIR_AUDIT","depends_on":["pair"],"input":{
            "job":"pair","run":"mastered","request":"master-request","request_sha256":"b"*64,
            "mastered_pair_sha256":"c"*64}},
        {"id":"pair","kind":"BILINGUAL_AUDIT","depends_on":[],"input":{"run":"original","pair_sha256":PIN}}]})


def test_order():
    assert [j["id"] for j in check(pair_plan())]==["pair","master"]


@pytest.mark.parametrize("key,value",[("resources",None),("resources",{}),("resources",[]),
    ("schema",w.PLAN),("schema","other"),("extra",1)])
def test_envelope(key,value):
    obj=pair_plan()
    obj[key]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("key,value",[("schema",r.SCHEMA),("plan_sha256",PIN),
    ("min_cpu_count",0),("min_cpu_count",True),("min_available_memory_mib",127),
    ("min_workspace_free_mib",63),("min_temp_free_mib",63),
    ("max_job_artifact_mib",7),("max_total_artifact_mib",7),("max_job_artifact_mib",65)])
def test_embedded_bounds(key,value):
    obj=pair_plan()
    obj["resources"][key]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("key,value",[("run","../pair"),("run",None),("pair_sha256","bad"),
    ("pair_sha256",None),("extra",1)])
def test_pair_input(key,value):
    obj=pair_plan()
    obj["jobs"][1]["input"][key]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("key,value",[("job","missing"),("job","master"),("run","original"),
    ("run","../a"),("request","a/b"),("request","con"),("request_sha256","bad"),
    ("mastered_pair_sha256",True),("extra",1)])
def test_master_input(key,value):
    obj=pair_plan()
    obj["jobs"][0]["input"][key]=value
    with pytest.raises(ValueError):check(obj)


def test_v1_cannot_use_new_jobs():
    obj=pair_plan()
    del obj["resources"]
    obj["schema"]=w.PLAN
    with pytest.raises(ValueError):check(obj)


@pytest.fixture
def mandatory(local):
    source,workspace,_=local
    obj=v2(w.pv.document(workspace/"plan.json"))
    raw=w.json_bytes(obj)
    dest=workspace.parent/"mandatory"
    w.initialize(source,dest,raw,w.sha(raw))
    return source,dest,w.sha(raw)


def test_legacy_step_enforces_v2(mandatory,monkeypatch):
    monkeypatch.setattr(r,"observe",lambda *a:{**observed(),"cpu_count":1})
    with pytest.raises(ValueError,match="RESOURCE_ADMISSION_BLOCKED"):w.step(*mandatory)
    assert not (mandatory[1]/"ACTIVE_JOB.json").exists()


def test_v2_roundtrip(mandatory,monkeypatch):
    monkeypatch.setattr(r,"observe",lambda *a:observed())
    tip=None
    for _ in range(3):tip=w.step(*mandatory,tip)["checkpoint_sha256"]
    assert w.status(*mandatory,tip)["workflow_complete"]


def test_optional_policy_cannot_weaken_v2(mandatory,monkeypatch):
    monkeypatch.setattr(r,"observe",lambda *a:{**observed(),"cpu_count":1})
    obj=policy(mandatory[2])
    obj["min_cpu_count"]=1
    raw=w.json_bytes(obj)
    with pytest.raises(ValueError,match="RESOURCE_ADMISSION_BLOCKED"):
        r.guarded_step(*mandatory,None,raw,w.sha(raw))


def test_v2_policy_tamper(mandatory,monkeypatch):
    path=mandatory[1]/"plan.json"
    obj=w.pv.document(path)
    obj["resources"]["min_cpu_count"]=1
    path.write_bytes(w.json_bytes(obj))
    with pytest.raises(ValueError):w.step(*mandatory)


def test_recovery_enforces_v2(mandatory,monkeypatch):
    monkeypatch.setattr(r,"observe",lambda *a:observed())
    write=w.write
    def fail(path,raw):
        if path.parent.name=="receipts":raise RuntimeError("crash")
        return write(path,raw)
    with monkeypatch.context() as patch:
        patch.setattr(w,"write",fail)
        with pytest.raises(RuntimeError):w.step(*mandatory)
    raw=recovery.prepare(*mandatory)
    monkeypatch.setattr(r,"observe",lambda *a:{**observed(),"cpu_count":1})
    with pytest.raises(ValueError,match="RESOURCE_ADMISSION_BLOCKED"):
        recovery.apply(*mandatory,None,raw,w.sha(raw))
    assert (mandatory[1]/"ACTIVE_JOB.json").exists()
    monkeypatch.setattr(r,"observe",lambda *a:observed())
    assert recovery.apply(*mandatory,None,raw,w.sha(raw))["completed"]==1


def test_pair_dispatch(tmp_path,monkeypatch):
    from tools import workflow_pair_adapters as a
    source=tmp_path/"source"
    source.mkdir()
    for name in ("original","mastered"):(source/name).mkdir()
    (source/"master-request").write_bytes(b"request")
    obj=pair_plan()
    raw=w.json_bytes(obj)
    dest=tmp_path/"workflow"
    pin=w.sha(raw)
    w.initialize(source,dest,raw,pin)
    monkeypatch.setattr(r,"observe",lambda *a:observed())
    evidence={"pair_sha256":PIN,"run":"original","fresh_media_audit":True}
    monkeypatch.setattr(a,"audit",lambda *a:evidence)
    def mastered(source,job,parent):
        assert parent==evidence
        return {"mastered_pair_sha256":"c"*64}
    monkeypatch.setattr(a,"mastered",mastered)
    tip=w.step(source,dest,pin)["checkpoint_sha256"]
    assert w.step(source,dest,pin,tip)["workflow_complete"]
    assert not list((dest/"artifacts").iterdir())
