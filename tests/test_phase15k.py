"""Scene-lag regression and paired mixed production contracts."""
from array import array
import copy
import json
import math
import random
import shutil

import pytest
from app.m25_audio_conformance import _waveform_score
from tools import paired_production_mix as p
from tools import bilingual_pilot as bp
from tools.domain_storyboard import demo_spec
from test_bilingual_compose import inputs, args, save
from test_production_mix_pilot import request
from test_narration_prepare import tone

PAIR="a"*64


@pytest.mark.parametrize("freq",[250,300,301,302,330,400])
def test_periodic_scene_near_sync(freq):
    raw=array("h",(round(5000*math.sin(2*math.pi*freq*i/16000)) for i in range(32000)))
    score,lag,coverage=_waveform_score(raw,raw,scene_sync=True)
    assert score>=.99 and abs(lag)<=100 and coverage>=.8


@pytest.mark.parametrize("offset",[-300,-200,200,300])
def test_distinct_delays_not_hidden(offset):
    rng=random.Random(92)
    raw=array("h",(rng.randrange(-6000,6001) for _ in range(32000)))
    n=abs(offset)*16
    got=(array("h",[0])*n+raw[:-n]) if offset>0 else (raw[n:]+array("h",[0])*n)
    score,lag,coverage=_waveform_score(raw,got,scene_sync=True)
    assert score>.99 and lag==offset and abs(lag)>100


def test_wrong_signal_not_accepted():
    a=random.Random(1)
    b=random.Random(2)
    x=array("h",(a.randrange(-5000,5001) for _ in range(32000)))
    y=array("h",(b.randrange(-5000,5001) for _ in range(32000)))
    assert _waveform_score(x,y,scene_sync=True)[0]<.65


def req():
    return {"schema":p.REQUEST,"pair_sha256":PAIR,"native_sha256":None,
            "tracks":{"hindi":request("STATIC",parent="b"*64),
                      "english":request("DUCK",parent="c"*64)}}


def validate(obj):
    raw=bp.json_bytes(obj)
    return p.validate(raw,p.sha(raw),PAIR,None)


@pytest.mark.parametrize("field,value",[
    ("schema","bad"),("pair_sha256","0"*64),("pair_sha256",None),("native_sha256","d"*64),
    ("tracks",None),("tracks",[]),("tracks",{}),("tracks",{"hindi":{}}),("extra",True)])
def test_request_fields(field,value):
    obj=req()
    obj[field]=value
    with pytest.raises(ValueError):validate(obj)


@pytest.mark.parametrize("lang",p.LANGS)
@pytest.mark.parametrize("field,value",[("schema","bad"),("parent_manifest_sha256","bad"),
    ("mode","WRONG"),("audio_request",None),("audio_request",[]),("extra",1)])
def test_track_request(lang,field,value):
    obj=req()
    obj["tracks"][lang][field]=value
    with pytest.raises(ValueError):validate(obj)


@pytest.mark.parametrize("lang",p.LANGS)
@pytest.mark.parametrize("field,value",[("music_rights_attested",False),("music_sha256","bad"),
    ("license_reference",""),("ceiling_dbtp",0),("fade_ms",True)])
def test_track_music(lang,field,value):
    obj=req()
    row=obj["tracks"][lang]
    cfg=row["audio_request"] if row["mode"]=="STATIC" else row["audio_request"]["mix"]
    cfg[field]=value
    with pytest.raises(ValueError):validate(obj)


def test_request_valid():
    rows=validate(req())
    assert set(rows)==set(p.LANGS)


def test_duplicate_parent():
    obj=req()
    obj["tracks"]["english"]["parent_manifest_sha256"]="b"*64
    with pytest.raises(ValueError,match="DUPLICATE_PARENT"):validate(obj)


@pytest.mark.parametrize("bad",["","0"*64,"A"*64,"g"*64])
def test_pin(bad):
    with pytest.raises(ValueError):p.validate(bp.json_bytes(req()),bad,PAIR,None)


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="PAIR_MIX_INVENTORY"):
        p.verify(tmp_path,PAIR,None,None,b"x",p.sha(b"x"),{},tmp_path,"0"*64)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media required")
