"""Offline paired mixed-production derivative; retain both independent parent runs."""
from __future__ import annotations
import argparse
import json
import sqlite3
import subprocess
import wave
from pathlib import Path

from tools import production_mix_pilot as pm, bilingual_review_dashboard as dash
from tools import pilot_run_verify as pv, pilot_snapshot as ps, bilingual_pilot as bp
from tools.narration_prepare import pinned, sha
from tools.narration_qc import private_file, MAX_WAV

REQUEST="VIRALOS_PAIRED_PRODUCTION_MIX_REQUEST_V1"
SCHEMA="VIRALOS_PAIRED_PRODUCTION_MIX_V1"
MAX_REQUEST=128000
LANGS=dash.LANGS


def validate(raw,request_pin,pair_pin,native_pin):
    pv.pin(pair_pin)
    if native_pin is not None:pv.pin(native_pin)
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","pair_sha256","native_sha256","tracks"}
               and obj["schema"]==REQUEST and obj["pair_sha256"]==pair_pin
               and obj["native_sha256"]==native_pin,"PAIR_REQUEST")
    pv.require(type(obj["tracks"]) is dict and set(obj["tracks"])==set(LANGS),"TRACKS")
    result={}
    for lang in LANGS:
        row=obj["tracks"][lang]
        pv.require(type(row) is dict and "parent_manifest_sha256" in row,"TRACK_REQUEST")
        sub=bp.json_bytes(row)
        pm.validate(sub,sha(sub),row["parent_manifest_sha256"])
        result[lang]=sub
    pv.require(obj["tracks"]["hindi"]["parent_manifest_sha256"]!=
               obj["tracks"]["english"]["parent_manifest_sha256"],"DUPLICATE_PARENT")
    return result


def inputs(pair,pair_pin,native,native_pin,request,request_pin,music):
    runs,duration=dash.select_runs(pair,pair_pin,native,native_pin)
    before=dash.snapshot(runs,duration,fresh=True)
    pv.require(3000<=duration<=120000,"PAIR_MIX_DURATION")
    requests=validate(request,request_pin,pair_pin,native_pin)
    pv.require(type(music) is dict and set(music)==set(LANGS),"MUSIC_TRACKS")
    for lang in LANGS:
        _,pin,_=runs[lang]
        obj,_=pm.validate(requests[lang],sha(requests[lang]),pin)
        cfg=obj["audio_request"] if obj["mode"]=="STATIC" else obj["audio_request"]["mix"]
        pinned(music[lang],cfg["music_sha256"],MAX_WAV)
    return runs,duration,requests,before


def track_receipt(path,pin,parent_pin,request_pin,duration):
    path=ps.local_dir(path)
    pv.require({p.name for p in path.iterdir()}=={"run","mix.json"},"TRACK_INVENTORY")
    obj=pv.decode(pinned(pv.read(path/"mix.json",pm.MAX_REQUEST),pin,pm.MAX_REQUEST))
    pv.require(type(obj) is dict and obj.get("schema")==pm.SCHEMA
               and obj.get("parent_manifest_sha256")==parent_pin
               and obj.get("request_sha256")==request_pin and obj.get("duration_ms")==duration
               and obj.get("publication_eligible") is False,"TRACK_BINDING")
    return {"mix_sha256":pin,"manifest_sha256":pv.pin(obj["manifest_sha256"]),
            "video_sha256":pv.pin(obj["video_sha256"]),"duration_ms":duration}


def receipt(pair_pin,native_pin,request_pin,duration,tracks):
    pv.require(tracks["hindi"]["manifest_sha256"]!=tracks["english"]["manifest_sha256"],"DUPLICATE_CHILD")
    return {"schema":SCHEMA,"pair_sha256":pair_pin,"native_sha256":native_pin,
            "request_sha256":request_pin,"duration_ms":duration,"tracks":tracks,
            "human_listening_required":True,"translation_verified":False,
            "human_review_verified":False,"publication_eligible":False}


