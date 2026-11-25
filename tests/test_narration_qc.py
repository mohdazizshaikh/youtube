"""Synthetic signal and input-boundary tests, not natural speech benchmarks."""
import hashlib
import io
import json
import math
import struct
import wave

import pytest

from tools import narration_qc as q


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wav(seconds=2, amplitude=5000, rate=16000, channels=1, width=2, kind="sine"):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setparams((channels, width, rate, 0, "NONE", "not compressed"))
        if width == 2:
            values = []
            for i in range(round(seconds*rate)):
                if kind == "constant":
                    sample = amplitude
                elif kind == "quiet_edges" and (i < rate or i >= seconds*rate-rate):
                    sample = 0
                else:
                    sample = round(amplitude*math.sin(2*math.pi*330*i/rate))
                values.extend([sample]*channels)
            w.writeframes(struct.pack(f"<{len(values)}h", *values))
        else:
            w.writeframes(bytes(round(seconds*rate)*channels*width))
    return buf.getvalue()


def report(audio, script=b"one two three four", locale="en-US"):
    return q.diagnose(audio, script, locale, sha(audio), sha(script))


@pytest.mark.parametrize("locale,script", [
    ("hi-IN", "यह एक परीक्षण है"), ("en-US", "one two three four"),
    ("en-IN", "one two three four"), ("hi-IN", "हिंदी में शब्द परीक्षण"),
])
def test_clean_diagnostic(locale, script):
    r = report(wav(), script.encode(), locale)
    assert r["technical_diagnostics_clean"]
    assert r["human_listening_required"] and not r["publication_eligible"]
    assert not r["spoken_words_verified"] and not r["voice_license_verified"]
    assert r["audio"]["duration_ms"] == 2000


@pytest.mark.parametrize("rate,channels,width,seconds", [
    (8000,1,2,1), (44100,1,2,1), (48000,1,2,1), (22050,1,2,1),
    (16000,2,2,1), (16000,1,1,1), (16000,1,3,1), (16000,1,4,1),
    (16000,1,2,.25), (16000,1,2,0),
])
def test_format_and_duration(rate, channels, width, seconds):
    with pytest.raises(ValueError):
        q.analyze_pcm(wav(seconds, rate=rate, channels=channels, width=width))


@pytest.mark.parametrize("raw", [b"", b"not a wav", b"RIFF", b"x"*20])
def test_bad_audio(raw):
    with pytest.raises((ValueError, EOFError, wave.Error)):
        q.analyze_pcm(raw)


@pytest.mark.parametrize("script", [
    b"", b"   ", b"\xff", b"\xef\xbb\xbfhello", b"hi\x00there",
    b"a\x1b", b"123 456", b"???", b"a"*121, b"a "*1001,
    b"a"*32769, "hello\u202eworld".encode(), "hello\u200bworld".encode(),
])
def test_bad_script(script):
    with pytest.raises(ValueError):
        q.script_stats(script, "en-US")


@pytest.mark.parametrize("locale", ["fr-FR", "hi", "EN-US", "", "en-GB"])
def test_unsupported_locale(locale):
    with pytest.raises(ValueError):
        q.script_stats(b"test", locale)


@pytest.mark.parametrize("field,bad", [
    ("audio", ""), ("audio", "0"*64), ("audio", "A"*64),
    ("audio", "f"*63), ("script", "0"*64), ("script", "z"*64),
    ("script", ""), ("script", "A"*64),
])
def test_bad_pin(field, bad):
    a, t = wav(), b"one two three four"
    with pytest.raises(ValueError):
        q.diagnose(a,t,"en-US",bad if field=="audio" else sha(a),
                   bad if field=="script" else sha(t))


