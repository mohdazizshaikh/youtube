"""Offline FFmpeg loudnorm measurement and bounded gain-only LUFS mastering.

No compression, limiting, resampling, trim, ASR, or release authorization.
"""
from __future__ import annotations
import argparse
import io
import json
import math
import re
import shutil
import struct
import subprocess
import wave
from pathlib import Path

from tools.narration_qc import RATE,MAX_WAV,analyze_pcm,private_file
from tools.narration_prepare import pinned,finite_number,sha,write_private
from tools.pilot_run_verify import require

FIELDS={"input_i":"integrated_lufs","input_tp":"true_peak_dbtp",
        "input_lra":"loudness_range_lu","input_thresh":"threshold_lufs"}


def parse_measurement(stderr):
    require(type(stderr) is bytes and len(stderr)<=128000,"MEASUREMENT_LOG_SIZE")
    text=stderr.decode("utf8",errors="strict")
    blocks=re.findall(r"\{[^{}]*\}",text,re.S)
    require(len(blocks)==1,"MEASUREMENT_JSON")
    data=json.loads(blocks[0])
    require(type(data) is dict and set(FIELDS)<=set(data),"MEASUREMENT_FIELDS")
    result={}
    for key,label in FIELDS.items():
        value=data[key]
        require(type(value) in (str,int,float) and len(str(value))<=24,"MEASUREMENT_VALUE")
        num=float(value)
        require(math.isfinite(num),"MEASUREMENT_NONFINITE")
        bounds=(0,100) if key=="input_lra" else (-150,20)
        require(bounds[0]<=num<=bounds[1],"MEASUREMENT_RANGE")
        result[label]=round(num,2)
    return result


def measure(raw,pin):
    pinned(raw,pin,MAX_WAV)
    qc=analyze_pcm(raw)
    require(qc["frames"]>=RATE*3,"LOUDNESS_MINIMUM_DURATION")
    require(not qc["audio_flags"],"SOURCE_AUDIO_REVIEW_REQUIRED")
    exe=shutil.which("ffmpeg")
    require(bool(exe),"LOCAL_FFMPEG_REQUIRED")
    command=[exe,"-nostdin","-hide_banner","-loglevel","info","-protocol_whitelist","pipe",
             "-f","wav","-i","pipe:0","-af","loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
             "-f","null","-"]
    result=subprocess.run(command,input=raw,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                          timeout=45,check=True)
    measured=parse_measurement(result.stderr)
    return {"schema":"VIRALOS_LOUDNESS_MEASUREMENT_V1","audio_sha256":pin,
            "frames":qc["frames"],"duration_ms":qc["duration_ms"],**measured,
            "method":"FFMPEG_LOUDNORM_INPUT_MEASUREMENT","human_listening_required":True,
            "professional_mastering_verified":False,"publication_eligible":False}


def gain_plan(measured,target=-16,ceiling=-1.5):
    target=finite_number(target,-23,-14)
    ceiling=finite_number(ceiling,-6,-1)
    integrated=finite_number(measured["integrated_lufs"],-150,20)
    peak=finite_number(measured["true_peak_dbtp"],-150,20)
    # Additional 0.2 dB margin covers reported hundredth-dB rounding and
    # PCM quantization. Output is measured again, not assumed compliant.
    gain=min(6,max(-12,target-integrated),ceiling-0.2-peak)
    require(gain>=-12,"EXCESSIVE_ATTENUATION_REQUIRED")
    return gain


def apply_gain(raw,gain):
    with wave.open(io.BytesIO(raw),"rb") as w:
        n=w.getnframes()
        samples=struct.unpack(f"<{n}h",w.readframes(n))
    scale=10**(gain/20)
    adjusted=tuple(round(x*scale) for x in samples)
    require(all(-32768<=x<=32767 for x in adjusted),"PCM_CLIPPING")
    out=io.BytesIO()
    with wave.open(out,"wb") as w:
        w.setparams((1,2,RATE,n,"NONE","not compressed"))
        w.writeframes(struct.pack(f"<{n}h",*adjusted))
    return out.getvalue()


def master(raw,pin,target=-16,ceiling=-1.5):
    target=finite_number(target,-23,-14)
    ceiling=finite_number(ceiling,-6,-1)
    before=measure(raw,pin)
    gain=gain_plan(before,target,ceiling)
    output=apply_gain(raw,gain)
    after=measure(output,sha(output))
    require(after["frames"]==before["frames"],"TIMING_CHANGED")
    require(after["true_peak_dbtp"]<=ceiling,"TRUE_PEAK_CEILING")
    return output,{"schema":"VIRALOS_LOUDNESS_MASTER_V1","source":before,"output":after,
             "target_lufs":target,"ceiling_dbtp":ceiling,"applied_gain_db":round(gain,4),
             "target_reached_within_1lu":abs(after["integrated_lufs"]-target)<=1,
             "timing_preserved":True,"gain_only":True,"human_listening_required":True,
             "professional_mastering_verified":False,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("measure","master"):
        a=sub.add_parser(mode)
        a.add_argument("--audio",type=Path,required=True)
        a.add_argument("--audio-sha256",required=True)
        if mode=="master":
            a.add_argument("--output",type=Path,required=True)
            a.add_argument("--target-lufs",type=float,default=-16)
            a.add_argument("--ceiling-dbtp",type=float,default=-1.5)
    args=p.parse_args()
    try:
        raw=private_file(args.audio,MAX_WAV)
        if args.mode=="measure":
            report=measure(raw,args.audio_sha256)
        else:
            output,report=master(raw,args.audio_sha256,args.target_lufs,args.ceiling_dbtp)
            write_private(args.output,output)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,
            OverflowError,struct.error,subprocess.SubprocessError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(report,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
