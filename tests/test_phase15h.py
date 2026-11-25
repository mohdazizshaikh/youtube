import json
import os
import shutil
from pathlib import Path
import pytest
from PIL import features
from app.domain_draft_video import DraftPlan
from tools import native_pilot_snapshot as s, native_hindi_pilot as nh, bilingual_pilot as p
from tools import bilingual_review_preflight as r, narration_mix as m
from test_bilingual_compose import inputs
from test_bilingual_pilot import pair_inputs, values
from test_narration_prepare import tone

PAIR="a"*64
NATIVE="b"*64


def receipts():
    pair={"schema":p.SCHEMA,"publication_eligible":False,"runs":{
        "hindi":{"manifest_sha256":"c"*64,"video_sha256":"d"*64,"duration_ms":2080},
        "english":{"manifest_sha256":"e"*64,"video_sha256":"f"*64,"duration_ms":2080}}}
    raw=p.json_bytes(pair)
    native={"schema":nh.SCHEMA,"parent_pair_sha256":p.sha(raw),
        "parent_hindi_manifest_sha256":"c"*64,"english_manifest_sha256":"e"*64,
        "manifest_sha256":"1"*64,"video_sha256":"2"*64,"duration_ms":2080,
        "font_sha256":"3"*64,"request_sha256":"4"*64,"publication_eligible":False,
        "native_visual_accepted":False,"visual_mode":"DEVANAGARI_RAQM_TEXT_CARDS"}
    return raw,native


@pytest.mark.parametrize("key,value",[
    ("schema","bad"),("parent_pair_sha256","0"*64),("parent_hindi_manifest_sha256","0"*64),
    ("english_manifest_sha256","0"*64),("manifest_sha256","c"*64),("manifest_sha256","e"*64),
    ("manifest_sha256","z"*64),("video_sha256",None),("font_sha256","bad"),
    ("request_sha256","bad"),("duration_ms",1000),("publication_eligible",True),
    ("native_visual_accepted",True),("visual_mode","ASCII_ONLY")])
def test_native_binding(key,value):
    raw,native=receipts()
    native[key]=value
    n=p.json_bytes(native)
    with pytest.raises(ValueError):
        s.receipt_records(raw,p.sha(raw),n,p.sha(n))


def test_native_receipts():
    raw,native=receipts()
    n=p.json_bytes(native)
    assert s.receipt_records(raw,p.sha(raw),n,p.sha(n))=={
        "original_hindi":"c"*64,"english":"e"*64,"native_hindi":"1"*64}


def test_incomplete_snapshot(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="SNAPSHOT_INVENTORY"):
        s.inspect(tmp_path,"0"*64,PAIR,NATIVE)


def review_request():
    return {"schema":r.SCHEMA,"pair_sha256":PAIR,"native_sha256":None,
            "reviews":{l:{"revision":0,"review":{}} for l in p.LANGS}}


@pytest.mark.parametrize("key,value",[
    ("schema","bad"),("pair_sha256","0"*64),("native_sha256",NATIVE),
    ("reviews",[]),("reviews",{}),("reviews",{"hindi":{}}),("extra",1)])
def test_review_request(key,value):
    obj=review_request()
    obj[key]=value
    raw=p.json_bytes(obj)
    with pytest.raises(ValueError):
        r.validate(raw,p.sha(raw),PAIR,None)


@pytest.mark.parametrize("value",[-1,True,0.0,100000,"0",None])
def test_review_revision(value):
    obj=review_request()
    obj["reviews"]["hindi"]["revision"]=value
    raw=p.json_bytes(obj)
    with pytest.raises(ValueError):
        r.validate(raw,p.sha(raw),PAIR,None)


@pytest.mark.parametrize("value",[None,[],True,"review"])
def test_review_envelope(value):
    obj=review_request()
    obj["reviews"]["english"]["review"]=value
    raw=p.json_bytes(obj)
    with pytest.raises(ValueError):
        r.validate(raw,p.sha(raw),PAIR,None)


def mix_request(voice=b"voice",music=b"music"):
    return {"schema":m.SCHEMA,"voice_sha256":p.sha(voice),"music_sha256":p.sha(music),
            "music_rights_attested":True,"license_reference":"owner declaration",
            "music_relative_lufs":-24,"fade_ms":150,"ceiling_dbtp":-3}


@pytest.mark.parametrize("key,value",[
    ("schema","bad"),("voice_sha256","bad"),("music_sha256","bad"),
    ("music_rights_attested",False),("music_rights_attested",1),
    ("license_reference",""),("license_reference",None),("license_reference","a"*301),
    ("license_reference","abc\nxyz"),("music_relative_lufs",-17),("music_relative_lufs",-37),
    ("music_relative_lufs",True),("music_relative_lufs",None),("fade_ms",49),
    ("fade_ms",1001),("fade_ms",50.0),("fade_ms",True),("ceiling_dbtp",0),
    ("ceiling_dbtp",-7),("ceiling_dbtp",False),("extra",1)])
