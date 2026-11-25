"""Native derivative contracts and real synthetic font + FFmpeg rendering."""
import os
from pathlib import Path
import shutil
import pytest
from PIL import features
from app.domain_draft_video import DraftPlan
from app.domain_storyboards import render_board
from tools import native_hindi_pilot as n, bilingual_pilot as p
from tools.domain_storyboard import demo_spec
from test_bilingual_compose import inputs
from test_bilingual_pilot import pair_inputs, values

PAIR="a"*64
FONT="b"*64


def plan():
    return DraftPlan.model_validate({"scenes":[{"board":demo_spec("technology","SHORT").model_dump(),
        "narration_file":f"voice{i}.wav","narration_sha256":"c"*64,
        "narration_text":"यह एक परीक्षण है","rights_attested":True} for i in (1,2)]})


def request():
    return {"schema":n.REQUEST,"pair_sha256":PAIR,"font_sha256":FONT,
            "font_rights_attested":True,"license_reference":"owner declaration",
            "scenes":[{"scene":i,"title":"हिन्दी दृश्य परीक्षण",
                       "claims":["यह एक परीक्षण है"]*len(plan().scenes[i-1].board.claims)} for i in (1,2)]}


def rows(obj):
    raw=p.json_bytes(obj)
    return n.request_rows(raw,n.sha(raw),PAIR,FONT,plan())


@pytest.mark.parametrize("field,value",[
    ("schema","bad"),("pair_sha256","0"*64),("font_sha256","0"*64),
    ("font_rights_attested",False),("font_rights_attested",1),("font_rights_attested","yes"),
    ("license_reference",""),("license_reference",None),("license_reference","a"*301),
    ("license_reference","abc\nxyz"),("scenes",None),("scenes",[]),("scenes",{}),
    ("extra",True)])
def test_request_fields(field,value):
    obj=request()
    obj[field]=value
    with pytest.raises(ValueError):
        rows(obj)


@pytest.mark.parametrize("field,value",[
    ("scene",0),("scene",2),("scene",True),("scene",1.0),("extra",1),
    ("title","English only"),("title",""),("title",None),("title"," हिंदी"),
    ("title","हिन्दी\nपरीक्षण"),("title","हिन्दी\u202eपरीक्षण"),("title","हिन्दी"*30),
    ("claims",[]),("claims",{}),("claims",None),("claims",["English"]),
    ("claims",["हिन्दी"]*3),("claims",[True]),("claims",["हिन्दी"*40])
])
def test_scene_fields(field,value):
    obj=request()
    obj["scenes"][0][field]=value
    with pytest.raises(ValueError):
        rows(obj)


@pytest.mark.parametrize("bad",["","0"*64,"A"*64,"g"*64])
def test_request_pin(bad):
    raw=p.json_bytes(request())
    with pytest.raises(ValueError):
        n.request_rows(raw,bad,PAIR,FONT,plan())


def test_valid_rows():
    visual=rows(request())
    assert len(visual)==2
    assert all(n.pv.decode(raw)["font_sha256"]==FONT for raw in visual)


def test_legacy_renderer_refuses_native_declaration(tmp_path):
    board=plan().scenes[0].board
    board.specialist_facts[n.KEY]="native"
    with pytest.raises(ValueError,match="explicit native renderer"):
        render_board(board,tmp_path/"board.png")
    assert not (tmp_path/"board.png").exists()


def test_native_renderer_hash_binding(tmp_path):
    board=plan().scenes[0].board
    raw=b"test declaration"
    board.specialist_facts[n.KEY]=raw.decode()
    png=b"fixture"
    dest=tmp_path/"board.png"
    report=n.renderer({n.sha(raw):png})(board,dest)
    assert report["board_sha256"]==n.sha(dest.read_bytes())
    with pytest.raises(FileExistsError):
        n.renderer({n.sha(raw):png})(board,dest)


def test_reserved_declaration_collision():
    pl=plan()
    pl.scenes[0].board.specialist_facts[n.KEY]="collision"
    raw=b"font"
    with pytest.raises(ValueError,match="NATIVE_DECLARATION_EXISTS"):
        n.plans_and_pngs(pl,rows(request()),raw,n.sha(raw),"a"*64,PAIR)


def test_invalid_parent_no_output(tmp_path):
    parent=tmp_path/"pair"
    parent.mkdir()
    raw=b"font"
    with pytest.raises(ValueError,match="PAIR_INVENTORY"):
        n.build(parent,PAIR,raw,n.sha(raw),b"x",n.sha(b"x"),tmp_path/"new")
    assert not (tmp_path/"new").exists()


def test_output_overlap(tmp_path):
    parent=tmp_path/"pair"
    parent.mkdir()
    with pytest.raises(ValueError,match="OVERLAPPING_OUTPUT"):
        n.build(parent,PAIR,b"x",n.sha(b"x"),b"x",n.sha(b"x"),parent/"new")


def test_incomplete_derivative(tmp_path):
    parent=tmp_path/"pair"
    parent.mkdir()
    out=tmp_path/"native"
    out.mkdir()
    (out/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="NATIVE_INVENTORY"):
        n.verify(parent,PAIR,b"x",n.sha(b"x"),b"x",n.sha(b"x"),out,"0"*64)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media tools required")
