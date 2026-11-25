import pytest
from tools import motion_review as r,motion_snapshot as s

PIN="a"*64
PP="b"*64


def packet(demo=True):
    parent={"manifest_sha256":"c"*64,"video_sha256":"d"*64,"publication_eligible":False,
            "synthetic_demo":demo,"scenes":[{"scene":i,"start_ms":(i-1)*600,"end_ms":i*600,
            "scene_sha256":str(i)*64,"narration_text":"test"} for i in (1,2)]}
    receipt={"schema":r.motion.SCHEMA,"publication_eligible":False,"editorial_queue_created":False,
             "parent_manifest_sha256":"c"*64,"parent_video_sha256":"d"*64,
             "motion_video_sha256":"e"*64,"caption_sha256":"f"*64,"duration_ms":1200,
             "stages":[[{"frames":5,"png_sha256":str(i)*64} for i in (1,2,3)] for _ in range(2)]}
    return r.packet_from(receipt,PIN,parent)


def evaluate(obj,review=None):
    raw=r.json_bytes(review if review is not None else r.template(obj))
    return r.evaluate_packet(obj,raw,r.sha(raw))


def test_template():
    obj=packet()
    assert obj["scenes"][1]["stages"][-1]["end_ms"]==1200
    result=evaluate(obj)
    assert len(result["blockers"])==20
    assert not result["publication_eligible"]


@pytest.mark.parametrize("demo",[True,False])
def test_all_pass(demo):
    obj=packet(demo)
    review=r.template(obj)
    review["reviewer"]="declared reviewer"
    for row in review["scenes"]:row["checks"]=dict.fromkeys(r.CHECKS,"PASS")
    result=evaluate(obj,review)
    assert result["self_attested_checklist_complete"] is (not demo)
    assert not result["publication_eligible"] and not result["reviewer_identity_verified"]


@pytest.mark.parametrize("field,value",[
    ("schema","wrong"),("motion_sha256",PP),("packet_sha256",PP),("reviewer",None),
    ("reviewer","a"*121),("reviewer","bad\u202e"),("scenes",None),("scenes",[]),
    ("scenes",{}),("extra",True)])
def test_review_fields(field,value):
    obj=packet()
    row=r.template(obj)
    row[field]=value
    with pytest.raises(ValueError):evaluate(obj,row)


@pytest.mark.parametrize("field,value",[("scene",True),("scene",1.0),("scene",2),
    ("scene_sha256",PP),("notes",None),("notes","a"*2001),("notes","x\u0000"),
    ("checks",{}),("checks",None),("extra",True)])
def test_review_scene(field,value):
    obj=packet()
    row=r.template(obj)
    row["scenes"][0][field]=value
    with pytest.raises(ValueError):evaluate(obj,row)


@pytest.mark.parametrize("bad",[None,True,"UNKNOWN","pass",1,[]])
def test_review_value(bad):
    obj=packet()
    row=r.template(obj)
    row["scenes"][0]["checks"][r.CHECKS[0]]=bad
    with pytest.raises(ValueError):evaluate(obj,row)


def test_revision_note():
    obj=packet()
    row=r.template(obj)
    row["scenes"][0]["checks"]["motion_timing"]="REVISE"
    with pytest.raises(ValueError,match="REVISION_NOTE"):evaluate(obj,row)
    row["scenes"][0]["notes"]="Check timing"
    assert any(b["reason"]=="REVISE" for b in evaluate(obj,row)["blockers"])


def meta():
    rows={name:{"bytes":1,"sha256":"c"*64} for name in s.LIMITS}
    rows["motion/motion.json"]["sha256"]=PIN
    rows["handoff/packet.json"]["sha256"]=PP
    return {"schema":s.SCHEMA,"motion_sha256":PIN,"packet_file_sha256":PP,
            "files":rows,"publication_eligible":False}


def check(obj):
    raw=r.json_bytes(obj)
    return s.validate_meta(raw,r.sha(raw),PIN,PP)


def test_meta():
    assert check(meta())==meta()


@pytest.mark.parametrize("field,value",[("schema","bad"),("motion_sha256",PP),
    ("packet_file_sha256",PIN),("publication_eligible",True),("files",None),
    ("files",{}),("extra",1)])
def test_meta_fields(field,value):
    obj=meta()
    obj[field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("field,value",[("bytes",0),("bytes",True),("bytes",1.0),
    ("bytes",s.motion.MAX_VIDEO+1),("sha256","bad"),("extra",1)])
def test_meta_record(field,value):
    obj=meta()
    obj["files"]["motion/motion.mp4"][field]=value
    with pytest.raises(ValueError):check(obj)


def test_meta_receipt_binding():
    obj=meta()
    obj["files"]["motion/motion.json"]["sha256"]=PP
    with pytest.raises(ValueError,match="FILE_PIN"):check(obj)


def test_snapshot_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="SNAPSHOT_INVENTORY"):s.inspect(tmp_path,PIN,PIN,PP)
