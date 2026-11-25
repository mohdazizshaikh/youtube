"""Synthetic portable tests; never a professional speech or owner acceptance benchmark."""
import io
import json
import math
import struct
import wave

import pytest

from tools import narration_prepare as p


def tone(seconds=1, amplitude=5000, frequency=330, constant=False):
    n = round(seconds*16000)
    values = [amplitude if constant else round(amplitude*math.sin(2*math.pi*frequency*i/16000))
              for i in range(n)]
    out = io.BytesIO()
    with wave.open(out,"wb") as w:
        w.setparams((1,2,16000,n,"NONE","not compressed"))
        w.writeframes(struct.pack(f"<{n}h",*values))
    return out.getvalue()


@pytest.mark.parametrize("amp", [500,1000,3000,5000,10000,20000])
def test_master_duration_and_bounds(amp):
    raw = tone(amplitude=amp)
    output, r = p.master(raw,p.sha(raw))
    assert r["source"]["frames"] == r["output"]["frames"] == 16000
    assert -12 <= r["applied_gain_db"] <= 6
    assert r["output"]["peak_dbfs"] <= -3
    assert r["output"]["audio_sha256"] == p.sha(output)
    assert r["timing_preserved"] and not r["publication_eligible"]
    assert r["human_listening_required"]


@pytest.mark.parametrize("target,peak", [
    (-27,-3),(-15,-3),(-20,-7),(-20,0),(True,-3),(-20,False),
    (float("nan"),-3),(-20,float("inf")),("20",-3),(-20,None),
])
def test_master_parameter_bounds(target,peak):
    raw=tone()
    with pytest.raises(ValueError):
        p.master(raw,p.sha(raw),target,peak)


@pytest.mark.parametrize("amp,constant", [(0,False),(10,False),(32767,True),(2000,True)])
def test_master_refuses_bad_source(amp,constant):
    raw=tone(amplitude=amp,constant=constant)
    with pytest.raises(ValueError,match="SOURCE_AUDIO_REVIEW_REQUIRED"):
        p.master(raw,p.sha(raw))


@pytest.mark.parametrize("bad", ["","0"*64,"A"*64,"z"*64,"a"*63])
def test_master_pin(bad):
    with pytest.raises(ValueError):
        p.master(tone(),bad)


def test_output_no_overwrite(tmp_path):
    out=tmp_path/"master.wav"
    p.write_private(out,b"first")
    with pytest.raises(FileExistsError):
        p.write_private(out,b"second")
    assert out.read_bytes()==b"first"


def test_output_extension(tmp_path):
    with pytest.raises(ValueError):
        p.write_private(tmp_path/"master.txt",b"x")


def gloss(locale="en-US"):
    return {"schema":"VIRALOS_PRONUNCIATION_GLOSSARY_V1","locale":locale,"entries":[
        {"id":"TERM_1","term":"New Delhi","spoken_hint":"new delhi","required":True,"owner_reviewed":True}]}


def pronounce(text,data,locale="en-US"):
    script=text.encode()
    raw=json.dumps(data,ensure_ascii=False).encode()
    return p.pronunciation(script,p.sha(script),raw,p.sha(raw),locale)


@pytest.mark.parametrize("text,count", [
    ("New Delhi is here",1),("NEW DELHI; new Delhi.",2),("New Delhiite",0),
    ("New, Delhi",1),("newdelhi",0),("Delhi New",0),("new\nDelhi",1),
])
def test_token_matching(text,count):
    r=pronounce(text,gloss())
    assert r["entries"][0]["occurrences"]==count
    assert not r["script_modified"] and not r["spoken_pronunciation_verified"]


def test_hindi_marks():
    data=gloss("hi-IN")
    data["entries"][0].update(term="नई दिल्ली",spoken_hint="नई दिल्ली")
    assert pronounce("नई दिल्ली में नई दिल्ली",data,"hi-IN")["entries"][0]["occurrences"]==2


def test_unicode_normalization():
    data=gloss()
    data["entries"][0]["term"]="Café"
    assert pronounce("Cafe\u0301",data)["entries"][0]["occurrences"]==1


@pytest.mark.parametrize("field,value", [
    ("id",""),("id","bad"),("id","A"*41),("id",1),("term",""),("term","a"*161),
    ("term","a\x00b"),("term","a b c d e f g h i"),("spoken_hint","???"),
    ("spoken_hint"," hi"),("required",1),("owner_reviewed","yes"),("extra",True),
])
def test_bad_glossary_entry(field,value):
    data=gloss()
    data["entries"][0][field]=value
    with pytest.raises(ValueError):
        pronounce("New Delhi",data)


def test_duplicate_term():
    data=gloss()
    data["entries"].append({**data["entries"][0],"id":"OTHER","term":"NEW DELHI"})
    with pytest.raises(ValueError,match="DUPLICATE_TERM"):
        pronounce("New Delhi",data)


