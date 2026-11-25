"""Stopped paired mixed-derivative backup and non-destructive restore.

Parents, source music and request remain separately retained owner inputs.
No publication authorization or concurrent-writer protection.
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import subprocess
import wave
from pathlib import Path

from tools import paired_production_mix as pm, pilot_snapshot as ps, pilot_run_verify as pv
from tools.bilingual_snapshot import state
from tools.narration_prepare import pinned, sha
from tools.narration_qc import private_file, MAX_WAV

SCHEMA="VIRALOS_PAIRED_MIX_SNAPSHOT_V1"
LANGS=pm.LANGS
MAX_JSON=pm.MAX_REQUEST
STATES={"PENDING","DEMO_BLOCKED","SELF_ATTESTED","NEEDS_REVISION","INCOMPLETE"}


def pair_records(raw,pair_mix_pin):
    obj=pv.decode(pinned(raw,pair_mix_pin,MAX_JSON))
    pv.require(type(obj) is dict and set(obj)=={"schema","pair_sha256","native_sha256",
               "request_sha256","duration_ms","tracks","human_listening_required",
               "translation_verified","human_review_verified","publication_eligible"},"PAIR_FIELDS")
    pv.require(obj["schema"]==pm.SCHEMA and obj["human_listening_required"] is True
               and all(obj[k] is False for k in ("translation_verified","human_review_verified",
                                                  "publication_eligible")),"PAIR_FLAGS")
    for k in ("pair_sha256","request_sha256"):pv.pin(obj[k])
    if obj["native_sha256"] is not None:pv.pin(obj["native_sha256"])
    pv.require(pv.exact_int(obj["duration_ms"],3000,120000) and obj["duration_ms"]%40==0,"PAIR_DURATION")
    tracks=obj["tracks"]
    pv.require(type(tracks) is dict and set(tracks)==set(LANGS),"TRACKS")
    for row in tracks.values():
        pv.require(type(row) is dict and set(row)=={"mix_sha256","manifest_sha256","video_sha256",
                   "duration_ms"} and type(row["duration_ms"]) is int
                   and row["duration_ms"]==obj["duration_ms"],"TRACK_FIELDS")
        for k in ("mix_sha256","manifest_sha256","video_sha256"):pv.pin(row[k])
    for key in ("mix_sha256","manifest_sha256"):
        pv.require(tracks["hindi"][key]!=tracks["english"][key],"DUPLICATE_CHILD")
    return obj


def track_record(raw,row):
    obj=pv.decode(pinned(raw,row["mix_sha256"],pm.pm.MAX_REQUEST))
    pv.require(type(obj) is dict and obj.get("schema")==pm.pm.SCHEMA
               and obj.get("publication_eligible") is False,"TRACK_RECEIPT")
    pv.require(all(obj.get(k)==row[k] for k in ("manifest_sha256","video_sha256","duration_ms")),
               "TRACK_BINDING")
    return obj


def inspect(snapshot,snapshot_pin,pair_mix_pin):
    snapshot=ps.local_dir(snapshot)
    pv.require({p.name for p in snapshot.iterdir()}==set(LANGS)|{"pair_mix.json","snapshot.json"},
               "SNAPSHOT_INVENTORY")
    obj=pair_records(pv.read(snapshot/"pair_mix.json",MAX_JSON),pair_mix_pin)
    meta=pv.decode(pinned(pv.read(snapshot/"snapshot.json",MAX_JSON),snapshot_pin,MAX_JSON))
    pv.require(type(meta) is dict and set(meta)=={"schema","pair_mix_sha256","children","publication_eligible"}
               and meta["schema"]==SCHEMA and meta["pair_mix_sha256"]==pair_mix_pin
               and meta["publication_eligible"] is False,"SNAPSHOT_SCHEMA")
    pv.require(type(meta["children"]) is dict and set(meta["children"])==set(LANGS),"CHILDREN")
    for lang in LANGS:
        child=ps.local_dir(snapshot/lang)
        pv.require({p.name for p in child.iterdir()}=={"mix.json","run"},"CHILD_INVENTORY")
        track=obj["tracks"][lang]
        track_record(pv.read(child/"mix.json",pm.pm.MAX_REQUEST),track)
        row=meta["children"][lang]
        pv.require(type(row) is dict and set(row)=={"snapshot_sha256","manifest_sha256",
                    "revision","state"} and row["manifest_sha256"]==track["manifest_sha256"]
                    and pv.exact_int(row["revision"],0,100000) and row["state"] in STATES,"CHILD_FIELDS")
        checked=ps.inspect(child/"run",row["snapshot_sha256"],row["manifest_sha256"])
        pv.require(state(checked)=={"revision":row["revision"],"state":row["state"]},"CHILD_STATE")
        pv.require(checked["files"]["draft/draft.mp4"]["sha256"]==track["video_sha256"],"VIDEO_BINDING")
    return meta


def new_output(output,source,inputs):
    output=ps.new_dir(output,source)
    for path in (inputs[0],inputs[2]):
        if path is not None:ps.new_dir(output,ps.local_dir(path))
    return output


def write_raw(path,raw):
    import os
    with path.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    pv.require(pv.read(path,len(raw))==raw,"RECEIPT_WRITE")


def backup(inputs,mixed,pair_mix_pin,output):
    mixed=ps.local_dir(mixed)
    output=new_output(output,mixed,inputs)
    before=pm.verify(*inputs,mixed,pair_mix_pin)
    pair_raw=pv.read(mixed/"pair_mix.json",MAX_JSON)
    obj=pair_records(pair_raw,pair_mix_pin)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    rows={}
    for lang in LANGS:
        track=obj["tracks"][lang]
        source=mixed/lang
        child=output/lang
        child.mkdir(mode=0o700)
        raw=pv.read(source/"mix.json",pm.pm.MAX_REQUEST)
        track_record(raw,track)
        write_raw(child/"mix.json",raw)
        report=ps.backup(source/"run",child/"run",track["manifest_sha256"])
        checked=ps.inspect(child/"run",report["snapshot_sha256"],track["manifest_sha256"])
        pv.require(state(checked)==before["review_states"][lang],"STATE_CHANGED")
        rows[lang]={"snapshot_sha256":report["snapshot_sha256"],
                    "manifest_sha256":track["manifest_sha256"],**state(checked)}
    pv.require(pm.verify(*inputs,mixed,pair_mix_pin)==before,"SOURCE_CHANGED")
    for lang in LANGS:
        row=rows[lang]
        checked=ps.inspect(output/lang/"run",row["snapshot_sha256"],row["manifest_sha256"])
        pv.require(ps.inventory(mixed/lang/"run")==checked["files"],"SOURCE_BYTES_CHANGED")
        pv.require(pv.read(mixed/lang/"mix.json",pm.pm.MAX_REQUEST)==
                   pv.read(output/lang/"mix.json",pm.pm.MAX_REQUEST),"RECEIPT_CHANGED")
    write_raw(output/"pair_mix.json",pair_raw)
    ps.write_json(output/"snapshot.json",{"schema":SCHEMA,"pair_mix_sha256":pair_mix_pin,
                   "children":rows,"publication_eligible":False})
    pin=pv.file_hash(output/"snapshot.json",MAX_JSON)
    marker.unlink()
    try:inspect(output,pin,pair_mix_pin)
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"snapshot_sha256":pin,"pair_mix_sha256":pair_mix_pin,
            "review_states":before["review_states"],"publication_eligible":False}


def restore(inputs,snapshot,snapshot_pin,pair_mix_pin,output):
    snapshot=ps.local_dir(snapshot)
    output=new_output(output,snapshot,inputs)
    meta=inspect(snapshot,snapshot_pin,pair_mix_pin)
    raw=pv.read(snapshot/"pair_mix.json",MAX_JSON)
    obj=pair_records(raw,pair_mix_pin)
    pair,pair_pin,native,native_pin,request,request_pin,music=inputs
    pv.require((obj["pair_sha256"],obj["native_sha256"],obj["request_sha256"])==
               (pair_pin,native_pin,request_pin),"INPUT_BINDING")
    pm.inputs(*inputs)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    for lang in LANGS:
        child=output/lang
        child.mkdir(mode=0o700)
        row=meta["children"][lang]
        result=ps.restore(snapshot/lang/"run",child/"run",row["snapshot_sha256"],row["manifest_sha256"])
        pv.require(state(result)=={"revision":row["revision"],"state":row["state"]},"RESTORE_STATE")
        write_raw(child/"mix.json",pv.read(snapshot/lang/"mix.json",pm.pm.MAX_REQUEST))
    write_raw(output/"pair_mix.json",raw)
    pv.require(inspect(snapshot,snapshot_pin,pair_mix_pin)==meta,"SNAPSHOT_CHANGED")
    marker.unlink()
    try:
        verified=pm.verify(*inputs,output,pair_mix_pin)
        pv.require(verified["review_states"]=={l:{"revision":meta["children"][l]["revision"],
                   "state":meta["children"][l]["state"]} for l in LANGS},"RESTORE_STATE")
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"restored":True,"fresh_media_audit":True,"pair_mix_sha256":pair_mix_pin,
            "review_states":verified["review_states"],"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("backup","verify","restore"):
        a=sub.add_parser(mode)
        a.add_argument("--snapshot",type=Path,required=True)
        a.add_argument("--pair-mix-sha256",required=True)
        if mode!="backup":a.add_argument("--snapshot-sha256",required=True)
        if mode!="verify":
            for name in ("pair","native","request","hindi-music","english-music","mixed"):
                a.add_argument("--"+name,type=Path,required=name!="native")
            a.add_argument("--pair-sha256",required=True)
            a.add_argument("--native-sha256")
            a.add_argument("--request-sha256",required=True)
    a=p.parse_args()
    try:
        if a.mode=="verify":
            inspect(a.snapshot,a.snapshot_sha256,a.pair_mix_sha256)
            result={"snapshot_integrity_passed":True,"fresh_media_audit":False,"publication_eligible":False}
        else:
            inputs=(a.pair,a.pair_sha256,a.native,a.native_sha256,private_file(a.request,MAX_JSON),
                    a.request_sha256,{l:private_file(getattr(a,l+"_music"),MAX_WAV) for l in LANGS})
            result=(backup(inputs,a.mixed,a.pair_mix_sha256,a.snapshot) if a.mode=="backup" else
                    restore(inputs,a.snapshot,a.snapshot_sha256,a.pair_mix_sha256,a.mixed))
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,
            sqlite3.Error,subprocess.SubprocessError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
