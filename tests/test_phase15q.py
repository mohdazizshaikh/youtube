import os
import shutil
from pathlib import Path
import pytest
from PIL import features
from tools import bilingual_chart_pilot as c,bilingual_pilot as bp
from tools.domain_storyboard import demo_spec
from app.domain_storyboards import render_board
from app.domain_draft_video import DraftPlan
from test_phase15p import SOURCE,SP,data,request
from test_bilingual_compose import inputs
from test_bilingual_pilot import pair_inputs,values

PIN="a"*64
FONTS={"hindi":"b"*64,"english":"c"*64}


def req():
    return {"schema":c.REQUEST,"pair_sha256":PIN,"font_sha256":FONTS.copy(),
            "scenes":[{"scene":i,"source_id":"A","source_sha256":"d"*64,
                       "data_sha256":"e"*64,"request_sha256":"f"*64,
                       "board_sha256":{"hindi":"1"*64,"english":"2"*64}} for i in (1,2)]}


def validate(obj):
    raw=c.json_bytes(obj)
    return c.validate(raw,c.sha(raw),PIN,2)


@pytest.mark.parametrize("field,value",[("schema","bad"),("pair_sha256","0"*64),
    ("pair_sha256",None),("font_sha256",None),("font_sha256",{}),("font_sha256",[]),
    ("scenes",None),("scenes",[]),("scenes",{}),("extra",1)])
def test_request_fields(field,value):
    obj=req()
    obj[field]=value
    with pytest.raises(ValueError):validate(obj)


@pytest.mark.parametrize("field,value",[("scene",0),("scene",True),("scene",1.0),("scene",2),
    ("source_id",""),("source_id","lowercase"),("source_id","A/"),("source_id",None),
    ("source_sha256","bad"),("data_sha256","bad"),("request_sha256","bad"),
    ("board_sha256",{}),("board_sha256",[]),("board_sha256",None),
    ("board_sha256",{"hindi":"a"*64,"english":"bad"}),("extra",1)])
def test_scene_fields(field,value):
    obj=req()
    obj["scenes"][0][field]=value
    with pytest.raises(ValueError):validate(obj)


def test_valid():
    assert validate(req())==req()


def test_binding():
    board=demo_spec("technology","SHORT")
    row=req()["scenes"][0]
    source=board.sources[0]
    row["source_id"]=source.source_id
    row["board_sha256"]["hindi"]=c.board_pin(board)
    c.source_binding(board,row,"hindi",str(source.url))
    with pytest.raises(ValueError,match="SOURCE_REFERENCE_BINDING"):
        c.source_binding(board,row,"hindi","https://different.invalid/")
    with pytest.raises(ValueError,match="BOARD_BINDING"):
        c.source_binding(board,row,"english",str(source.url))
    board.specialist_facts[c.KEY]="collision"
    with pytest.raises(ValueError,match="DERIVATIVE_PARENT"):
        c.source_binding(board,row,"hindi",str(source.url))


