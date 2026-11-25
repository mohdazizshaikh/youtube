"""Owner-local bounded voice-activity music ducking; no compression of narration."""
from __future__ import annotations
import argparse
import json
import math
import struct
import subprocess
import wave
from pathlib import Path

from tools import narration_mix as mix, narration_loudness as loud
from tools.narration_qc import RATE,MAX_WAV,analyze_pcm,private_file
from tools.narration_prepare import pinned,sha,finite_number,write_private
from tools.pilot_run_verify import decode,require

SCHEMA="VIRALOS_NARRATION_DUCK_REQUEST_V1"
MAX_REQUEST=24000
BLOCK=RATE//50


def validate(raw,pin):
    obj=decode(pinned(raw,pin,MAX_REQUEST))
    require(type(obj) is dict and set(obj)=={"schema","mix","threshold_dbfs","duck_db",
            "attack_ms","release_ms","hold_ms"} and obj["schema"]==SCHEMA,"DUCK_FIELDS")
    inner=json.dumps(obj["mix"],ensure_ascii=False).encode()
    mix.validate(inner,sha(inner))
    finite_number(obj["threshold_dbfs"],-50,-20)
    finite_number(obj["duck_db"],3,18)
    for key,lo,hi in (("attack_ms",10,200),("release_ms",80,1000),("hold_ms",0,500)):
        require(type(obj[key]) is int and lo<=obj[key]<=hi,"DUCK_TIME")
    return obj


def targets(voice,threshold,hold_ms):
    """20-ms RMS activity, one-block lookahead and bounded hold; not ASR."""
    cutoff=32768*10**(threshold/20)
    active=[]
    for i in range(0,len(voice),BLOCK):
        block=voice[i:i+BLOCK]
        active.append(math.sqrt(sum(x*x for x in block)/len(block))>=cutoff)
    remaining=0
    hold=(hold_ms+19)//20
    result=[]
    for i,a in enumerate(active):
        if a or (i+1<len(active) and active[i+1]):
            remaining=hold+1
        result.append(remaining>0)
        remaining=max(0,remaining-1)
    return result


def render_samples(voice,music,base_gain,obj):
    require(len(voice)==len(music) and len(voice)>=RATE*3,"DUCK_LENGTH")
    n=len(voice)
    fade=obj["mix"]["fade_ms"]*RATE//1000
    require(2*fade<n,"DUCK_FADE_OVERLAP")
    activity=targets(voice,obj["threshold_dbfs"],obj["hold_ms"])
    floor=10**(-obj["duck_db"]/20)
    attack=math.exp(-1/(RATE*obj["attack_ms"]/1000))
    release=math.exp(-1/(RATE*obj["release_ms"]/1000))
    scale=10**(base_gain/20)
    envelope=1.0
    minimum=1.0
    result=[]
    for i,(x,y) in enumerate(zip(voice,music)):
        target=floor if activity[i//BLOCK] else 1.0
        coeff=attack if target<envelope else release
        envelope=target+(envelope-target)*coeff
        minimum=min(minimum,envelope)
        edge=min(1,i/fade,(n-1-i)/fade)
        sample=x+round(y*scale*edge*envelope)
        require(-32768<=sample<=32767,"DUCK_SAMPLE_CLIPPING")
        result.append(sample)
    return result,{"activity_window_fraction":round(sum(activity)/len(activity),6),
                   "max_applied_duck_db":round(-20*math.log10(minimum),4)}


def duck(voice,music,request,request_pin):
    obj=validate(request,request_pin)
    cfg=obj["mix"]
    pinned(voice,cfg["voice_sha256"],MAX_WAV)
    pinned(music,cfg["music_sha256"],MAX_WAV)
    vq,mq=analyze_pcm(voice),analyze_pcm(music)
    require(vq["frames"]==mq["frames"],"DUCK_LENGTH")
    require(vq["pcm_sha256"]!=mq["pcm_sha256"],"DUCK_DUPLICATE_PCM")
    require(not vq["audio_flags"] and not mq["audio_flags"],"DUCK_SOURCE_REVIEW")
    v=loud.measure(voice,cfg["voice_sha256"])
    m=loud.measure(music,cfg["music_sha256"])
    gain=mix.gain_for_music(v["integrated_lufs"],m["integrated_lufs"],cfg["music_relative_lufs"])
    result,stats=render_samples(mix.samples(voice),mix.samples(music),gain,obj)
    raw=mix.wav(result)
    out=loud.measure(raw,sha(raw))
    require(out["frames"]==vq["frames"],"DUCK_TIMING")
    require(out["true_peak_dbtp"]<=cfg["ceiling_dbtp"],"DUCK_TRUE_PEAK")
    return raw,{"schema":"VIRALOS_NARRATION_DUCK_V1","request_sha256":request_pin,
                "voice":v,"music":m,"output":out,"base_music_gain_db":round(gain,4),
                **stats,"activity_method":"RMS_20MS_LOOKAHEAD_HOLD","timing_preserved":True,
                "music_rights_self_attested":True,"voice_compressed":False,
                "speech_intelligibility_verified":False,"human_listening_required":True,
                "publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("voice","music","request","output"):p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--request-sha256",required=True)
    a=p.parse_args()
    try:
        raw,report=duck(private_file(a.voice,MAX_WAV),private_file(a.music,MAX_WAV),
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
