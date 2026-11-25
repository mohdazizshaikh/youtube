"""Pinned paired narration dynamics and frame-aligned scene assets.

Input WAVs are already synchronized owner-local narration masters. This module
does not align speech, alter scene boundaries, or authorize publication.
"""
from __future__ import annotations
import argparse
import json
import struct
import subprocess
import wave
from pathlib import Path

from tools import narration_dynamics as dynamics, narration_mix as mix
from tools import pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import RATE,MAX_WAV,private_file,analyze_pcm
from tools.bilingual_pilot import json_bytes

REQUEST="VIRALOS_BILINGUAL_DYNAMICS_REQUEST_V1"
SCHEMA="VIRALOS_BILINGUAL_DYNAMICS_V1"
LANGS=("hindi","english")
MAX_REQUEST=48000
FRAME=RATE//25


def validate(raw,request_pin):
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","scenes","tracks"}
               and obj["schema"]==REQUEST,"PAIR_REQUEST")
    rows=obj["scenes"]
    pv.require(type(rows) is list and 2<=len(rows)<=8,"SCENE_COUNT")
    total=0
    for i,row in enumerate(rows,1):
        pv.require(type(row) is dict and set(row)=={"scene","frames"} and
                   type(row["scene"]) is int and row["scene"]==i and
                   pv.exact_int(row["frames"],13,750),"SCENE_FIELDS")
        total+=row["frames"]
    pv.require(75<=total<=3000,"TOTAL_FRAMES")
    tracks=obj["tracks"]
    pv.require(type(tracks) is dict and set(tracks)==set(LANGS),"TRACKS")
    requests={}
    for lang in LANGS:
        row=tracks[lang]
        sub=json_bytes(row)
        dynamics.validate(sub,sha(sub))
        requests[lang]=sub
    hi,en=tracks["hindi"],tracks["english"]
    pv.require(hi["voice_sha256"]!=en["voice_sha256"],"DUPLICATE_VOICE")
    pv.require(hi["target_lufs"]==en["target_lufs"] and
               hi["ceiling_dbtp"]==en["ceiling_dbtp"],"SHARED_MASTERING_TARGET")
    return obj,requests,total*FRAME


def source_qc(voices,obj,count):
    pv.require(type(voices) is dict and set(voices)==set(LANGS),"VOICE_INPUTS")
    metrics={}
    for lang in LANGS:
        raw=pinned(voices[lang],obj["tracks"][lang]["voice_sha256"],MAX_WAV)
        q=analyze_pcm(raw)
        pv.require(q["frames"]==count and not q["audio_flags"],"SOURCE_TIMING_OR_QC")
        metrics[lang]=q
    pv.require(metrics["hindi"]["pcm_sha256"]!=metrics["english"]["pcm_sha256"],"DUPLICATE_PCM")
    return metrics


def split(raw,scenes,count):
    samples=mix.samples(raw)
    pv.require(len(samples)==count,"MASTER_LENGTH")
    pos=0
    parts=[]
    for i,row in enumerate(scenes,1):
        end=pos+row["frames"]*FRAME
        pv.require(end<=count,"SCENE_BOUNDARY")
        chunk=mix.wav(samples[pos:end])
        pv.require(any(samples[pos:end]),"SILENT_SCENE")
        q=analyze_pcm(chunk)
        pv.require(q["frames"]==end-pos,"SCENE_LENGTH")
        # A short scene may have its own QC flags even if the whole master is
        # clean. Preserve them explicitly; never silently discard this evidence.
        parts.append((chunk,{"scene":i,"start_sample":pos,"end_sample":end,
                  "start_ms":pos//16,"end_ms":end//16,"frames":row["frames"],
                  "audio_sha256":sha(chunk),"pcm_sha256":q["pcm_sha256"],
                  "audio_flags":q["audio_flags"]}))
        pos=end
    pv.require(pos==count,"SCENE_TOTAL")
    return parts