@pytest.mark.parametrize("mode",[n.TEXT_MODE,n.FLOW_MODE])
def test_real_native_derivative(pair_inputs,tmp_path,mode):
    font=Path(os.environ.get("VIRALOS_CI_HINDI_FONT","/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"))
    if not font.is_file() or not features.check_feature("raqm"):
        if os.environ.get("VIRALOS_REQUIRE_HINDI_PREVIEW")=="1":
            pytest.fail("required CI font or RAQM absent")
        pytest.skip("owner font and RAQM required")
    data=font.read_bytes()
    v=values(pair_inputs)
    parent=p.build(*v)
    pair=v[-1]
    old=(pair/"hindi"/"draft"/"manifest.json").read_bytes()
    obj=request()
    original=DraftPlan.model_validate(n.pv.document(pair/"hindi"/"draft"/"plan.json"))
    obj.update(pair_sha256=parent["pair_sha256"],font_sha256=n.sha(data))
    for row,scene in zip(obj["scenes"],original.scenes):
        if mode==n.FLOW_MODE:
            obj["schema"]=n.FLOW_REQUEST
            del row["claims"]
            import json
            row["source_declaration_sha256"]=n.sha(json.dumps(scene.board.model_dump(),sort_keys=True,ensure_ascii=False).encode())
            row["nodes"]=[{"step":1,"label":"जानकारी एकत्र करें"},{"step":2,"label":"तथ्य जाँच करें"},{"step":3,"label":"परिणाम समझाएँ"}]
        else:
            row["claims"]=["यह एक परीक्षण है"]*len(scene.board.claims)
    raw=p.json_bytes(obj)
    out=tmp_path/"native"
    args=(pair,parent["pair_sha256"],data,n.sha(data),raw,n.sha(raw),out)
    result=n.build(*args)
    assert result["duration_ms"]==2080
    assert (out/"hindi"/"draft"/"draft.mp4").stat().st_size>0
    assert result["manifest_sha256"]!=parent["runs"]["hindi"]["manifest_sha256"]
    assert (pair/"hindi"/"draft"/"manifest.json").read_bytes()==old
    checked=n.verify(*args,result["native_sha256"])
    assert checked["fresh_media_audit"] and not checked["publication_eligible"]
    assert checked["review_states"]["hindi"]=={"revision":0,"state":"PENDING"}
    assert n.pv.document(out/"native.json")["visual_mode"]==mode
    from tools import bilingual_review_dashboard as dash, native_pilot_snapshot as ns
    assert dash.select_runs(pair,parent["pair_sha256"],out,result["native_sha256"])[0]["hindi"][1]==result["manifest_sha256"]
    assert ns.receipt_records((pair/"pair.json").read_bytes(),parent["pair_sha256"],(out/"native.json").read_bytes(),result["native_sha256"])["native_hindi"]==result["manifest_sha256"]
    if mode==n.FLOW_MODE:
        from tools import native_flow_motion as motion
        req=p.json_bytes({"schema":motion.REQUEST,"native_sha256":result["native_sha256"],
                          "effect":"STEP_HIGHLIGHT_V1"})
        inputs=(*args,result["native_sha256"],req,p.sha(req))
        dest=tmp_path/"motion"
        report=motion.build(inputs,dest)
        check=motion.verify(inputs,dest,report["motion_sha256"])
        assert check["frames_compared"]==52 and check["decoded_parent_audio_equal"]
        assert not check["publication_eligible"]
        from tools import motion_review as mr,motion_snapshot as ms
        handoff=tmp_path/"handoff"
        motion_pin=report["motion_sha256"]
        hand=mr.prepare(inputs,dest,motion_pin,handoff)
        packet_pin=hand["packet_file_sha256"]
        packet=mr.verify_handoff(inputs,dest,motion_pin,handoff,packet_pin)
        review=mr.template(packet)
        review["reviewer"]="synthetic reviewer"
        for row in review["scenes"]:row["checks"]=dict.fromkeys(mr.CHECKS,"PASS")
        raw=p.json_bytes(review)
        assessed=mr.evaluate_packet(packet,raw,p.sha(raw))
        assert not assessed["self_attested_checklist_complete"] and not assessed["publication_eligible"]
        snapshot=tmp_path/"motion-snapshot"
        saved=ms.backup(inputs,dest,motion_pin,handoff,packet_pin,snapshot)
        restored=tmp_path/"motion-restored"
        restored_report=ms.restore(inputs,snapshot,saved["snapshot_sha256"],motion_pin,packet_pin,restored)
        assert restored_report["fresh_media_audit"]
        assert (restored/"motion"/"motion.mp4").read_bytes()==(dest/"motion.mp4").read_bytes()
        assert (restored/"handoff"/"packet.json").read_bytes()==(handoff/"packet.json").read_bytes()
        (snapshot/"motion"/"captions.vtt").write_bytes(b"tamper")
        with pytest.raises(ValueError):
            ms.inspect(snapshot,saved["snapshot_sha256"],motion_pin,packet_pin)
        (dest/"captions.vtt").write_bytes(b"tamper")
        with pytest.raises(ValueError):
            motion.verify(inputs,dest,report["motion_sha256"])
    with pytest.raises(ValueError):
        n.verify(*args,"0"*64)
    (out/"hindi"/"draft"/"scene_01.png").write_bytes(b"tamper")
    with pytest.raises(ValueError):
        n.verify(*args,result["native_sha256"])
