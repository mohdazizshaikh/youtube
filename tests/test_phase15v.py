import pytest
from tools import chart_motion_snapshot as s
from test_phase15u import fixture

PIN="a"*64
HAND="b"*64


def meta():
    records={name:{"bytes":1,"sha256":"c"*64} for name in s.LIMITS}
    records["motion/motion_pair.json"]["sha256"]=PIN
    records["handoff/handoff.json"]["sha256"]=HAND
    return {"schema":s.SCHEMA,"motion_pair_sha256":PIN,"handoff_sha256":HAND,
            "files":records,"publication_eligible":False}


def check(obj):
    raw=s.json_bytes(obj)
    return s.validate_meta(raw,s.sha(raw),PIN,HAND)


@pytest.mark.parametrize("field,value",[("schema","bad"),("motion_pair_sha256",HAND),
    ("handoff_sha256",PIN),("publication_eligible",True),("files",None),("files",{}),("extra",1)])
def test_meta_fields(field,value):
    obj=meta()
    obj[field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("field,value",[("bytes",0),("bytes",True),("bytes",1.0),("bytes",-1),
    ("bytes",s.cm.motion.MAX_VIDEO+1),("sha256","bad"),("extra",1)])
def test_file_record(field,value):
    obj=meta()
    obj["files"]["motion/hindi/motion.mp4"][field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("name",["motion/motion_pair.json","handoff/handoff.json"])
def test_receipt_pin(name):
    obj=meta()
    obj["files"][name]["sha256"]="d"*64
    with pytest.raises(ValueError,match="RECEIPT_PINS"):check(obj)


@pytest.mark.parametrize("name",list(s.LIMITS))
def test_missing_file(name):
    obj=meta()
    del obj["files"][name]
    with pytest.raises(ValueError,match="SNAPSHOT_FILES"):check(obj)


def test_valid_meta():
    assert check(meta())==meta()


@pytest.fixture
def payload(tmp_path,monkeypatch):
    roots=[tmp_path/x for x in ("pair","source","chart","motion","handoff")]
    for root in roots:root.mkdir()
    candidate,handoff=roots[-2:]
    obj,parents=fixture()
    for lang in s.LANGS:
        folder=candidate/lang
        folder.mkdir()
        for name,key in (("motion.mp4","motion_video_sha256"),("captions.vtt","caption_sha256")):
            raw=(lang+name).encode()
            (folder/name).write_bytes(raw)
            obj["tracks"][lang][key]=s.sha(raw)
    raw=s.json_bytes(obj)
    motion_pin=s.sha(raw)
    (candidate/"motion_pair.json").write_bytes(raw)
    packets=s.review.packets_from(obj,motion_pin,obj["chart_pair_sha256"],parents)
    files,_=s.review.payload(packets)
    for name,data in files.items():(handoff/name).write_bytes(data)
    handoff_pin=s.sha(files["handoff.json"])
    args=((roots[0],PIN,roots[1]),roots[2],obj["chart_pair_sha256"],b"",PIN,candidate,motion_pin)
    # Mock expensive media verification only; all real snapshot bytes,
    # receipt, packet and template checks still execute.
    monkeypatch.setattr(s.review,"verify",lambda *a:packets)
    return args,handoff,handoff_pin


def test_backup_restore(payload,tmp_path):
    args,handoff,hand=payload
    dest=tmp_path/"snapshot"
    report=s.backup(args,handoff,hand,dest)
    pin=report["snapshot_sha256"]
    obj=s.inspect(dest,pin,args[6],hand)
    assert len(obj["files"])==10
    out=tmp_path/"restored"
    restored=s.restore((*args[:5],None,args[6]),dest,pin,hand,out)
    assert restored["fresh_media_audit"]
    assert s.inventory(out/"motion",out/"handoff")==obj["files"]
    assert not (out/"INCOMPLETE").exists()
    with pytest.raises(ValueError):s.restore(args,dest,pin,hand,out)


@pytest.mark.parametrize("name",list(s.LIMITS))
def test_snapshot_tamper(payload,tmp_path,name):
    args,handoff,hand=payload
    dest=tmp_path/"snapshot"
    report=s.backup(args,handoff,hand,dest)
    (dest/name).write_bytes(b"tampered")
    with pytest.raises(ValueError):s.inspect(dest,report["snapshot_sha256"],args[6],hand)


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="SNAPSHOT_INVENTORY"):s.inspect(tmp_path,PIN,PIN,HAND)


def test_failed_restore_marker(payload,tmp_path,monkeypatch):
    args,handoff,hand=payload
    dest=tmp_path/"snapshot"
    report=s.backup(args,handoff,hand,dest)
    def fail(*a):raise ValueError("FRESH_AUDIT_FAILED")
    monkeypatch.setattr(s.review,"verify",fail)
    out=tmp_path/"restored"
    with pytest.raises(ValueError,match="FRESH_AUDIT_FAILED"):
        s.restore(args,dest,report["snapshot_sha256"],hand,out)
    assert (out/"INCOMPLETE").is_file()


def test_overlapping_output(payload):
    args,handoff,hand=payload
    with pytest.raises(ValueError):s.backup(args,handoff,hand,handoff/"snapshot")
