import json
import shutil
import pytest
from tools import narration_loudness as l
from test_narration_prepare import tone


def report():
    return {"input_i":"-20.23","input_tp":"-9.5","input_lra":"2.0","input_thresh":"-30.0"}


def parse(obj):
    return l.parse_measurement(json.dumps(obj).encode())


def test_parse():
    assert parse(report())=={"integrated_lufs":-20.23,"true_peak_dbtp":-9.5,
                             "loudness_range_lu":2.0,"threshold_lufs":-30.0}


@pytest.mark.parametrize("field,value",[
    ("input_i","-inf"),("input_i","nan"),("input_tp","inf"),("input_lra","-1"),
    ("input_lra","101"),("input_i","21"),("input_tp","-151"),("input_thresh",None),
    ("input_i",True),("input_i",[]),("input_i",{}),("input_i","invalid"),
    ("input_i","1"*25),("input_tp",False)])
def test_invalid_measurement(field,value):
    obj=report()
    obj[field]=value
    with pytest.raises((ValueError,TypeError)):
        parse(obj)


@pytest.mark.parametrize("raw",[b"",b"not json",b"{} {}",b"{bad}",b"[]" ,b"x"*128001,b"\xff"])
def test_invalid_log(raw):
    with pytest.raises(ValueError):
        l.parse_measurement(raw)


@pytest.mark.parametrize("field",list(l.FIELDS))
def test_missing_field(field):
    obj=report()
    del obj[field]
    with pytest.raises(ValueError):
        parse(obj)


@pytest.mark.parametrize("target,ceiling",[
    (-24,-1.5),(-13,-1.5),(-16,-7),(-16,0),(True,-1.5),
    (-16,False),(float("nan"),-1.5),(-16,float("inf")),("16",-1.5),(-16,None)])
def test_bad_parameters(target,ceiling):
    with pytest.raises(ValueError):
        l.gain_plan({"integrated_lufs":-20,"true_peak_dbtp":-8},target,ceiling)


@pytest.mark.parametrize("integrated,peak,expected",[
    (-20,-8,4),(-40,-20,6),(-10,-3,-6),(-20,-2,0.3),
    (-40,-1.5,-0.2),(-30,0,-1.7),(-2,-1,-12)])
def test_gain_plan(integrated,peak,expected):
    assert l.gain_plan({"integrated_lufs":integrated,"true_peak_dbtp":peak})==pytest.approx(expected)


def test_excessive_attenuation():
    with pytest.raises(ValueError,match="EXCESSIVE_ATTENUATION_REQUIRED"):
        l.gain_plan({"integrated_lufs":-10,"true_peak_dbtp":15})


def test_short_input():
    raw=tone()
    with pytest.raises(ValueError,match="LOUDNESS_MINIMUM_DURATION"):
        l.measure(raw,l.sha(raw))


def test_missing_ffmpeg(monkeypatch):
    raw=tone(seconds=3)
    monkeypatch.setattr(l.shutil,"which",lambda name:None)
    with pytest.raises(ValueError,match="LOCAL_FFMPEG_REQUIRED"):
        l.measure(raw,l.sha(raw))


@pytest.mark.parametrize("bad",["","0"*64,"A"*64,"x"*64])
def test_pin(bad):
    with pytest.raises(ValueError):
        l.measure(tone(),bad)


@pytest.mark.skipif(not shutil.which("ffmpeg"),reason="local FFmpeg required")
def test_real_loudness():
    raw=tone(seconds=4,amplitude=5000)
    source=l.measure(raw,l.sha(raw))
    out,r=l.master(raw,l.sha(raw),-20,-3)
    assert source["frames"]==r["output"]["frames"]==64000
    assert r["output"]["audio_sha256"]==l.sha(out)
    assert r["output"]["true_peak_dbtp"]<=-3
    assert r["timing_preserved"] and not r["publication_eligible"]
    assert r["gain_only"]
