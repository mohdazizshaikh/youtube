import shutil
import pytest
from tools import bilingual_dynamics as b
from test_phase15x import request as track_request
from test_narration_prepare import tone

PIN="a"*64


def request(pins=None):
    pins=pins or {"hindi":PIN,"english":"b"*64}
    return {"schema":b.REQUEST,"scenes":[{"scene":1,"frames":50},{"scene":2,"frames":50}],
            "tracks":{l:track_request(pins[l]) for l in b.LANGS}}


def check(obj):
    raw=b.json_bytes(obj)
    return b.validate(raw,b.sha(raw))


@pytest.mark.parametrize("field,value",[("schema","bad"),("scenes",None),("scenes",[]),
    ("scenes",{}),("tracks",None),("tracks",[]),("tracks",{}),("extra",1)])
def test_request(field,value):
    obj=request()
    obj[field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("field,value",[("scene",0),("scene",True),("scene",1.0),
    ("scene",2),("frames",12),("frames",751),("frames",True),("frames",50.0),("extra",1)])
def test_scene(field,value):
    obj=request()
    obj["scenes"][0][field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("frames",[[13,13],[37,37],[750]*5,[50]*9])
def test_total(frames):
    obj=request()
    obj["scenes"]=[{"scene":i,"frames":f} for i,f in enumerate(frames,1)]
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("field,value",[("target_lufs",-19),("ceiling_dbtp",-4),
    ("voice_sha256",PIN),("schema","bad"),("ratio",True)])
def test_nested(field,value):
    obj=request()
    obj["tracks"]["english"][field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("frames",[[25,50],[50,50],[25,25,25,25],[13,62]])
def test_valid(frames):
    obj=request()
    obj["scenes"]=[{"scene":i,"frames":f} for i,f in enumerate(frames,1)]
    actual,raw,count=check(obj)
    assert actual==obj and count==sum(frames)*640
    assert set(raw)==set(b.LANGS)


def inputs():
    voices={l:tone(seconds=4,frequency=f,amplitude=a) for l,f,a in
            (("hindi",330,7000),("english",440,11000))}
    obj=request({l:b.sha(v) for l,v in voices.items()})
    return voices,obj


def test_source_qc():
    voices,obj=inputs()
    assert all(x["frames"]==64000 for x in b.source_qc(voices,obj,64000).values())


@pytest.mark.parametrize("kind",["wrong_length","changed","missing","extra","silence"])
def test_bad_source(kind):
    voices,obj=inputs()
    if kind=="wrong_length":
        voices["hindi"]=tone(seconds=3)
        obj["tracks"]["hindi"]["voice_sha256"]=b.sha(voices["hindi"])
    elif kind=="changed":voices["hindi"]=tone(seconds=4)
    elif kind=="missing":del voices["english"]
    elif kind=="extra":voices["other"]=voices["english"]
    else:
        voices["hindi"]=tone(seconds=4,amplitude=0)
        obj["tracks"]["hindi"]["voice_sha256"]=b.sha(voices["hindi"])
    with pytest.raises(ValueError):b.source_qc(voices,obj,64000)


@pytest.mark.parametrize("frames",[[25,50],[50,50],[25,25,25,25],[13,62]])
def test_split(frames):
    count=sum(frames)*640
    samples=tuple((i%200)-100 for i in range(count))
    raw=b.mix.wav(samples)
    rows=[{"scene":i,"frames":f} for i,f in enumerate(frames,1)]
    parts=b.split(raw,rows,count)
    assert tuple(x for chunk,_ in parts for x in b.mix.samples(chunk))==samples
    assert parts[-1][1]["end_sample"]==count
    assert parts[-1][1]["end_ms"]==count//16


def test_silent_scene():
    raw=b.mix.wav([0]*32000+list(b.mix.samples(tone(seconds=2))))
    with pytest.raises(ValueError,match="SILENT_SCENE"):b.split(raw,request()["scenes"],64000)


@pytest.mark.parametrize("count",[63999,64001])
def test_master_length(count):
    raw=tone(seconds=4)
    with pytest.raises(ValueError,match="MASTER_LENGTH"):b.split(raw,request()["scenes"],count)


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    voices,obj=inputs()
    raw=b.json_bytes(obj)
    with pytest.raises(ValueError,match="PAIR_INVENTORY"):b.verify(voices,raw,b.sha(raw),tmp_path,PIN)


@pytest.mark.skipif(not shutil.which("ffmpeg"),reason="local FFmpeg required")
def test_real_pair(tmp_path):
    voices,obj=inputs()
    raw=b.json_bytes(obj)
    args=(voices,raw,b.sha(raw))
    dest=tmp_path/"paired-master"
    result=b.build(*args,dest)
    assert result["samples_per_track"]==64000 and not result["publication_eligible"]
    checked=b.verify(*args,dest,result["pair_dynamics_sha256"])
    assert checked["fresh_dynamics_audit"]
    receipt=b.pv.document(dest/"pair_dynamics.json")
    assert receipt["scene_timing_preserved"] and not receipt["word_alignment_verified"]
    for lang in b.LANGS:
        assert receipt["tracks"][lang]["true_peak_dbtp"]<=-3
        master=b.mix.samples((dest/(lang+"_master.wav")).read_bytes())
        assert tuple(x for i in (1,2) for x in b.mix.samples(
            (dest/f"{lang}_{i:02}.wav").read_bytes()))==master
    with pytest.raises(ValueError):b.build(*args,dest)
    (dest/"english_02.wav").write_bytes(b"tamper")
    with pytest.raises(ValueError):b.verify(*args,dest,result["pair_dynamics_sha256"])
