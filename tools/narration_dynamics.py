"""Offline bounded narration dynamics candidate; not professional listening acceptance."""
from __future__ import annotations
import argparse
import json
import math
import os
import struct
import subprocess
import wave
from collections import deque
from pathlib import Path
from tools import narration_loudness as loud,narration_mix as mix
from tools import pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha,finite_number
from tools.narration_qc import RATE,MAX_WAV,private_file,analyze_pcm
from tools.bilingual_pilot import json_bytes

REQUEST="VIRALOS_NARRATION_DYNAMICS_REQUEST_V1"
SCHEMA="VIRALOS_NARRATION_DYNAMICS_V1"
MAX_REQUEST=16000
WINDOW=RATE//50


def validate(raw,request_pin):
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","voice_sha256","threshold_dbfs",
        "ratio","attack_ms","release_ms","target_lufs","ceiling_dbtp","lookahead_ms",
        "limiter_release_ms"} and obj["schema"]==REQUEST,"DYNAMICS_FIELDS")
    pv.pin(obj["voice_sha256"])
    for key,low,high in (("threshold_dbfs",-36,-10),("ratio",1.5,4),
                         ("target_lufs",-23,-14),("ceiling_dbtp",-6,-1)):
        finite_number(obj[key],low,high)
    for key,low,high in (("attack_ms",5,100),("release_ms",50,500),
                         ("lookahead_ms",2,10),("limiter_release_ms",30,300)):
        pv.require(pv.exact_int(obj[key],low,high),"DYNAMICS_TIMING")
    pv.require(obj["release_ms"]>=obj["attack_ms"],"COMPRESSOR_RELEASE")
    return obj


def compression_target(rms,threshold,ratio):
    if rms<=0:return 0.
    level=20*math.log10(rms/32768)
    return max(-12.,-max(0.,level-threshold)*(1-1/ratio))


def compress(samples,obj):
    pv.require(len(samples)>=WINDOW,"COMPRESSOR_LENGTH")
    attack=math.exp(-1/(RATE*obj["attack_ms"]/1000))
    release=math.exp(-1/(RATE*obj["release_ms"]/1000))
    envelope=0.
    deepest=0.
    active=0
    output=[]
    for pos in range(0,len(samples),WINDOW):
        block=samples[pos:pos+WINDOW]
        rms=math.sqrt(sum(x*x for x in block)/len(block))
        target=compression_target(rms,obj["threshold_dbfs"],obj["ratio"])
        for value in block:
            coefficient=attack if target<envelope else release
            envelope=target+(envelope-target)*coefficient
            deepest=min(deepest,envelope)
            active+=envelope<-.1
            output.append(round(value*10**(envelope/20)))
    pv.require(len(output)==len(samples) and all(abs(y)<=abs(x) for x,y in zip(samples,output)),
               "COMPRESSOR_INVARIANT")
    return output,{"max_compression_db":round(-deepest,4),
                   "compression_active_fraction":round(active/len(samples),6)}


def future_peaks(samples,lookahead):
    """Inclusive sliding forward maximum; O(n) monotonic queue."""
    pv.require(len(samples)>0 and pv.exact_int(lookahead,0,RATE),"LOOKAHEAD")
    q=deque()
    right=0
    for i in range(len(samples)):
        end=min(len(samples),i+lookahead+1)
        while right<end:
            value=abs(samples[right])
            while q and q[-1][1]<=value:q.pop()
            q.append((right,value))
            right+=1
        while q and q[0][0]<i:q.popleft()
        yield q[0][1]


def limit(samples,gain_db,obj):
    scale=10**(gain_db/20)
    lookahead=obj["lookahead_ms"]*RATE//1000
    release=math.exp(-1/(RATE*obj["limiter_release_ms"]/1000))
    # Reserve 1 dB for intersample peaks; actual true peak is measured afterward.
    ceiling=math.floor(32768*10**((obj["ceiling_dbtp"]-1)/20))
    envelope=1.
    minimum=1.
    active=0
    output=[]
    for value,peak in zip(samples,future_peaks(samples,lookahead)):
        target=min(1.,ceiling/(peak*scale)) if peak else 1.
        envelope=min(target,1-(1-envelope)*release)
        minimum=min(minimum,envelope)
        active+=envelope<.999
        output.append(round(value*scale*envelope))
    pv.require(len(output)==len(samples) and max(map(abs,output))<=ceiling,"LIMITER_PEAK")
    reduction=-20*math.log10(minimum)
    pv.require(reduction<=12,"EXCESSIVE_LIMITING_REQUIRED")
    return output,{"max_limiting_db":round(reduction,4),"limiter_active_fraction":round(active/len(samples),6),
                   "sample_peak_ceiling_dbfs":obj["ceiling_dbtp"]-1}


