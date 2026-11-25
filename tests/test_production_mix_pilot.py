import shutil
import pytest
from tools import production_mix_pilot as p, pilot_pipeline as pp
from tools.domain_storyboard import demo_spec
from app.domain_draft_video import DraftPlan
from app.domain_storyboards import render_board
from test_narration_prepare import tone
from test_phase15h import mix_request
from test_phase15i import duck_request

PARENT="a"*64


def request(mode="STATIC",voice=b"voice",music=b"music",parent=PARENT):
    return {"schema":p.REQUEST,"parent_manifest_sha256":parent,"mode":mode,
            "audio_request":mix_request(voice,music) if mode=="STATIC" else duck_request(voice,music)}


def validate(obj):
    raw=p.json_bytes(obj)
    return p.validate(raw,p.sha(raw),PARENT)


@pytest.mark.parametrize("mode",["STATIC","DUCK"])
def test_request_valid(mode):
    obj=request(mode)
    assert validate(obj)[0]==obj


@pytest.mark.parametrize("key,value",[
    ("schema","bad"),("parent_manifest_sha256","0"*64),("parent_manifest_sha256",None),
    ("mode","OTHER"),("mode","static"),("mode",None),("mode",True),
    ("audio_request",None),("audio_request",[]),("audio_request",{}),("extra",1)])
def test_request_fields(key,value):
    obj=request()
    obj[key]=value
    with pytest.raises(ValueError):
        validate(obj)


@pytest.mark.parametrize("pin",["","0"*64,"A"*64,"g"*64])
def test_request_pin(pin):
    with pytest.raises(ValueError):
        p.validate(p.json_bytes(request()),pin,PARENT)


@pytest.mark.parametrize("mode",["STATIC","DUCK"])
@pytest.mark.parametrize("field,value",[("music_rights_attested",False),("music_rights_attested",1),
    ("music_sha256","bad"),("license_reference",""),("ceiling_dbtp",0),("fade_ms",True)])
def test_nested_mix(mode,field,value):
    obj=request(mode)
    cfg=obj["audio_request"] if mode=="STATIC" else obj["audio_request"]["mix"]
    cfg[field]=value
    with pytest.raises(ValueError):
        validate(obj)


def records():
    return [{"scene":1,"start_ms":0,"end_ms":2000,"frames":50,"board_sha256":"b"*64},
            {"scene":2,"start_ms":2000,"end_ms":4000,"frames":50,"board_sha256":"c"*64}]


def test_split_exact_pcm():
    raw=tone(seconds=4)
    chunks=p.split_master(raw,records())
    assert list(chunks)==["mixed_01.wav","mixed_02.wav"]
    assert p.mix.samples(chunks["mixed_01.wav"])+p.mix.samples(chunks["mixed_02.wav"])==p.mix.samples(raw)


@pytest.mark.parametrize("key,value",[
    ("scene",0),("scene",True),("scene",1.0),("frames",0),("frames",12),
    ("frames",751),("frames",True),("start_ms",1),("start_ms",False),
    ("end_ms",1999),("end_ms",2000.0),("frames",49),("frames",51)])
def test_split_boundaries(key,value):
    rec=records()
    rec[0][key]=value
    with pytest.raises(ValueError):
        p.split_master(tone(seconds=4),rec)


@pytest.mark.parametrize("seconds",[3,3.96,4.04,5])
def test_split_duration(seconds):
    with pytest.raises(ValueError):
        p.split_master(tone(seconds=seconds),records())


def plan():
    return DraftPlan.model_validate({"scenes":[{"board":demo_spec("technology","SHORT").model_dump(),
       "narration_file":f"voice{i}.wav","narration_sha256":"d"*64,
       "narration_text":"This is a test","rights_attested":True} for i in (1,2)]})


def derive(pl):
    raw=tone(seconds=4)
    return p.derive_plan(pl,records(),p.split_master(raw,records()),PARENT,
                         "e"*64,p.sha(raw),"f"*64,"STATIC")


def test_plan_preserved():
    original=plan()
    new=derive(original)
    assert original.scenes[0].narration_file=="voice1.wav"
    assert new.scenes[0].narration_file=="mixed_01.wav"
    assert new.scenes[0].board.claims==original.scenes[0].board.claims
    assert new.scenes[0].board.sources==original.scenes[0].board.sources
    assert new.scenes[0].narration_text==original.scenes[0].narration_text
    assert new.scenes[0].board.specialist_facts["production_mix_original_narration_sha256"]=="d"*64


def test_double_mix_rejected():
    with pytest.raises(ValueError,match="ALREADY_MIXED"):
        derive(derive(plan()))


def test_default_renderer_rejects_mix(tmp_path):
    with pytest.raises(ValueError,match="pinned parent renderer"):
        render_board(derive(plan()).scenes[0].board,tmp_path/"board.png")


def test_renderer_wrong_board(tmp_path):
    with pytest.raises(ValueError,match="BOARD_BINDING"):
        p.renderer({"1":b"wrong"})(derive(plan()).scenes[0].board,tmp_path/"board.png")


def test_incomplete_output(tmp_path):
    parent=tmp_path/"parent"
    parent.mkdir()
    output=tmp_path/"out"
    output.mkdir()
    (output/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="MIX_INVENTORY"):
        p.verify(parent,PARENT,b"x",b"x",p.sha(b"x"),output,"0"*64)


@pytest.fixture
def original(tmp_path):
    assets=tmp_path/"assets"
    assets.mkdir()
    pl=plan().model_dump()
    for i,s in enumerate(pl["scenes"],1):
        raw=tone(seconds=2,frequency=300+i)
        (assets/s["narration_file"]).write_bytes(raw)
        s["narration_sha256"]=p.sha(raw)
    path=tmp_path/"plan.json"
    path.write_bytes(p.json_bytes(pl))
    parent=tmp_path/"parent"
    result=pp.build(path,assets,parent)
    return parent,result["manifest_sha256"]


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media required")
@pytest.mark.parametrize("mode",["STATIC","DUCK"])
def test_real_production_mix(mode,original,tmp_path):
    parent,pin=original
    voice=(parent/"draft"/"narration.wav").read_bytes()
    music=tone(seconds=4,frequency=500,amplitude=2000)
    raw=p.json_bytes(request(mode,voice,music,pin))
    output=tmp_path/"mixed"
    before=p.ps.inventory(parent)
    args=(parent,pin,music,raw,p.sha(raw),output)
    result=p.build(*args)
    assert result["duration_ms"]==4000 and result["manifest_sha256"]!=pin
    assert p.ps.inventory(parent)==before
    check=p.verify(*args,result["mix_sha256"])
    assert check["fresh_media_audit"] and check["queue_state"]=="PENDING"
    assert not check["publication_eligible"]
    for i in (1,2):
        name=f"scene_{i:02}.png"
        assert (output/"run"/"draft"/name).read_bytes()==(parent/"draft"/name).read_bytes()
    with pytest.raises(ValueError):
        p.build(*args)
    with pytest.raises(ValueError):
        p.verify(*args,"0"*64)
    (output/"run"/"assets"/"mixed_01.wav").write_bytes(b"tamper")
    with pytest.raises(ValueError):
        p.verify(*args,result["mix_sha256"])
