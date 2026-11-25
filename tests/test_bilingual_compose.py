"""Portable synthetic PCM composition and adversarial bundle checks."""
import io
import json
import wave
import pytest

from tools import bilingual_compose as b
from test_narration_prepare import tone


@pytest.fixture
def inputs(tmp_path):
    root = tmp_path/"input"
    root.mkdir()
    rows=[]
    for i in (1,2):
        row={"scene":i}
        for lang,locale,offset in (("hindi","hi-IN",0),("english","en-IN",20)):
            name=f"{lang}{i}.wav"
            raw=tone(seconds=1 if lang=="hindi" else 1.03,frequency=300+i+offset)
            (root/name).write_bytes(raw)
            row[lang]={"locale":locale,"file":name,"sha256":b.sha(raw)}
        rows.append(row)
    request={"schema":"VIRALOS_BILINGUAL_SCENE_REQUEST_V1","format":"SHORT","scenes":rows}
    caps={"schema":b.CAPTION_SCHEMA,"timing_request_sha256":b.sha(json.dumps(request).encode()),
          "scenes":[{"scene":i,"hindi":"यह एक परीक्षण है","english":"This is a test"} for i in (1,2)]}
    return root,request,caps,tmp_path/"bundle"


def args(inputs):
    root,req,caps,_=inputs
    r,c=json.dumps(req).encode(),json.dumps(caps).encode()
    return root,r,b.sha(r),c,b.sha(c)


def save(inputs):
    return b.compose(*args(inputs),inputs[3])


def pcm(path):
    with wave.open(str(path),"rb") as w:
        return w.readframes(w.getnframes())


def test_roundtrip(inputs):
    r=save(inputs)
    root,_,_,out=inputs
    assert r["files"]==9 and r["duration_ms"]==2080
    assert r["total_samples_per_track"]==33280
    for lang,pad in (("hindi",640),("english",160)):
        first=pcm(root/f"{lang}1.wav")
        assert pcm(out/f"{lang}_01.wav")==first+b"\0"*(pad*2)
        assert pcm(out/f"{lang}.wav")==pcm(out/f"{lang}_01.wav")+pcm(out/f"{lang}_02.wav")
        vtt=(out/f"{lang}.vtt").read_text(encoding="utf8")
        assert vtt.startswith("WEBVTT\n\n")
        assert "00:00:00.000 --> 00:00:01.040" in vtt
        assert "00:00:01.040 --> 00:00:02.080" in vtt
    assert b.verify(*args(inputs),out,r["manifest_sha256"])["fresh_recomposition"]
    assert not r["publication_eligible"] and not (out/"INCOMPLETE").exists()


@pytest.mark.parametrize("name",["hindi.wav","english.wav","hindi.vtt","english.vtt",
    "hindi_01.wav","hindi_02.wav","english_01.wav","english_02.wav","manifest.json"])
@pytest.mark.parametrize("mutation",["missing","changed","appended"])
def test_bundle_tamper(inputs,name,mutation):
    r=save(inputs)
    out=inputs[3]
    path=out/name
    if mutation=="missing":
        path.unlink()
    elif mutation=="changed":
        path.write_bytes(b"tampered")
    else:
        with path.open("ab") as f:f.write(b"x")
    with pytest.raises((ValueError,OSError)):
        b.verify(*args(inputs),out,r["manifest_sha256"])


@pytest.mark.parametrize("text",["", "  text", "text ", "x"*501, "a\nb", "a\rbc",
    "a\tbc","a\x00bc","a\u202ebc","a\u2028bc","a\u2029bc","a --> b",
    "12345","???","यह हिंदी है",None,True,123])
def test_bad_caption(inputs,text):
    inputs[2]["scenes"][0]["english"]=text
    with pytest.raises(ValueError):
        save(inputs)
    assert not inputs[3].exists()


@pytest.mark.parametrize("field,value",[
    ("schema","wrong"),("timing_request_sha256","0"*64),("scenes",[]),
    ("scenes",{}),("scenes",None),("extra",1)])
def test_bad_caption_document(inputs,field,value):
    inputs[2][field]=value
    with pytest.raises(ValueError):
        save(inputs)


@pytest.mark.parametrize("field,value",[
    ("scene",0),("scene",True),("scene",2),("scene",1.0),
    ("extra",1),("hindi","English words")])
def test_bad_caption_row(inputs,field,value):
    inputs[2]["scenes"][0][field]=value
    with pytest.raises(ValueError):
        save(inputs)


@pytest.mark.parametrize("bad",["","0"*64,"A"*64,"g"*64])
def test_wrong_manifest_pin(inputs,bad):
    save(inputs)
    with pytest.raises(ValueError):
        b.verify(*args(inputs),inputs[3],bad)


def test_existing_output(inputs):
    save(inputs)
    with pytest.raises(ValueError,match="OUTPUT_EXISTS"):
        save(inputs)


def test_unknown_file(inputs):
    r=save(inputs)
    (inputs[3]/"extra.txt").write_text("extra")
    with pytest.raises(ValueError,match="BUNDLE_INVENTORY"):
        b.verify(*args(inputs),inputs[3],r["manifest_sha256"])


def test_incomplete(inputs):
    r=save(inputs)
    (inputs[3]/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="BUNDLE_INVENTORY"):
        b.verify(*args(inputs),inputs[3],r["manifest_sha256"])


def test_source_tamper(inputs):
    save(inputs)
    (inputs[0]/"hindi1.wav").write_bytes(tone(frequency=700))
    with pytest.raises(ValueError,match="INPUT_PIN"):
        b.prepare(*args(inputs))


def test_nested_output(inputs):
    with pytest.raises(ValueError,match="OVERLAPPING_OUTPUT"):
        b.compose(*args(inputs),inputs[0]/"nested")


def test_caption_markup_escaped(inputs):
    inputs[2]["scenes"][0]["english"]="This <b> & that"
    save(inputs)
    text=(inputs[3]/"english.vtt").read_text(encoding="utf8")
    assert "This &lt;b&gt; &amp; that" in text


def test_mixed_english_locale(inputs):
    inputs[1]["scenes"][1]["english"]["locale"]="en-US"
    inputs[2]["timing_request_sha256"]=b.sha(json.dumps(inputs[1]).encode())
    with pytest.raises(ValueError,match="ENGLISH_LOCALE_CHANGED"):
        save(inputs)


def test_timing_review_refusal(inputs):
    raw=tone(seconds=4)
    track=inputs[1]["scenes"][0]["english"]
    (inputs[0]/track["file"]).write_bytes(raw)
    track["sha256"]=b.sha(raw)
    inputs[2]["timing_request_sha256"]=b.sha(json.dumps(inputs[1]).encode())
    with pytest.raises(ValueError,match="TIMING_REVIEW_REQUIRED"):
        save(inputs)


def test_source_unchanged(inputs):
    before={p.name:b.sha(p.read_bytes()) for p in inputs[0].iterdir()}
    save(inputs)
    assert before=={p.name:b.sha(p.read_bytes()) for p in inputs[0].iterdir()}


def test_caption_pin(inputs):
    root,r,rp,c,_=args(inputs)
    with pytest.raises(ValueError,match="INPUT_PIN"):
        b.compose(root,r,rp,c,"0"*64,inputs[3])


def test_failed_write_marker(inputs,monkeypatch):
    def fail(*args,**kwargs):
        raise OSError("simulated failure")
    monkeypatch.setattr(b,"file_hash",fail)
    with pytest.raises(OSError):
        save(inputs)
    assert (inputs[3]/"INCOMPLETE").exists()
