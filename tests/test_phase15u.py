import pytest
from tools import chart_motion_review as r

PIN="a"*64
CHART="b"*64


def fixture(count=3,demo=True):
    duration=count*5*40*2
    parents={}
    tracks={}
    for lang,digit in (("hindi","c"),("english","d")):
        parents[lang]={"manifest_sha256":digit*64,"video_sha256":"e"*64,
            "publication_eligible":False,"synthetic_demo":demo,"scenes":[]}
        for i in (1,2):
            parents[lang]["scenes"].append({"scene":i,"start_ms":(i-1)*duration//2,
                "end_ms":i*duration//2,"scene_sha256":str(i)*64,
                "specialist_facts":{r.cm.cp.KEY:r.json_bytes({"language":lang,"scene":i,
                       "source_transcription_verified":False}).decode()}})
        tracks[lang]={"parent_manifest_sha256":digit*64,"parent_video_sha256":"e"*64,
            "motion_video_sha256":digit*64,"caption_sha256":"f"*64,"duration_ms":duration,
            "stages":[[{"frames":5,"png_sha256":str(j)*64} for j in range(1,count+1)] for _ in (1,2)],
            "audit":{"decoded_parent_audio_equal":True,"comparison_resolution":[96,96],
                     "full_resolution_pixels_verified":False,"frames_compared":duration//40}}
    return r.cm.receipt(CHART,"1"*64,tracks),parents


@pytest.mark.parametrize("count",[3,4,5])
def test_packet(count):
    obj,parents=fixture(count)
    p=r.packets_from(obj,PIN,CHART,parents)
    for lang in r.LANGS:
        assert p[lang]["language"]==lang and len(p[lang]["scenes"][0]["stages"])==count
        assert p[lang]["scenes"][-1]["stages"][-1]["end_ms"]==obj["duration_ms"]
        assert len(r.template(p[lang])["scenes"][0]["checks"])==13


@pytest.mark.parametrize("field,value",[("schema","bad"),("chart_pair_sha256","0"*64),
    ("effect","other"),("fps",25.0),("fps",30),("timing_method","WORD"),
    ("human_visual_review_required",False),("editorial_queue_created",True),
    ("source_transcription_verified",True),("word_alignment_verified",True),
    ("publication_eligible",True),("tracks",{}),("duration_ms",1241)])
def test_receipt(field,value):
    obj,parents=fixture()
    obj[field]=value
    with pytest.raises(ValueError):r.packets_from(obj,PIN,CHART,parents)


@pytest.mark.parametrize("field,value",[("decoded_parent_audio_equal",False),
    ("comparison_resolution",[128,128]),("full_resolution_pixels_verified",True),
    ("frames_compared",29),("frames_compared",30.0)])
def test_audit(field,value):
    obj,parents=fixture()
    obj["tracks"]["hindi"]["audit"][field]=value
    with pytest.raises(ValueError):r.packets_from(obj,PIN,CHART,parents)


@pytest.mark.parametrize("field,value",[("parent_manifest_sha256","0"*64),
    ("parent_video_sha256","0"*64),("motion_video_sha256","bad"),("caption_sha256","bad"),
    ("duration_ms",1240),("extra",1)])
def test_track(field,value):
    obj,parents=fixture()
    obj["tracks"]["hindi"][field]=value
    with pytest.raises(ValueError):r.packets_from(obj,PIN,CHART,parents)


@pytest.mark.parametrize("field,value",[("frames",4),("frames",True),("frames",5.0),
    ("png_sha256","bad"),("extra",1)])
def test_stage(field,value):
    obj,parents=fixture()
    obj["tracks"]["hindi"]["stages"][0][0][field]=value
    with pytest.raises(ValueError):r.packets_from(obj,PIN,CHART,parents)


def test_stage_count():
    obj,parents=fixture()
    obj["tracks"]["hindi"]["stages"][0].pop()
    with pytest.raises(ValueError):r.packets_from(obj,PIN,CHART,parents)


def test_wrong_chart_evidence():
    obj,parents=fixture()
    parents["hindi"]["scenes"][0]["specialist_facts"][r.cm.cp.KEY]=r.json_bytes(
        {"language":"english","scene":1,"source_transcription_verified":False}).decode()
    with pytest.raises(ValueError,match="CHART_EVIDENCE"):r.packets_from(obj,PIN,CHART,parents)


def test_asymmetric_stages():
    obj,parents=fixture()
    # Same scene duration, different allocation in the two languages.
    obj,parents=fixture(4)
    obj["tracks"]["english"]["stages"][0][0]["frames"]=6
    obj["tracks"]["english"]["stages"][0][1]["frames"]=4
    with pytest.raises(ValueError):r.packets_from(obj,PIN,CHART,parents)


@pytest.mark.parametrize("demo",[True,False])
def test_pair_review(demo):
    obj,parents=fixture(demo=demo)
    p=r.packets_from(obj,PIN,CHART,parents)
    reviews={}
    for lang in r.LANGS:
        review=r.template(p[lang])
        review["reviewer"]="declared reviewer"
        for row in review["scenes"]:row["checks"]=dict.fromkeys(r.CHECKS,"PASS")
        reviews[lang]=r.json_bytes(review)
    pins={l:r.sha(raw) for l,raw in reviews.items()}
    files,meta=r.payload(p)
    result=r.evaluate_packets(p,reviews,pins,r.sha(files["handoff.json"]))
    assert result["both_self_attested_checklists_complete"] is (not demo)
    assert not result["publication_eligible"] and not result["source_transcription_verified"]
    reviews["english"]=reviews["hindi"]
    pins["english"]=pins["hindi"]
    with pytest.raises(ValueError,match="REVIEW_BINDING"):r.evaluate_packets(p,reviews,pins,PIN)


def test_native_schema_not_accepted():
    obj,parents=fixture()
    p=r.packets_from(obj,PIN,CHART,parents)
    raw=r.json_bytes(r.mr.template(p["hindi"]))
    with pytest.raises(ValueError,match="REVIEW_BINDING"):
        r.mr.evaluate_packet(p["hindi"],raw,r.sha(raw),required_checks=r.CHECKS,review_schema=r.REVIEW)


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="HANDOFF_INVENTORY"):r.verify((),tmp_path,PIN)


def test_handoff_bytes(tmp_path,monkeypatch):
    obj,parents=fixture()
    p=r.packets_from(obj,PIN,CHART,parents)
    monkeypatch.setattr(r,"packets",lambda *args:p)
    roots=[tmp_path/x for x in ("pair","input","chart","motion")]
    for root in roots:root.mkdir()
    args=((roots[0],None,roots[1]),roots[2],CHART,b"",PIN,roots[3],PIN)
    dest=tmp_path/"handoff"
    report=r.prepare(args,dest)
    assert r.verify(args,dest,report["handoff_sha256"])==p
    (dest/"english_review_template.json").write_bytes(b"changed")
    with pytest.raises(ValueError,match="HANDOFF_BYTES"):r.verify(args,dest,report["handoff_sha256"])