@pytest.mark.parametrize("amplitude,kind,seconds,flag", [
    (0,"sine",2,"LOW_RMS"), (10,"sine",2,"MOSTLY_QUIET"),
    (32767,"constant",2,"CLIPPING"), (2000,"constant",2,"DC_OFFSET"),
    (2000,"constant",2,"LOW_CREST_FACTOR"),
    (5000,"quiet_edges",3,"LONG_LEADING_QUIET"),
    (5000,"quiet_edges",3,"LONG_TRAILING_QUIET"),
    (0,"sine",3,"LONG_QUIET_INTERVAL"),
])
def test_signal_flags(amplitude,kind,seconds,flag):
    assert flag in q.analyze_pcm(wav(seconds, amplitude, kind=kind))["audio_flags"]


@pytest.mark.parametrize("locale,script,flag", [
    ("hi-IN", "hello world today", "HINDI_SCRIPT_REVIEW"),
    ("en-US", "यह हिंदी है", "ENGLISH_SCRIPT_REVIEW"),
    ("en-IN", "one", "DECLARED_TEXT_PACE_REVIEW"),
    ("en-US", "one two three four five six seven eight", "DECLARED_TEXT_PACE_REVIEW"),
])
def test_script_flags(locale,script,flag):
    assert flag in report(wav(),script.encode(),locale)["review_flags"]


@pytest.fixture
def tracks(tmp_path):
    def track(locale,stem,script,amp):
        a,t=wav(amplitude=amp),script.encode()
        (tmp_path/f"{stem}.wav").write_bytes(a)
        (tmp_path/f"{stem}.txt").write_bytes(t)
        return {"locale":locale,"audio":f"{stem}.wav","script":f"{stem}.txt",
                "audio_sha256":sha(a),"script_sha256":sha(t)}
    return tmp_path,{"schema":"VIRALOS_BILINGUAL_QC_REQUEST_V1",
                     "hindi":track("hi-IN","hi","यह एक परीक्षण है",5000),
                     "english":track("en-IN","en","one two three four",6000)}


def paired(root,data):
    raw=json.dumps(data).encode()
    return q.pair(root,raw,sha(raw))


def test_pair(tracks):
    root,data=tracks
    r=paired(root,data)
    assert r["technical_diagnostics_clean"]
    assert r["hindi_to_english_duration_ratio"]==1
    assert not r["translation_verified"] and not r["alignment_verified"]
    assert not r["publication_eligible"]


@pytest.mark.parametrize("name", ["../a.wav","a/b.wav","C:/a.wav","con.wav","COM1.wav",
                                 "a.wav:stream","a.WAV",".a.wav","a b.wav","a..wav"])
def test_bad_asset_name(tracks,name):
    root,data=tracks
    data["hindi"]["audio"]=name
    with pytest.raises(ValueError):
        paired(root,data)


def test_reused_pcm(tracks):
    root,data=tracks
    data["english"]["audio"]=data["hindi"]["audio"]
    data["english"]["audio_sha256"]=data["hindi"]["audio_sha256"]
    with pytest.raises(ValueError,match="REUSED_PCM"):
        paired(root,data)


def test_reused_script(tracks):
    root,data=tracks
    data["english"]["script"]=data["hindi"]["script"]
    data["english"]["script_sha256"]=data["hindi"]["script_sha256"]
    with pytest.raises(ValueError,match="REUSED_SCRIPT"):
        paired(root,data)


def test_request_tamper(tracks):
    root,data=tracks
    raw=json.dumps(data).encode()
    with pytest.raises(ValueError,match="REQUEST_PIN"):
        q.pair(root,raw,"0"*64)


def test_audio_tamper(tracks):
    root,data=tracks
    (root/"hi.wav").write_bytes(wav(amplitude=7000))
    with pytest.raises(ValueError,match="INPUT_PIN"):
        paired(root,data)


def test_duration_ratio(tracks):
    root,data=tracks
    a=wav(seconds=5)
    (root/"hi.wav").write_bytes(a)
    data["hindi"]["audio_sha256"]=sha(a)
    assert "DURATION_RATIO_REVIEW" in paired(root,data)["pair_flags"]