def build(pair,pair_pin,native,native_pin,request,request_pin,music,output):
    pair=ps.local_dir(pair)
    output=ps.new_dir(output,pair)
    if native is not None:ps.new_dir(output,ps.local_dir(native))
    runs,duration,requests,before=inputs(pair,pair_pin,native,native_pin,request,request_pin,music)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    tracks={}
    for lang in LANGS:
        parent,pin,_=runs[lang]
        result=pm.build(parent,pin,music[lang],requests[lang],sha(requests[lang]),output/lang)
        tracks[lang]=track_receipt(output/lang,result["mix_sha256"],pin,sha(requests[lang]),duration)
    obj=receipt(pair_pin,native_pin,request_pin,duration,tracks)
    raw=bp.json_bytes(obj)
    with (output/"pair_mix.json").open("xb") as f:f.write(raw)
    pv.require(dash.select_runs(pair,pair_pin,native,native_pin)==(runs,duration)
               and dash.snapshot(runs,duration)=={**before,"fresh_media_audit":False},"PARENT_CHANGED")
    pv.require({p.name for p in output.iterdir()}==set(LANGS)|{"pair_mix.json","INCOMPLETE"},"PAIR_MIX_INVENTORY")
    marker.unlink()
    try:
        report=verify(pair,pair_pin,native,native_pin,request,request_pin,music,output,sha(raw))
        pv.require(all(x=={"revision":0,"state":"PENDING"} for x in report["review_states"].values()),"NEW_QUEUES")
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"pair_mix_sha256":sha(raw),"duration_ms":duration,"tracks":tracks,"publication_eligible":False}


def verify(pair,pair_pin,native,native_pin,request,request_pin,music,output,pair_mix_pin):
    output=ps.local_dir(output)
    pv.require({p.name for p in output.iterdir()}==set(LANGS)|{"pair_mix.json"},"PAIR_MIX_INVENTORY")
    raw=pinned(pv.read(output/"pair_mix.json",MAX_REQUEST),pair_mix_pin,MAX_REQUEST)
    obj=pv.decode(raw)
    pv.require(type(obj) is dict and obj.get("schema")==SCHEMA
               and type(obj.get("tracks")) is dict and set(obj["tracks"])==set(LANGS),"PAIR_MIX_SCHEMA")
    runs,duration,requests,before=inputs(pair,pair_pin,native,native_pin,request,request_pin,music)
    tracks,states={},{}
    for lang in LANGS:
        parent,pin,_=runs[lang]
        child_pin=pv.pin(obj["tracks"][lang]["mix_sha256"])
        check=pm.verify(parent,pin,music[lang],requests[lang],sha(requests[lang]),output/lang,child_pin)
        tracks[lang]=track_receipt(output/lang,child_pin,pin,sha(requests[lang]),duration)
        states[lang]={"revision":check["queue_revision"],"state":check["queue_state"]}
    pv.require(raw==bp.json_bytes(receipt(pair_pin,native_pin,request_pin,duration,tracks)),"PAIR_MIX_RECEIPT")
    pv.require(dash.select_runs(pair,pair_pin,native,native_pin)==(runs,duration)
               and dash.snapshot(runs,duration)=={**before,"fresh_media_audit":False},"PARENT_CHANGED")
    return {"pair_mix_sha256":pair_mix_pin,"fresh_media_audit":True,"review_states":states,
            "duration_ms":duration,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("pair","native","request","hindi-music","english-music","output"):
            a.add_argument("--"+name,type=Path,required=name!="native")
        a.add_argument("--pair-sha256",required=True)
        a.add_argument("--native-sha256")
        a.add_argument("--request-sha256",required=True)
        if mode=="verify":a.add_argument("--pair-mix-sha256",required=True)
    a=p.parse_args()
    try:
        music={lang:private_file(getattr(a,lang+"_music"),MAX_WAV) for lang in LANGS}
        args=(a.pair,a.pair_sha256,a.native,a.native_sha256,
              private_file(a.request,MAX_REQUEST),a.request_sha256,music,a.output)
        result=build(*args) if a.mode=="build" else verify(*args,a.pair_mix_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,
            sqlite3.Error,subprocess.SubprocessError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