def test_mix_request(key,value):
    obj=mix_request()
    obj[key]=value
    raw=p.json_bytes(obj)
    with pytest.raises(ValueError):
        m.validate(raw,p.sha(raw))


@pytest.mark.parametrize("v,b,relative,expected",[(-20,-10,-24,-34),(-20,-60,-24,0),(-16,-16,-18,-18)])
def test_music_gain(v,b,relative,expected):
    assert m.gain_for_music(v,b,relative)==expected


def test_excessive_music_gain():
    with pytest.raises(ValueError):
        m.gain_for_music(-80,-2,-36)


def test_mix_mismatch():
    v,b=tone(seconds=3),tone(seconds=4,frequency=500)
    raw=p.json_bytes(mix_request(v,b))
    with pytest.raises(ValueError,match="MIX_LENGTH"):
        m.mix(v,b,raw,p.sha(raw))


def test_mix_identical():
    v=tone(seconds=3)
    raw=p.json_bytes(mix_request(v,v))
    with pytest.raises(ValueError,match="MIX_DUPLICATE"):
        m.mix(v,v,raw,p.sha(raw))


@pytest.mark.skipif(not shutil.which("ffmpeg"),reason="local FFmpeg required")
def test_real_mix():
    v,b=tone(seconds=4),tone(seconds=4,frequency=500,amplitude=2000)
    raw=p.json_bytes(mix_request(v,b))
    out,report=m.mix(v,b,raw,p.sha(raw))
    assert report["timing_preserved"] and report["output"]["frames"]==64000
    assert report["output"]["true_peak_dbtp"]<=-3
    assert m.samples(out)[0]==m.samples(v)[0] and m.samples(out)[-1]==m.samples(v)[-1]
    assert not report["publication_eligible"] and not report["professional_mix_verified"]


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media tools required")
def test_native_recovery_and_review(pair_inputs,tmp_path):
    font_path=Path(os.environ.get("VIRALOS_CI_HINDI_FONT","/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"))
    if not font_path.is_file() or not features.check_feature("raqm"):
        if os.environ.get("VIRALOS_REQUIRE_HINDI_PREVIEW")=="1":
            pytest.fail("required CI font or RAQM absent")
        pytest.skip("local font and RAQM required")
    font=font_path.read_bytes()
    v=values(pair_inputs)
    parent=p.build(*v)
    pair=v[-1]
    pair_pin=parent["pair_sha256"]
    plan=DraftPlan.model_validate(nh.pv.document(pair/"hindi"/"draft"/"plan.json"))
    obj={"schema":nh.REQUEST,"pair_sha256":pair_pin,"font_sha256":p.sha(font),
         "font_rights_attested":True,"license_reference":"CI test fixture",
         "scenes":[{"scene":i,"title":"हिन्दी दृश्य परीक्षण",
                    "claims":["यह एक परीक्षण है"]*len(scene.board.claims)}
                    for i,scene in enumerate(plan.scenes,1)]}
    request=p.json_bytes(obj)
    native=tmp_path/"native"
    n=nh.build(pair,pair_pin,font,p.sha(font),request,p.sha(request),native)
    native_pin=n["native_sha256"]
    rv={"schema":r.SCHEMA,"pair_sha256":pair_pin,"native_sha256":native_pin,"reviews":{}}
    for lang,run in (("hindi",native/"hindi"),("english",pair/"english")):
        rv["reviews"][lang]={"revision":0,"review":nh.pv.document(run/"review_template.json")}
    raw=p.json_bytes(rv)
    before={k:(path/"reviews.sqlite").read_bytes() for k,path in s.source_runs(pair,native).items()}
    result=r.preflight(pair,pair_pin,raw,p.sha(raw),native,native_pin)
    assert result["both_envelopes_valid"] and not result["queues_modified"]
    assert all(x["proposed_state"]=="DEMO_BLOCKED" for x in result["languages"].values())
    assert before=={k:(path/"reviews.sqlite").read_bytes() for k,path in s.source_runs(pair,native).items()}
    snapshot=tmp_path/"snapshot"
    saved=s.backup(pair,pair_pin,font,p.sha(font),request,p.sha(request),native,native_pin,snapshot)
    restored=tmp_path/"restored"
    result=s.restore(snapshot,saved["snapshot_sha256"],pair_pin,native_pin,font,p.sha(font),
                     request,p.sha(request),restored)
    assert result["fresh_media_audit"] and result["review_states"]==saved["review_states"]
    assert before=={k:(path/"reviews.sqlite").read_bytes()
                   for k,path in s.source_runs(restored/"pair",restored/"native").items()}
    (snapshot/"native_hindi"/"payload"/"draft"/"draft.mp4").write_bytes(b"tamper")
    with pytest.raises(ValueError):
        s.inspect(snapshot,saved["snapshot_sha256"],pair_pin,native_pin)
