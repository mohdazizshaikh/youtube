"""Portable recovery contracts and real restore orchestration."""
import shutil
import pytest
from tools import production_workflow as w,workflow_recovery as r
from test_phase16a import local,plan,check,PIN
from test_pilot_run_verify import run
from test_pilot_pipeline import inputs as media_inputs
from tools import pilot_pipeline as pp


def extended(pin=PIN):
    obj=plan(pin)
    obj["jobs"].insert(0,{"id":"restore","kind":"PILOT_RESTORE",
                       "depends_on":["backup","verify"],"input":{"job":"backup"}})
    return obj


def test_restore_order():
    assert [j["id"] for j in check(extended())]==["audit","backup","verify","restore"]


@pytest.mark.parametrize("deps",[[],["backup"],["verify"],["audit","backup"],["backup","restore"],
                                ["backup","verify","missing"]])
def test_restore_dependencies(deps):
    obj=extended()
    obj["jobs"][0]["depends_on"]=deps
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("job",["audit","verify","restore","missing"])
def test_restore_input(job):
    obj=extended()
    obj["jobs"][0]["input"]["job"]=job
    with pytest.raises(ValueError):check(obj)


@pytest.fixture
def with_restore(local):
    source,workspace,_=local
    pin=w.pv.file_hash(source/"pilot"/"draft"/"manifest.json")
    raw=w.json_bytes(extended(pin))
    dest=workspace.parent/(workspace.name+"-restore")
    w.initialize(source,dest,raw,w.sha(raw))
    return source,dest,w.sha(raw)


def advance(local,n):
    tip=None
    for _ in range(n):tip=w.step(*local,tip)["checkpoint_sha256"]
    return tip


def interrupt_after_receipt(local,tip,monkeypatch,*,after=False):
    old=w.write
    def fail(path,raw):
        if path.parent.name=="receipts":
            if after:old(path,raw)
            raise RuntimeError("simulated crash")
        return old(path,raw)
    with monkeypatch.context() as patch:
        patch.setattr(w,"write",fail)
        with pytest.raises(RuntimeError,match="simulated crash"):w.step(*local,tip)


def recover(local,tip,pin=None):
    raw=r.prepare(*local,tip,pin)
    return r.apply(*local,tip,raw,w.sha(raw))


@pytest.mark.parametrize("after",[False,True])
def test_read_only_recovery(local,monkeypatch,after):
    interrupt_after_receipt(local,None,monkeypatch,after=after)
    raw=r.prepare(*local)
    assert w.pv.decode(raw)["action"]=="RECHECK_READ_ONLY"
    assert w.pv.decode(raw)["receipt_already_present"] is after
    with pytest.raises(ValueError):w.step(*local)
    result=r.apply(*local,None,raw,w.sha(raw))
    assert result["next_job"]=="backup" and not result["production_write_repeated"]
    assert w.status(*local,result["checkpoint_sha256"])["completed"]==1


@pytest.mark.parametrize("after",[False,True])
def test_backup_adoption(local,monkeypatch,after):
    tip=advance(local,1)
    captured={}
    old=w.ps.backup
    def record(*a):
        result=old(*a)
        captured["pin"]=result["snapshot_sha256"]
        return result
    monkeypatch.setattr(w.ps,"backup",record)
    interrupt_after_receipt(local,tip,monkeypatch,after=after)
    with pytest.raises(ValueError):r.prepare(*local,tip)
    def forbidden(*a):pytest.fail("backup repeated")
    monkeypatch.setattr(w.ps,"backup",forbidden)
    result=recover(local,tip,captured["pin"])
    assert result["recovery_action"]=="ADOPT_VERIFIED_BACKUP"
    assert w.step(*local,result["checkpoint_sha256"])["workflow_complete"]


def test_restore(with_restore):
    tip=advance(with_restore,4)
    assert w.status(*with_restore,tip)["workflow_complete"]
    root=with_restore[1]/"artifacts"/"restore"
    source=with_restore[0]/"pilot"
    assert (root/"reviews.sqlite").read_bytes()==(source/"reviews.sqlite").read_bytes()
    assert (root/"catalog.json").read_bytes()!=(source/"catalog.json").read_bytes()


@pytest.mark.parametrize("after",[False,True])
def test_restore_adoption(with_restore,monkeypatch,after):
    tip=advance(with_restore,3)
    interrupt_after_receipt(with_restore,tip,monkeypatch,after=after)
    def forbidden(*a):pytest.fail("restore repeated")
    monkeypatch.setattr(w.ps,"restore",forbidden)
    result=recover(with_restore,tip)
    assert result["workflow_complete"] and result["recovery_action"]=="ADOPT_VERIFIED_RESTORE"