def test_default_renderer(tmp_path):
    board=demo_spec("technology","SHORT")
    board.specialist_facts[c.KEY]="chart"
    with pytest.raises(ValueError,match="explicit pinned chart renderer"):
        render_board(board,tmp_path/"board.png")


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="CHART_PAIR_INVENTORY"):c.verify((),tmp_path,PIN)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media required")
def test_real_chart_pair(pair_inputs,tmp_path):
    hi=Path(os.environ.get("VIRALOS_CI_HINDI_FONT","/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"))
    en=Path(os.environ.get("VIRALOS_CI_ENGLISH_FONT","/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"))
    if not hi.is_file() or not en.is_file() or not features.check_feature("raqm"):
        if os.environ.get("VIRALOS_REQUIRE_HINDI_PREVIEW")=="1":pytest.fail("required fonts or RAQM missing")
        pytest.skip("owner fonts and RAQM required")
    fonts={"hindi":hi.read_bytes(),"english":en.read_bytes()}
    pins={l:c.sha(v) for l,v in fonts.items()}
    v=values(pair_inputs)
    parent=bp.build(*v)
    pair=v[-1]
    original={l:DraftPlan.model_validate(c.pv.document(pair/l/"draft"/"plan.json")) for l in c.LANGS}
    root=tmp_path/"chart-inputs"
    root.mkdir()
    obj={"schema":c.REQUEST,"pair_sha256":parent["pair_sha256"],"font_sha256":pins,"scenes":[]}
    for i,kind in enumerate(("BAR","LINE"),1):
        folder=root/f"scene_{i:02}"
        folder.mkdir()
        source=original["hindi"].scenes[i-1].board.sources[0]
        ds=data(kind)
        ds["source_reference"]=str(source.url)
        raw=c.json_bytes(ds)
        visual=c.json_bytes(request(c.sha(raw),pins,"SHORT"))
        for name,b in (("source.bin",SOURCE),("data.json",raw),("request.json",visual)):
            (folder/name).write_bytes(b)
        obj["scenes"].append({"scene":i,"source_id":source.source_id,"source_sha256":SP,
            "data_sha256":c.sha(raw),"request_sha256":c.sha(visual),
            "board_sha256":{l:c.board_pin(original[l].scenes[i-1].board) for l in c.LANGS}})
    raw=c.json_bytes(obj)
    inputs=(pair,parent["pair_sha256"],root,raw,c.sha(raw),fonts,pins)
    before={l:c.ps.inventory(pair/l) for l in c.LANGS}
    out=tmp_path/"chart-video"
    result=c.build(inputs,out)
    checked=c.verify(inputs,out,result["chart_pair_sha256"])
    assert checked["duration_ms"]==2080
    assert all(x=={"revision":0,"state":"PENDING"} for x in checked["review_states"].values())
    assert before=={l:c.ps.inventory(pair/l) for l in c.LANGS}
    for lang in c.LANGS:
        assert (out/lang/"draft"/"narration.wav").read_bytes()==(pair/lang/"draft"/"narration.wav").read_bytes()
    with pytest.raises(ValueError):c.build(inputs,out)
    from tools import chart_pair_snapshot as snap,chart_review_dashboard as dashboard
    from app import domain_review_queue as queue
    from fastapi.testclient import TestClient
    import re
    run=out/"hindi"
    pin=result["runs"]["hindi"]["manifest_sha256"]
    review=c.pv.document(run/"review_template.json")
    queue.submit(run/"reviews.sqlite",run/"draft",run/"assets",pin,0,review)
    pair_pin=result["chart_pair_sha256"]
    snapshot=tmp_path/"chart-snapshot"
    saved=snap.backup(inputs,out,pair_pin,snapshot)
    assert saved["review_states"]["hindi"]=={"revision":1,"state":"DEMO_BLOCKED"}
    restored=tmp_path/"chart-restored"
    checked=snap.restore(inputs,snapshot,saved["snapshot_sha256"],pair_pin,restored)
    assert checked["review_states"]==saved["review_states"]
    for lang in c.LANGS:
        assert (restored/lang/"reviews.sqlite").read_bytes()==(out/lang/"reviews.sqlite").read_bytes()
    with TestClient(dashboard.create_app(restored,pair_pin)) as client:
        page=client.get("/")
        assert "Chart-production editorial review" in page.text
        token=re.search(r'name="review-session" content="([0-9a-f]{64})"',page.text).group(1)
        h={"X-Review-Session":token}
        assert client.get("/api/status").status_code==403
        response=client.get("/api/status",headers=h)
        assert response.status_code==200
        assert response.json()["languages"]["hindi"]["revision"]==1
        assert all(s["chart_declaration"] for l in response.json()["languages"].values() for s in l["scenes"])
        assert client.post("/api/submit",headers=h,json={}).status_code==404
        for lang in c.LANGS:
            video=client.get("/api/video/"+lang,headers=h)
            assert video.status_code==200 and c.sha(video.content)==result["runs"][lang]["video_sha256"]
        (restored/"chart_pair.json").write_bytes(b"tamper")
        assert client.get("/api/status",headers=h).status_code==409
    # Use a new review declaration for the previously reviewed Hindi child.
    # Inject a failed second write, prove status/resume and idempotent retry.
    from tools import chart_review_transaction as ct
    obj={"schema":ct.REQUEST,"chart_pair_sha256":pair_pin,"reviews":{}}
    for lang in c.LANGS:
        review=c.pv.document(out/lang/"review_template.json")
        review["reviewer"]="synthetic transaction reviewer"
        obj["reviews"][lang]={"revision":saved["review_states"][lang]["revision"],"review":review}
    request_raw=c.json_bytes(obj)
    txbase=(inputs,out,pair_pin,request_raw,c.sha(request_raw))
    plan=ct.prepare(*txbase)
    txargs=(*txbase,plan,c.sha(plan))
    assert ct.reconcile(*txargs)=={"hindi":"PENDING","english":"PENDING"}
    submit=ct.tx.queue.submit
    def fail_english(path,*a,**kw):
        if path.parent.name=="english":raise RuntimeError("simulated interruption")
        return submit(path,*a,**kw)
    from unittest.mock import patch
    with patch.object(ct.tx.queue,"submit",side_effect=fail_english):
        with pytest.raises(RuntimeError,match="simulated interruption"):ct.apply(*txargs)
    assert ct.reconcile(*txargs)=={"hindi":"RECORDED","english":"PENDING"}
    assert ct.apply(*txargs)["completed"]
    assert ct.reconcile(*txargs)=={"hindi":"RECORDED","english":"RECORDED"}
    assert ct.apply(*txargs)["cross_database_atomic"] is False
    from tools import chart_scene_transition as transition
    transition_raw=c.json_bytes({"schema":transition.REQUEST,"chart_pair_sha256":pair_pin,
                                 "effect":transition.EFFECT,"fade_frames":3})
    transition_dest=tmp_path/"chart-transition"
    transition_args=(inputs,out,pair_pin,transition_raw,c.sha(transition_raw),transition_dest)
    transition_report=transition.build(*transition_args)
    transition_check=transition.verify(*transition_args,transition_report["transition_pair_sha256"])
    assert transition_check["frames_compared"]=={"hindi":52,"english":52}
    assert transition_check["presentation_timestamps_verified"] and not transition_check["publication_eligible"]
    (transition_dest/"hindi"/"captions.vtt").write_bytes(b"tamper")
    with pytest.raises(ValueError):transition.verify(*transition_args,transition_report["transition_pair_sha256"])
    from tools import chart_pair_motion as motion
    motion_raw=c.json_bytes({"schema":motion.REQUEST,"chart_pair_sha256":pair_pin,
                             "effect":"VALUE_ROW_HIGHLIGHT_V1"})
    motion_dest=tmp_path/"chart-motion"
    motion_args=(inputs,out,pair_pin,motion_raw,c.sha(motion_raw),motion_dest)
    motion_report=motion.build(*motion_args)
    motion_check=motion.verify(*motion_args,motion_report["motion_pair_sha256"])
    assert motion_check["frames_compared"]=={"hindi":52,"english":52}
    assert motion_check["fresh_media_audit"] and not motion_check["publication_eligible"]
    from tools import chart_motion_review as cmr
    args=(*motion_args,motion_report["motion_pair_sha256"])
    handoff=tmp_path/"chart-motion-handoff"
    hand=cmr.prepare(args,handoff)
    packets=cmr.verify(args,handoff,hand["handoff_sha256"])
    reviews={}
    for lang in c.LANGS:
        review=cmr.template(packets[lang])
        review["reviewer"]="synthetic motion reviewer"
        for row in review["scenes"]:row["checks"]=dict.fromkeys(cmr.CHECKS,"PASS")
        reviews[lang]=c.json_bytes(review)
    assessed=cmr.evaluate_packets(packets,reviews,{l:c.sha(raw) for l,raw in reviews.items()},hand["handoff_sha256"])
    assert not assessed["both_self_attested_checklists_complete"] and not assessed["publication_eligible"]
    from tools import chart_motion_snapshot as cms
    motion_snapshot=tmp_path/"chart-motion-snapshot"
    motion_saved=cms.backup(args,handoff,hand["handoff_sha256"],motion_snapshot)
    motion_restored=tmp_path/"chart-motion-restored"
    assert cms.restore((*args[:5],None,args[6]),motion_snapshot,motion_saved["snapshot_sha256"],
                       hand["handoff_sha256"],motion_restored)["fresh_media_audit"]
    assert cms.inventory(motion_restored/"motion",motion_restored/"handoff")==cms.inventory(motion_dest,handoff)
    (motion_dest/"english"/"captions.vtt").write_bytes(b"tamper")
    with pytest.raises(ValueError):motion.verify(*motion_args,motion_report["motion_pair_sha256"])
    (snapshot/"english"/"payload"/"draft"/"draft.mp4").write_bytes(b"tamper")
    with pytest.raises(ValueError):snap.inspect(snapshot,saved["snapshot_sha256"],pair_pin)
    (root/"scene_01"/"source.bin").write_bytes(b"changed")
    with pytest.raises(ValueError):ct.apply(*txargs)
    with pytest.raises(ValueError):c.verify(inputs,out,result["chart_pair_sha256"])