def test_duplicate_id():
    data=gloss()
    data["entries"].append({**data["entries"][0],"term":"Mumbai"})
    with pytest.raises(ValueError,match="ENTRY_ID"):
        pronounce("New Delhi",data)


def test_unreviewed_hint():
    data=gloss()
    data["entries"][0]["owner_reviewed"]=False
    r=pronounce("New Delhi",data)
    assert r["entries"][0]["flags"]==["HINT_OWNER_REVIEW_PENDING"]


def test_missing_required():
    r=pronounce("Mumbai",gloss())
    assert r["entries"][0]["flags"]==["REQUIRED_TERM_NOT_FOUND"]


def test_wrong_glossary_locale():
    with pytest.raises(ValueError):
        pronounce("Delhi",gloss("hi-IN"))


@pytest.fixture
def scene_inputs(tmp_path):
    scenes=[]
    for i in (1,2):
        row={"scene":i}
        for lang,locale,offset in (("hindi","hi-IN",0),("english","en-IN",20)):
            name=f"{lang}{i}.wav"
            raw=tone(seconds=1 if lang=="hindi" else 1.03,frequency=300+i+offset)
            (tmp_path/name).write_bytes(raw)
            row[lang]={"locale":locale,"file":name,"sha256":p.sha(raw)}
        scenes.append(row)
    return tmp_path,{"schema":"VIRALOS_BILINGUAL_SCENE_REQUEST_V1","format":"SHORT","scenes":scenes}


def plan(root,data):
    raw=json.dumps(data).encode()
    return p.timing(root,raw,p.sha(raw))


def test_timing_exact(scene_inputs):
    root,data=scene_inputs
    r=plan(root,data)
    assert r["total_video_frames"]==52 and r["duration_ms"]==2080
    assert r["scenes"][0]["hindi_pad_samples"]==640
    assert r["scenes"][0]["english_pad_samples"]==160
    assert r["scenes"][1]["start_ms"]==1040
    assert not r["audio_modified"] and not r["word_alignment_verified"]
    assert not r["publication_eligible"]


@pytest.mark.parametrize("name", ["../bad.wav","a/b.wav","C:/a.wav","CON.wav","LPT1.wav",
                                 "a.wav:stream","a.WAV",".a.wav","a b.wav","a..wav"])
def test_bad_scene_filename(scene_inputs,name):
    root,data=scene_inputs
    data["scenes"][0]["hindi"]["file"]=name
    with pytest.raises(ValueError):
        plan(root,data)


@pytest.mark.parametrize("field,value", [
    ("scene",True),("scene",2),("scene",0),("scene",1.0),("extra",1),("hindi",None),
])
def test_bad_scene(scene_inputs,field,value):
    root,data=scene_inputs
    data["scenes"][0][field]=value
    with pytest.raises(ValueError):
        plan(root,data)


def test_timing_pin(scene_inputs):
    root,data=scene_inputs
    with pytest.raises(ValueError,match="INPUT_PIN"):
        p.timing(root,json.dumps(data).encode(),"0"*64)


def test_audio_pin(scene_inputs):
    root,data=scene_inputs
    data["scenes"][0]["hindi"]["sha256"]="0"*64
    with pytest.raises(ValueError,match="INPUT_PIN"):
        plan(root,data)


def test_same_language_pcm(scene_inputs):
    root,data=scene_inputs
    hi=data["scenes"][0]["hindi"]
    en=data["scenes"][0]["english"]
    en["file"],en["sha256"]=hi["file"],hi["sha256"]
    with pytest.raises(ValueError,match="DUPLICATE_LANGUAGE_PCM"):
        plan(root,data)


def test_reused_name(scene_inputs):
    root,data=scene_inputs
    data["scenes"][1]["hindi"]=dict(data["scenes"][0]["hindi"])
    with pytest.raises(ValueError,match="REUSED_FILENAME"):
        plan(root,data)


def test_large_padding_flags(scene_inputs):
    root,data=scene_inputs
    raw=tone(seconds=4)
    track=data["scenes"][0]["english"]
    (root/track["file"]).write_bytes(raw)
    track["sha256"]=p.sha(raw)
    r=plan(root,data)
    assert "EXCESSIVE_PADDING_REVIEW" in r["scenes"][0]["flags"]
    assert "DURATION_RATIO_REVIEW" in r["scenes"][0]["flags"]


def test_timing_no_mutation(scene_inputs):
    root,data=scene_inputs
    before={x.name:p.sha(x.read_bytes()) for x in root.iterdir()}
    plan(root,data)
    assert before=={x.name:p.sha(x.read_bytes()) for x in root.iterdir()}
