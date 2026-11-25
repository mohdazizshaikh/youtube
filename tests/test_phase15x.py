import math
import shutil
import pytest
from tools import narration_dynamics as d
from test_narration_prepare import tone

PIN="a"*64


def request(voice=PIN):
    return {"schema":d.REQUEST,"voice_sha256":voice,"threshold_dbfs":-22,"ratio":3,
            "attack_ms":10,"release_ms":150,"target_lufs":-18,"ceiling_dbtp":-3,
            "lookahead_ms":5,"limiter_release_ms":80}


def validate(obj):
    raw=d.json_bytes(obj)
    return d.validate(raw,d.sha(raw))


@pytest.mark.parametrize("field,value",[
    ("schema","bad"),("voice_sha256","bad"),("voice_sha256",None),("extra",1),
    ("threshold_dbfs",-37),("threshold_dbfs",-9),("threshold_dbfs",True),
    ("ratio",1),("ratio",4.1),("ratio","3"),("ratio",None),
    ("target_lufs",-24),("target_lufs",-13),("target_lufs",False),
    ("ceiling_dbtp",-7),("ceiling_dbtp",0),("ceiling_dbtp",True),
    ("attack_ms",4),("attack_ms",101),("attack_ms",10.0),("attack_ms",True),
    ("release_ms",49),("release_ms",501),("release_ms",None),
    ("lookahead_ms",1),("lookahead_ms",11),("lookahead_ms",5.0),
    ("limiter_release_ms",29),("limiter_release_ms",301),("limiter_release_ms",False)])
def test_request(field,value):
    obj=request()
    obj[field]=value
    with pytest.raises(ValueError):validate(obj)


def test_release_order():
    obj=request()
    obj.update(attack_ms=100,release_ms=50)
    with pytest.raises(ValueError,match="COMPRESSOR_RELEASE"):validate(obj)


def test_valid():
    assert validate(request())==request()


@pytest.mark.parametrize("rms,expected",[(0,0),(100,0),(32768*10**(-22/20),0),
    (32768*10**(-16/20),-4),(32768,-12)])
def test_curve(rms,expected):
    assert d.compression_target(rms,-22,3)==pytest.approx(expected)


@pytest.mark.parametrize("n",[1,2,3,10,100])
@pytest.mark.parametrize("ahead",[0,1,5,20])
def test_future_peaks(n,ahead):
    samples=[((i*89)%29-14)*100 for i in range(n)]
    assert list(d.future_peaks(samples,ahead))==[
        max(map(abs,samples[i:i+ahead+1])) for i in range(n)]


@pytest.mark.parametrize("amplitude",[500,2000,10000,25000])
def test_compressor(amplitude):
    samples=d.mix.samples(tone(seconds=1,amplitude=amplitude))
    result,stats=d.compress(samples,request())
    assert len(result)==len(samples)
    assert all(abs(y)<=abs(x) for x,y in zip(samples,result))
    assert 0<=stats["max_compression_db"]<=12
    if amplitude>=10000:assert stats["max_compression_db"]>1
    else:assert stats["max_compression_db"]==0


@pytest.mark.parametrize("gain",[-6,0,6])
def test_limiter(gain):
    source=[0,1000,-1000]*400+[24000,-24000,0]+[1000,-1000,0]*400
    result,stats=d.limit(source,gain,request())
    assert len(result)==len(source)
    assert max(map(abs,result))<=math.floor(32768*10**(-4/20))
    assert all(y==0 for x,y in zip(source,result) if x==0)
    assert 0<=stats["max_limiting_db"]<=12
    if gain==6:assert stats["max_limiting_db"]>1


def test_lookahead():
    source=[1000]*200+[30000]+[1000]*200
    result,_=d.limit(source,0,request())
    assert result[119]==1000
    assert result[120]<1000
    assert result[201]<1000


def test_source_pin():
    raw=d.json_bytes(request())
    with pytest.raises(ValueError,match="INPUT_PIN"):d.master(tone(seconds=4),raw,d.sha(raw))


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="DYNAMICS_INVENTORY"):d.verify(b"",b"",PIN,tmp_path,PIN)


@pytest.mark.skipif(not shutil.which("ffmpeg"),reason="local FFmpeg required")
def test_real_dynamics(tmp_path):
    samples=d.mix.samples(tone(seconds=2,amplitude=5000))+d.mix.samples(tone(seconds=2,amplitude=19000))
    voice=d.mix.wav(samples)
    raw=d.json_bytes(request(d.sha(voice)))
    args=(voice,raw,d.sha(raw))
    result,report=d.master(*args)
    assert report["source"]["frames"]==report["output"]["frames"]==64000
    assert report["compressor"]["max_compression_db"]>1
    assert report["output"]["true_peak_dbtp"]<=-3
    assert not report["publication_eligible"] and not report["professional_mastering_verified"]
    assert len(d.mix.samples(result))==len(samples)
    out=tmp_path/"master"
    built=d.build(*args,out)
    assert d.verify(*args,out,built["dynamics_sha256"])["fresh_dynamics_audit"]
    with pytest.raises(ValueError):d.build(*args,out)
    (out/"master.wav").write_bytes(b"tamper")
    with pytest.raises(ValueError):d.verify(*args,out,built["dynamics_sha256"])