def test_real_pair(inputs,tmp_path):
    root,timing,caps,bundle=inputs
    for row in timing["scenes"]:
        for lang in p.LANGS:
            tr=row[lang]
            raw=tone(seconds=2,frequency=270+row["scene"]+(40 if lang=="english" else 0))
            (root/tr["file"]).write_bytes(raw)
            tr["sha256"]=bp.sha(raw)
    caps["timing_request_sha256"]=bp.sha(json.dumps(timing).encode())
    saved=save(inputs)
    board=demo_spec("technology","SHORT").model_dump()
    boards={"schema":bp.BOARD_SCHEMA,"bundle_manifest_sha256":saved["manifest_sha256"],
            "scenes":[{"scene":i,"hindi":copy.deepcopy(board),"english":copy.deepcopy(board),
                       "rights_attested":{"hindi":True,"english":True}} for i in (1,2)]}
    raw=bp.json_bytes(boards)
    pair=tmp_path/"pair"
    built=bp.build(*args(inputs),bundle,saved["manifest_sha256"],raw,bp.sha(raw),pair)
    music={lang:tone(seconds=4,frequency=450+(20 if lang=="english" else 0),amplitude=2000)
           for lang in p.LANGS}
    obj={"schema":p.REQUEST,"pair_sha256":built["pair_sha256"],"native_sha256":None,"tracks":{}}
    for lang in p.LANGS:
        obj["tracks"][lang]=request("STATIC" if lang=="hindi" else "DUCK",
             (pair/lang/"draft"/"narration.wav").read_bytes(),music[lang],built["runs"][lang]["manifest_sha256"])
    raw=bp.json_bytes(obj)
    before={lang:p.ps.inventory(pair/lang) for lang in p.LANGS}
    out=tmp_path/"mixed"
    values=(pair,built["pair_sha256"],None,None,raw,p.sha(raw),music,out)
    result=p.build(*values)
    assert result["duration_ms"]==4000
    checked=p.verify(*values,result["pair_mix_sha256"])
    assert all(row=={"revision":0,"state":"PENDING"} for row in checked["review_states"].values())
    assert before=={lang:p.ps.inventory(pair/lang) for lang in p.LANGS}
    from tools import paired_mix_snapshot as snap
    snapshot=tmp_path/"mix-snapshot"
    pair_mix_pin=result["pair_mix_sha256"]
    saved=snap.backup(values[:-1],out,pair_mix_pin,snapshot)
    restored=tmp_path/"restored-mix"
    report=snap.restore(values[:-1],snapshot,saved["snapshot_sha256"],pair_mix_pin,restored)
    assert report["fresh_media_audit"] and report["review_states"]==saved["review_states"]
    for lang in p.LANGS:
        assert (out/lang/"run"/"reviews.sqlite").read_bytes()==(restored/lang/"run"/"reviews.sqlite").read_bytes()
        assert (out/lang/"mix.json").read_bytes()==(restored/lang/"mix.json").read_bytes()
    (snapshot/"english"/"run"/"payload"/"draft"/"draft.mp4").write_bytes(b"tamper")
    with pytest.raises(ValueError):
        snap.inspect(snapshot,saved["snapshot_sha256"],pair_mix_pin)
    import re
    from fastapi.testclient import TestClient
    from tools import mixed_review_dashboard as mixed_dash
    client=TestClient(mixed_dash.create_app(restored,pair_mix_pin))
    page=client.get("/")
    token=re.search(r'name="review-session" content="([0-9a-f]{64})"',page.text).group(1)
    headers={"X-Review-Session":token}
    status=client.get("/api/status",headers=headers)
    assert status.status_code==200
    assert all(s["mixed_audio"] for row in status.json()["languages"].values() for s in row["scenes"])
    assert client.get("/api/status").status_code==403
    for lang in p.LANGS:
        video=client.get("/api/video/"+lang,headers=headers)
        assert video.status_code==200 and p.sha(video.content)==result["tracks"][lang]["video_sha256"]
    assert client.post("/api/submit",headers=headers,json={}).status_code==404
    (restored/"english"/"mix.json").write_bytes(b"tamper")
    assert client.get("/api/status",headers=headers).status_code==409
    (out/"english"/"mix.json").write_bytes(b"tamper")
    with pytest.raises(ValueError):p.verify(*values,result["pair_mix_sha256"])
