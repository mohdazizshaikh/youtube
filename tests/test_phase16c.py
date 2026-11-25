import pytest
from tools import workflow_resources as r,production_workflow as w
from test_phase16a import local,PIN
from test_pilot_run_verify import run

M=r.MIB


def policy(pin=PIN):
    return {"schema":r.SCHEMA,"plan_sha256":pin,"min_cpu_count":2,
            "min_available_memory_mib":256,"min_workspace_free_mib":128,
            "min_temp_free_mib":64,"max_job_artifact_mib":32,"max_total_artifact_mib":64}


def validate(obj):
    raw=w.json_bytes(obj)
    return r.validate(raw,w.sha(raw),PIN)


@pytest.mark.parametrize("key,value",[("schema","bad"),("plan_sha256","b"*64),("extra",1),
    ("min_cpu_count",0),("min_cpu_count",257),("min_cpu_count",True),
    ("min_available_memory_mib",127),("min_available_memory_mib",262145),
    ("min_workspace_free_mib",63),("min_workspace_free_mib",1048577),
    ("min_temp_free_mib",63),("min_temp_free_mib",None),
    ("max_job_artifact_mib",7),("max_job_artifact_mib",2049),
    ("max_total_artifact_mib",7),("max_total_artifact_mib",65537),
    ("max_job_artifact_mib",65),("max_total_artifact_mib",31),
    ("min_cpu_count",2.0),("max_job_artifact_mib","32")])
def test_policy(key,value):
    obj=policy()
    obj[key]=value
    with pytest.raises(ValueError):validate(obj)


def test_valid():
    assert validate(policy())==policy()


@pytest.mark.parametrize("raw",["","MemFree: 100 kB","MemAvailable: 0 kB","MemAvailable: -2 kB",
    "MemAvailable: 1 MB","MemAvailable: 1 kB\nMemAvailable: 2 kB","MemAvailable: 1.2 kB",
    "MemAvailable: "+"9"*17+" kB","x"*128001])
def test_meminfo_invalid(raw):
    with pytest.raises(ValueError):r.linux_available(raw)


def test_meminfo():
    assert r.linux_available("MemTotal: 4096 kB\nMemAvailable:  2048 kB\n")==2048*1024


def observed():
    return {"cpu_count":4,"available_memory_bytes":1024*M,
            "workspace_free_bytes":1024*M,"temp_free_bytes":1024*M}


@pytest.mark.parametrize("key,value,check",[("cpu_count",1,"cpu"),
    ("available_memory_bytes",256*M-1,"memory"),
    ("workspace_free_bytes",200*M-1,"workspace_disk"),
    ("temp_free_bytes",64*M-1,"temp_disk")])
def test_observation_blocks(key,value,check):
    obj=observed()
    obj[key]=value
    result=r.evaluate(policy(),obj,8*M,16*M)
    assert not result["admitted"] and not result["checks"][check]


@pytest.mark.parametrize("next_bytes,total,check",[(32*M+1,0,"job_artifact_budget"),
    (32*M,32*M+1,"total_artifact_budget"),(0,64*M+1,"total_artifact_budget")])
def test_budgets(next_bytes,total,check):
    result=r.evaluate(policy(),observed(),next_bytes,total)
    assert not result["admitted"] and not result["checks"][check]


@pytest.mark.parametrize("key,value",[("cpu_count",None),("cpu_count",True),
    ("available_memory_bytes",-1),("temp_free_bytes",1.0),("extra",1)])
def test_bad_observation(key,value):
    obj=observed()
    obj[key]=value
    with pytest.raises(ValueError):r.evaluate(policy(),obj,0,0)


def test_exact_boundaries():
    obj={"cpu_count":2,"available_memory_bytes":256*M,
         "workspace_free_bytes":224*M,"temp_free_bytes":64*M}
    assert r.evaluate(policy(),obj,32*M,32*M)["admitted"]


def args(local,tip=None,obj=None):
    raw=w.json_bytes(obj or policy(local[2]))
    return (*local,tip,raw,w.sha(raw))


def test_initial_denial(local,monkeypatch):
    monkeypatch.setattr(r,"observe",lambda *a:{**observed(),"available_memory_bytes":1})
    def forbidden(*a,**kw):pytest.fail("replay reached with insufficient resources")
    monkeypatch.setattr(w,"load",forbidden)
    assert not r.preflight(*args(local))["prerequisites_replayed"]
    with pytest.raises(ValueError,match="RESOURCE_ADMISSION_BLOCKED"):r.guarded_step(*args(local))
    assert not (local[1]/"ACTIVE_JOB.json").exists()


def test_guarded_roundtrip(local,monkeypatch):
    monkeypatch.setattr(r,"observe",lambda *a:observed())
    tip=None
    for expected in ("audit","backup","verify"):
        report=r.preflight(*args(local,tip))
        assert report["admitted"] and report["next_job"]==expected
        if expected=="backup":assert report["next_artifact_estimated_bytes"]>r.OVERHEAD
        if expected=="verify":assert report["committed_artifact_estimated_bytes"]>r.OVERHEAD
        result=r.guarded_step(*args(local,tip))
        assert result["resource_admission_checked"] and not result["hard_resource_limits_enforced"]
        tip=result["checkpoint_sha256"]
    assert w.status(*local,tip)["workflow_complete"]


def test_payload_budget_before_intent(local,monkeypatch):
    monkeypatch.setattr(r,"observe",lambda *a:observed())
    tip=w.step(*local)["checkpoint_sha256"]
    obj=policy(local[2])
    obj["max_job_artifact_mib"]=8
    report=r.preflight(*args(local,tip,obj))
    assert not report["checks"]["job_artifact_budget"]
    with pytest.raises(ValueError,match="RESOURCE_ADMISSION_BLOCKED"):
        r.guarded_step(*args(local,tip,obj))
    assert not (local[1]/"ACTIVE_JOB.json").exists()
    assert not list((local[1]/"artifacts").iterdir())


def test_resource_change_after_intent(local,monkeypatch):
    values=iter([observed(),observed(),{**observed(),"cpu_count":1}])
    monkeypatch.setattr(r,"observe",lambda *a:next(values))
    with pytest.raises(ValueError,match="RESOURCE_ADMISSION_BLOCKED"):r.guarded_step(*args(local))
    assert (local[1]/"ACTIVE_JOB.json").exists()
    assert not list((local[1]/"receipts").iterdir())


def test_wrong_plan_pin(local,monkeypatch):
    monkeypatch.setattr(r,"observe",lambda *a:pytest.fail("probe before policy validation"))
    with pytest.raises(ValueError):r.preflight(*args(local,obj=policy(PIN)))


def test_stale_checkpoint(local,monkeypatch):
    monkeypatch.setattr(r,"observe",lambda *a:observed())
    w.step(*local)
    with pytest.raises(ValueError):r.guarded_step(*args(local))


def test_native_probe(tmp_path):
    import sys
    if not (sys.platform.startswith("linux") or sys.platform=="win32"):pytest.skip("host unsupported")
    obj=r.observe(tmp_path)
    assert obj["available_memory_bytes"]>0 and obj["cpu_count"]>0
    assert obj["workspace_free_bytes"]>=0 and obj["temp_free_bytes"]>=0