def test_failed_backup_not_adopted(local,monkeypatch):
    tip=advance(local,1)
    def fail(source,dest,pin):
        dest.mkdir()
        (dest/"INCOMPLETE").touch()
        raise RuntimeError("failed backup")
    monkeypatch.setattr(w.ps,"backup",fail)
    with pytest.raises(RuntimeError):w.step(*local,tip)
    with pytest.raises((ValueError,OSError)):r.prepare(*local,tip,PIN)
    assert (local[1]/"ACTIVE_JOB.json").exists()


@pytest.mark.parametrize("field,value",[("schema","other"),("plan_sha256",PIN),
    ("previous_sha256",PIN),("intent_sha256",PIN),("job_id","backup"),("sequence",2),
    ("action","RETRY_WRITE"),("snapshot_sha256",PIN),("candidate_checkpoint_sha256",PIN),
    ("receipt_already_present",True),("publication_eligible",True),("extra",1)])
def test_changed_recovery(local,monkeypatch,field,value):
    interrupt_after_receipt(local,None,monkeypatch)
    raw=r.prepare(*local)
    obj=w.pv.decode(raw)
    obj[field]=value
    tampered=w.json_bytes(obj)
    with pytest.raises(ValueError):r.apply(*local,None,tampered,w.sha(tampered))
    assert (local[1]/"ACTIVE_JOB.json").exists()


def test_wrong_recovery_pin(local,monkeypatch):
    interrupt_after_receipt(local,None,monkeypatch)
    raw=r.prepare(*local)
    with pytest.raises(ValueError):r.apply(*local,None,raw,PIN)


def test_wrong_intent(local,monkeypatch):
    interrupt_after_receipt(local,None,monkeypatch)
    (local[1]/"ACTIVE_JOB.json").write_bytes(b"tamper")
    with pytest.raises(ValueError):r.prepare(*local)


def test_uncommitted_receipt_tamper(local,monkeypatch):
    interrupt_after_receipt(local,None,monkeypatch,after=True)
    target=local[1]/"receipts"/"01.json"
    obj=w.pv.document(target)
    obj["report"]["queue_revision"]=1
    target.write_bytes(w.json_bytes(obj))
    with pytest.raises(ValueError):r.prepare(*local)


def test_missing_intent(local):
    with pytest.raises(ValueError):r.prepare(*local)


def test_changed_source(local,monkeypatch):
    interrupt_after_receipt(local,None,monkeypatch)
    raw=r.prepare(*local)
    (local[0]/"pilot"/"draft"/"draft.mp4").write_bytes(b"changed")
    with pytest.raises(ValueError):r.apply(*local,None,raw,w.sha(raw))


def test_retry_after_receipt_written(local,monkeypatch):
    interrupt_after_receipt(local,None,monkeypatch)
    raw=r.prepare(*local)
    obj,receipt,*_=r.candidate(*local,None)
    w.write(local[1]/"receipts"/"01.json",receipt)
    assert r.apply(*local,None,raw,w.sha(raw))["completed"]==1


def test_restore_tamper(with_restore):
    tip=advance(with_restore,4)
    (with_restore[1]/"artifacts"/"restore"/"draft"/"draft.mp4").write_bytes(b"tamper")
    with pytest.raises(ValueError):w.status(*with_restore,tip)


def test_recovery_checkpoint(local,monkeypatch):
    tip=advance(local,1)
    interrupt_after_receipt(local,tip,monkeypatch)
    with pytest.raises(ValueError):r.prepare(*local,PIN,PIN)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media required")
def test_real_restore_workflow(tmp_path):
    plan_path,assets=media_inputs(tmp_path)
    source=tmp_path/"sources"
    source.mkdir()
    result=pp.build(plan_path,assets,source/"pilot")
    raw=w.json_bytes(extended(result["manifest_sha256"]))
    dest=tmp_path/"workflow"
    pin=w.sha(raw)
    w.initialize(source,dest,raw,pin)
    tip=advance((source,dest,pin),4)
    assert w.status(source,dest,pin,tip)["workflow_complete"]
    assert w.pv.verify(dest/"artifacts"/"restore",result["manifest_sha256"],fresh=True)["fresh_media_audit"]
