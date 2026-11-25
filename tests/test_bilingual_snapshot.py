import copy
import shutil
import pytest
from tools import bilingual_snapshot as s
from tools import bilingual_pilot as p
from test_bilingual_compose import inputs
from test_bilingual_pilot import pair_inputs, values


def pair():
    return {"schema":p.SCHEMA,"publication_eligible":False,"runs":{
        "hindi":{"manifest_sha256":"a"*64,"video_sha256":"b"*64,"duration_ms":2080},
        "english":{"manifest_sha256":"c"*64,"video_sha256":"d"*64,"duration_ms":2080}}}


def records(obj):
    raw=p.json_bytes(obj)
    return s.pair_records(raw,p.sha(raw))


@pytest.mark.parametrize("field,value",[
    ("schema","bad"),("publication_eligible",True),("publication_eligible",0),
    ("runs",None),("runs",[]),("runs",{}),("runs",{"hindi":{}})
])
def test_bad_pair(field,value):
    obj=pair()
    obj[field]=value
    with pytest.raises(ValueError):
        records(obj)


@pytest.mark.parametrize("field,value",[
    ("manifest_sha256",""),("manifest_sha256","x"*64),("manifest_sha256","A"*64),
    ("video_sha256",None),("video_sha256","a"*63),("duration_ms",0),
    ("duration_ms",120001),("duration_ms",True),("duration_ms",2080.0),("extra",1)
])
def test_bad_child(field,value):
    obj=pair()
    obj["runs"]["hindi"][field]=value
    with pytest.raises(ValueError):
        records(obj)


def test_duplicate():
    obj=pair()
    obj["runs"]["english"]["manifest_sha256"]="a"*64
    with pytest.raises(ValueError,match="PAIR_DUPLICATE"):
        records(obj)


@pytest.mark.parametrize("pin",["","0"*64,"A"*64,"z"*64])
def test_pair_pin(pin):
    with pytest.raises(ValueError):
        s.pair_records(p.json_bytes(pair()),pin)


def test_incomplete_snapshot(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="PAIR_SNAPSHOT_INVENTORY"):
        s.inspect(tmp_path,"a"*64,"b"*64)


def test_output_inside_source(pair_inputs):
    v=values(pair_inputs)
    src=v[-1]
    src.mkdir()
    with pytest.raises(ValueError,match="OVERLAPPING_PATH"):
        s.backup(v[:-1],src,"0"*64,src/"nested")


def test_output_inside_bundle(pair_inputs):
    v=values(pair_inputs)
    src=v[-1]
    src.mkdir()
    with pytest.raises(ValueError,match="OVERLAPPING_PATH"):
        s.backup(v[:-1],src,"0"*64,v[5]/"nested")


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="real local FFmpeg required")
def test_pair_snapshot_roundtrip(pair_inputs,tmp_path):
    v=values(pair_inputs)
    original=p.build(*v)
    pair_pin=original["pair_sha256"]
    src=v[-1]
    snapshot=tmp_path/"snapshot"
    saved=s.backup(v[:-1],src,pair_pin,snapshot)
    pin=saved["snapshot_sha256"]
    meta=s.inspect(snapshot,pin,pair_pin)
    assert all(meta["children"][lang]["revision"]==0 for lang in p.LANGS)
    restored=tmp_path/"restored"
    result=s.restore(v[:-1],snapshot,pin,pair_pin,restored)
    assert result["fresh_media_audit"] and not result["publication_eligible"]
    assert result["review_states"]==saved["review_states"]
    assert (restored/"pair.json").read_bytes()==(src/"pair.json").read_bytes()
    for lang in p.LANGS:
        assert (restored/lang/"reviews.sqlite").read_bytes()==(src/lang/"reviews.sqlite").read_bytes()
        assert (restored/lang/"catalog.json").read_bytes()!=(src/lang/"catalog.json").read_bytes()
    assert s.inspect(snapshot,pin,pair_pin)==meta
    with pytest.raises(ValueError):
        s.restore(v[:-1],snapshot,pin,pair_pin,restored)
    (snapshot/"english"/"payload"/"draft"/"draft.mp4").write_bytes(b"tamper")
    with pytest.raises(ValueError):
        s.inspect(snapshot,pin,pair_pin)