def prepare(voices,request,request_pin):
    obj,requests,count=validate(request,request_pin)
    source=source_qc(voices,obj,count)
    files={}
    reports={}
    tracks={}
    scene_rows=[{"scene":i+1,"frames":row["frames"],"tracks":{}}
                for i,row in enumerate(obj["scenes"])]
    for lang in LANGS:
        sub=requests[lang]
        master,report=dynamics.master(voices[lang],sub,sha(sub))
        pv.require(report["schema"]==dynamics.SCHEMA and
                   report["request_sha256"]==sha(sub) and
                   report["source"]["audio_sha256"]==source[lang]["audio_sha256"] and
                   report["output"]["audio_sha256"]==sha(master) and
                   report["output"]["frames"]==count and report["timing_preserved"] is True
                   and report["publication_eligible"] is False,"MASTER_BINDING")
        files[lang+"_master.wav"]=master
        detail=json_bytes(report)
        files[lang+"_dynamics.json"]=detail
        reports[lang]=report
        tracks[lang]={"source_audio_sha256":source[lang]["audio_sha256"],
                      "source_pcm_sha256":source[lang]["pcm_sha256"],
                      "request_sha256":sha(sub),"master_sha256":sha(master),
                      "dynamics_sha256":sha(detail),
                      "integrated_lufs":report["output"]["integrated_lufs"],
                      "true_peak_dbtp":report["output"]["true_peak_dbtp"],
                      "target_reached_within_1lu":report["target_reached_within_1lu"]}
        parts=split(master,obj["scenes"],count)
        rebuilt=[]
        for i,(chunk,row) in enumerate(parts,1):
            name=f"{lang}_{i:02}.wav"
            files[name]=chunk
            rebuilt.extend(mix.samples(chunk))
            scene_rows[i-1]["tracks"][lang]={**row,"file":name}
        pv.require(tuple(rebuilt)==mix.samples(master),"PCM_REASSEMBLY")
    for row in scene_rows:
        h,e=(row["tracks"][l] for l in LANGS)
        pv.require(all(h[k]==e[k] for k in ("start_sample","end_sample","start_ms","end_ms","frames")),
                   "BILINGUAL_TIMING")
    pv.require(analyze_pcm(files["hindi_master.wav"])["pcm_sha256"]!=
               analyze_pcm(files["english_master.wav"])["pcm_sha256"],"DUPLICATE_MASTER_PCM")
    difference=round(abs(tracks["hindi"]["integrated_lufs"]-tracks["english"]["integrated_lufs"]),4)
    scene_flags=[{"scene":r["scene"],"language":l,"flags":r["tracks"][l]["audio_flags"]}
                 for r in scene_rows for l in LANGS if r["tracks"][l]["audio_flags"]]
    receipt={"schema":SCHEMA,"request_sha256":request_pin,"sample_rate_hz":RATE,"fps":25,
             "samples_per_track":count,"duration_ms":count//16,
             "target_lufs":obj["tracks"]["hindi"]["target_lufs"],
             "ceiling_dbtp":obj["tracks"]["hindi"]["ceiling_dbtp"],
             "tracks":tracks,"scenes":scene_rows,"loudness_difference_lu":difference,
             "both_targets_within_1lu":all(x["target_reached_within_1lu"] for x in tracks.values()),
             "pair_loudness_difference_within_2lu":difference<=2,
             "scene_audio_review_flags":scene_flags,"scene_timing_preserved":True,
             "human_listening_required":True,"spoken_words_verified":False,
             "word_alignment_verified":False,"professional_mastering_verified":False,
             "publication_eligible":False}
    files["pair_dynamics.json"]=json_bytes(receipt)
    return files,receipt


def build(voices,request,request_pin,output):
    files,receipt=prepare(voices,request,request_pin)
    output=Path(output).absolute()
    output=ps.local_dir(output.parent)/output.name
    pv.require(not output.exists() and not output.is_symlink(),"DESTINATION_EXISTS")
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    for name,raw in files.items():dynamics.write(output/name,raw)
    marker.unlink()
    return {"pair_dynamics_sha256":sha(files["pair_dynamics.json"]),
            "samples_per_track":receipt["samples_per_track"],
            "both_targets_within_1lu":receipt["both_targets_within_1lu"],
            "pair_loudness_difference_within_2lu":receipt["pair_loudness_difference_within_2lu"],
            "scene_audio_review_flags":receipt["scene_audio_review_flags"],"publication_eligible":False}


def verify(voices,request,request_pin,output,pair_pin):
    root=ps.local_dir(output)
    obj,_,_=validate(request,request_pin)
    expected={"pair_dynamics.json"}|{l+s for l in LANGS for s in ("_master.wav","_dynamics.json")}
    expected|={f"{l}_{i:02}.wav" for l in LANGS for i in range(1,len(obj["scenes"])+1)}
    pv.require({p.name for p in root.iterdir()}==expected,"PAIR_INVENTORY")
    pinned(pv.read(root/"pair_dynamics.json",pv.MAX_JSON),pair_pin,pv.MAX_JSON)
    files,receipt=prepare(voices,request,request_pin)
    pv.require(set(files)==expected,"PREPARED_INVENTORY")
    for name,raw in files.items():
        pv.require(pv.read(root/name,len(raw))==raw,"PAIR_BYTES")
    return {"pair_dynamics_sha256":pair_pin,"fresh_dynamics_audit":True,
            "samples_per_track":receipt["samples_per_track"],
            "both_targets_within_1lu":receipt["both_targets_within_1lu"],
            "pair_loudness_difference_within_2lu":receipt["pair_loudness_difference_within_2lu"],
            "scene_audio_review_flags":receipt["scene_audio_review_flags"],"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("hindi","english","request","output"):a.add_argument("--"+name,type=Path,required=True)
        a.add_argument("--request-sha256",required=True)
        if mode=="verify":a.add_argument("--pair-dynamics-sha256",required=True)
    a=p.parse_args()
    try:
        args=({l:private_file(getattr(a,l),MAX_WAV) for l in LANGS},
              private_file(a.request,MAX_REQUEST),a.request_sha256,a.output)
        result=build(*args) if a.mode=="build" else verify(*args,a.pair_dynamics_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,OverflowError,
            struct.error,subprocess.SubprocessError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