def master(voice,request,request_pin):
    obj=validate(request,request_pin)
    pinned(voice,obj["voice_sha256"],MAX_WAV)
    before=loud.measure(voice,obj["voice_sha256"])
    original=mix.samples(voice)
    compressed,cstats=compress(original,obj)
    compressed_raw=mix.wav(compressed)
    mid=loud.measure(compressed_raw,sha(compressed_raw))
    gain=min(6.,max(-12.,obj["target_lufs"]-mid["integrated_lufs"]))
    adjusted,lstats=limit(compressed,gain,obj)
    raw=mix.wav(adjusted)
    after=loud.measure(raw,sha(raw))
    pv.require(before["frames"]==mid["frames"]==after["frames"]==len(original),"TIMING_CHANGED")
    pv.require(after["true_peak_dbtp"]<=obj["ceiling_dbtp"],"TRUE_PEAK_CEILING")
    pv.require(all((x>=0 and y>=0) or (x<=0 and y<=0) for x,y in zip(original,adjusted))
               and all(y==0 for x,y in zip(original,adjusted) if x==0),"SIGN_AND_ZERO_PRESERVATION")
    return raw,{"schema":SCHEMA,"request_sha256":request_pin,"source":before,"compressed":mid,"output":after,
                "compressor":cstats,"limiter":lstats,"makeup_gain_db":round(gain,4),
                "target_lufs":obj["target_lufs"],"ceiling_dbtp":obj["ceiling_dbtp"],
                "target_reached_within_1lu":abs(after["integrated_lufs"]-obj["target_lufs"])<=1,
                "timing_preserved":True,"sample_peak_limiter":True,"true_peak_remeasured":True,
                "human_listening_required":True,"speech_intelligibility_verified":False,
                "professional_mastering_verified":False,"publication_eligible":False}


def write(path,raw):
    with path.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    pv.require(pv.read(path,len(raw))==raw,"OUTPUT_BYTES")


def build(voice,request,request_pin,output):
    raw,report=master(voice,request,request_pin)
    output=Path(output).absolute()
    output=ps.local_dir(output.parent)/output.name
    pv.require(not output.exists() and not output.is_symlink(),"DESTINATION_EXISTS")
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    receipt=json_bytes(report)
    write(output/"master.wav",raw)
    write(output/"dynamics.json",receipt)
    marker.unlink()
    return {"dynamics_sha256":sha(receipt),"audio_sha256":sha(raw),
            "target_reached_within_1lu":report["target_reached_within_1lu"],"publication_eligible":False}


def verify(voice,request,request_pin,output,dynamics_pin):
    root=ps.local_dir(output)
    pv.require({p.name for p in root.iterdir()}=={"master.wav","dynamics.json"},"DYNAMICS_INVENTORY")
    receipt=pinned(pv.read(root/"dynamics.json",pv.MAX_JSON),dynamics_pin,pv.MAX_JSON)
    raw,report=master(voice,request,request_pin)
    pv.require(receipt==json_bytes(report),"DYNAMICS_RECEIPT")
    pv.require(pv.read(root/"master.wav",MAX_WAV)==raw,"DYNAMICS_AUDIO_BYTES")
    return {"dynamics_sha256":dynamics_pin,"fresh_dynamics_audit":True,
            "target_reached_within_1lu":report["target_reached_within_1lu"],"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("voice","request","output"):a.add_argument("--"+name,type=Path,required=True)
        a.add_argument("--request-sha256",required=True)
        if mode=="verify":a.add_argument("--dynamics-sha256",required=True)
    a=p.parse_args()
    try:
        args=(private_file(a.voice,MAX_WAV),private_file(a.request,MAX_REQUEST),a.request_sha256,a.output)
        result=build(*args) if a.mode=="build" else verify(*args,a.dynamics_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,OverflowError,
            struct.error,subprocess.SubprocessError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
