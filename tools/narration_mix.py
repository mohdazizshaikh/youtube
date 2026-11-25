"""Pinned, exact-length owner-local narration/music mix, with measured peak QC."""
from __future__ import annotations
import argparse
import io
import json
import math
import struct
import subprocess
import unicodedata
import wave
from pathlib import Path

from tools import narration_loudness as loud
from tools.narration_qc import RATE,MAX_WAV,analyze_pcm,private_file
from tools.narration_prepare import pinned,sha,finite_number,write_private
from tools.pilot_run_verify import decode,require

SCHEMA="VIRALOS_NARRATION_MIX_REQUEST_V1"
MAX_REQUEST=16000


def validate(raw,pin):
    obj=decode(pinned(raw,pin,MAX_REQUEST))
    require(type(obj) is dict and set(obj)=={"schema","voice_sha256","music_sha256",
            "music_rights_attested","license_reference","music_relative_lufs","fade_ms","ceiling_dbtp"},
            "MIX_FIELDS")
    require(obj["schema"]==SCHEMA and obj["music_rights_attested"] is True,"MIX_RIGHTS")
    from tools.pilot_run_verify import pin as check_pin
    check_pin(obj["voice_sha256"])
    check_pin(obj["music_sha256"])
    require(obj["voice_sha256"]!=obj["music_sha256"],"MIX_DUPLICATE")
    ref=obj["license_reference"]
    require(type(ref) is str and 3<=len(ref.strip())<=300
            and all(unicodedata.category(c)[0]!="C" for c in ref),"LICENSE_REFERENCE")
    finite_number(obj["music_relative_lufs"],-36,-18)
    finite_number(obj["ceiling_dbtp"],-6,-1)
    require(type(obj["fade_ms"]) is int and 50<=obj["fade_ms"]<=1000,"FADE_RANGE")
    return obj


def samples(raw):
    with wave.open(io.BytesIO(raw),"rb") as w:
        n=w.getnframes()
        return struct.unpack(f"<{n}h",w.readframes(n))


def wav(samples):
    out=io.BytesIO()
    with wave.open(out,"wb") as w:
        w.setparams((1,2,RATE,len(samples),"NONE","not compressed"))
        w.writeframes(struct.pack(f"<{len(samples)}h",*samples))
    return out.getvalue()


def gain_for_music(voice_lufs,music_lufs,relative):
    # Never boost music; reject a requested gain beyond the supported floor.
    gain=min(0,voice_lufs+relative-music_lufs)
    require(gain>=-60,"MUSIC_ATTENUATION_RANGE")
    return gain


def mix(voice,music,request,request_pin):
    obj=validate(request,request_pin)
    pinned(voice,obj["voice_sha256"],MAX_WAV)
    pinned(music,obj["music_sha256"],MAX_WAV)
    vq,mq=analyze_pcm(voice),analyze_pcm(music)
    require(vq["frames"]==mq["frames"],"MIX_LENGTH")
    require(vq["pcm_sha256"]!=mq["pcm_sha256"],"MIX_DUPLICATE_PCM")
    require(not vq["audio_flags"] and not mq["audio_flags"],"MIX_SOURCE_REVIEW")
    v=loud.measure(voice,obj["voice_sha256"])
    m=loud.measure(music,obj["music_sha256"])
    gain=gain_for_music(v["integrated_lufs"],m["integrated_lufs"],obj["music_relative_lufs"])
    scale=10**(gain/20)
    n=vq["frames"]
    fade=obj["fade_ms"]*RATE//1000
    require(2*fade<n,"MIX_FADE_OVERLAP")
    # Voice is never time-stretched or attenuated here. Music fades at both ends.
    mixed=[]
    for i,(x,y) in enumerate(zip(samples(voice),samples(music))):
        envelope=min(1,i/fade,(n-1-i)/fade)
        value=x+round(y*scale*envelope)
        require(-32768<=value<=32767,"MIX_SAMPLE_CLIPPING")
        mixed.append(value)
    result=wav(mixed)
    measured=loud.measure(result,sha(result))
    require(measured["frames"]==n,"MIX_TIMING")
    require(measured["true_peak_dbtp"]<=obj["ceiling_dbtp"],"MIX_TRUE_PEAK")
    return result,{"schema":"VIRALOS_NARRATION_MIX_V1","request_sha256":request_pin,
                   "voice":v,"music":m,"output":measured,"music_gain_db":round(gain,4),
                   "music_relative_lufs_target":obj["music_relative_lufs"],"fade_ms":obj["fade_ms"],
                   "music_rights_self_attested":True,"timing_preserved":True,
                   "human_listening_required":True,"speech_intelligibility_verified":False,
                   "professional_mix_verified":False,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("voice","music","request","output"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--request-sha256",required=True)
    a=p.parse_args()
    try:
        raw,report=mix(private_file(a.voice,MAX_WAV),private_file(a.music,MAX_WAV),
                       private_file(a.request,MAX_REQUEST),a.request_sha256)
        write_private(a.output,raw)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,
            struct.error,subprocess.SubprocessError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(report,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
