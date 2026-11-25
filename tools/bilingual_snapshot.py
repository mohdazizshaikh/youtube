"""Stopped paired-pilot backup and restore. Original pinned inputs remain required."""
from __future__ import annotations
import argparse
import json
import sqlite3
import wave
from pathlib import Path

from tools import bilingual_pilot as bp, pilot_snapshot as ps, pilot_run_verify as pv
from tools.narration_qc import private_file
from tools.narration_prepare import pinned, sha

SCHEMA = "VIRALOS_BILINGUAL_SNAPSHOT_V1"
LANGS = bp.LANGS


def pair_records(raw, pair_pin):
    obj = pv.decode(pinned(raw,pair_pin,bp.MAX_BOARDS))
    pv.require(type(obj) is dict and obj.get("schema")==bp.SCHEMA
               and obj.get("publication_eligible") is False
               and type(obj.get("runs")) is dict and set(obj["runs"])==set(LANGS),
               "PAIR_SCHEMA")
    for lang in LANGS:
        row=obj["runs"][lang]
        pv.require(type(row) is dict and set(row)=={"manifest_sha256","video_sha256","duration_ms"},
                   "PAIR_RUN")
        pv.pin(row["manifest_sha256"])
        pv.pin(row["video_sha256"])
        pv.require(type(row["duration_ms"]) is int and 0<row["duration_ms"]<=120000,
                   "PAIR_DURATION")
    pv.require(obj["runs"]["hindi"]["manifest_sha256"]!=obj["runs"]["english"]["manifest_sha256"],
               "PAIR_DUPLICATE")
    return obj["runs"]


def state(row):
    return {"revision":row["queue_revision"],"state":row["queue_state"]}


def inspect(snapshot,snapshot_pin,pair_pin):
    snapshot=ps.local_dir(snapshot)
    pv.require({p.name for p in snapshot.iterdir()}==set(LANGS)|{"pair.json","snapshot.json"},
               "PAIR_SNAPSHOT_INVENTORY")
    raw=pv.read(snapshot/"pair.json",bp.MAX_BOARDS)
    runs=pair_records(raw,pair_pin)
    meta=pv.decode(pinned(pv.read(snapshot/"snapshot.json",bp.MAX_BOARDS),snapshot_pin,bp.MAX_BOARDS))
    pv.require(type(meta) is dict and set(meta)=={"schema","pair_sha256","children","publication_eligible"}
               and meta["schema"]==SCHEMA and meta["pair_sha256"]==pair_pin
               and meta["publication_eligible"] is False,"PAIR_SNAPSHOT_SCHEMA")
    pv.require(type(meta["children"]) is dict and set(meta["children"])==set(LANGS),
               "PAIR_CHILDREN")
    for lang in LANGS:
        row=meta["children"][lang]
        pv.require(type(row) is dict and set(row)=={"snapshot_sha256","manifest_sha256","revision","state"},
                   "CHILD_FIELDS")
        pv.require(row["manifest_sha256"]==runs[lang]["manifest_sha256"],"CHILD_BINDING")
        child=ps.inspect(snapshot/lang,row["snapshot_sha256"],row["manifest_sha256"])
        pv.require(type(row["revision"]) is int and state(child)=={"revision":row["revision"],"state":row["state"]},
                   "CHILD_QUEUE")
    return meta


def distinct_output(output,source,inputs):
    output=ps.new_dir(output,source)
    # inputs tuple is the nine arguments accepted by bilingual_pilot.prepare.
    for path in (inputs[0],inputs[5]):
        ps.new_dir(output,ps.local_dir(path))
    return output


def backup(inputs,pair,pair_pin,output):
    pair=ps.local_dir(pair)
    output=distinct_output(output,pair,inputs)
    before=bp.verify(*inputs,pair,pair_pin)
    raw=pv.read(pair/"pair.json",bp.MAX_BOARDS)
    runs=pair_records(raw,pair_pin)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    children={}
    for lang in LANGS:
        manifest=runs[lang]["manifest_sha256"]
        result=ps.backup(pair/lang,output/lang,manifest)
        child=ps.inspect(output/lang,result["snapshot_sha256"],manifest)
        pv.require(state(child)==before["review_states"][lang],"QUEUE_CHANGED")
        children[lang]={"snapshot_sha256":result["snapshot_sha256"],"manifest_sha256":manifest,
                        **state(child)}
    pv.require(bp.verify(*inputs,pair,pair_pin)==before,"PAIR_CHANGED")
    # Recheck exact original DB bytes, not just revision numbers.
    for lang in LANGS:
        child=ps.inspect(output/lang,children[lang]["snapshot_sha256"],children[lang]["manifest_sha256"])
        pv.require(ps.inventory(pair/lang)==child["files"],"SOURCE_CHANGED")
    with (output/"pair.json").open("xb") as f:
        f.write(raw)
    meta={"schema":SCHEMA,"pair_sha256":pair_pin,"children":children,"publication_eligible":False}
    ps.write_json(output/"snapshot.json",meta)
    snapshot_pin=pv.file_hash(output/"snapshot.json",bp.MAX_BOARDS)
    marker.unlink()
    try:
        inspect(output,snapshot_pin,pair_pin)
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"snapshot_sha256":snapshot_pin,"pair_sha256":pair_pin,
            "review_states":before["review_states"],"publication_eligible":False}


def restore(inputs,snapshot,snapshot_pin,pair_pin,output):
    snapshot=ps.local_dir(snapshot)
    output=distinct_output(output,snapshot,inputs)
    meta=inspect(snapshot,snapshot_pin,pair_pin)
    # Validate original audio and board requests before any output.
    bp.prepare(*inputs)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    for lang in LANGS:
        row=meta["children"][lang]
        result=ps.restore(snapshot/lang,output/lang,row["snapshot_sha256"],row["manifest_sha256"])
        pv.require(state(result)=={"revision":row["revision"],"state":row["state"]},"RESTORE_QUEUE")
    raw=pinned(pv.read(snapshot/"pair.json",bp.MAX_BOARDS),pair_pin,bp.MAX_BOARDS)
    with (output/"pair.json").open("xb") as f:
        f.write(raw)
    pv.require(inspect(snapshot,snapshot_pin,pair_pin)==meta,"SNAPSHOT_CHANGED")
    marker.unlink()
    try:
        checked=bp.verify(*inputs,output,pair_pin)
        pv.require(checked["review_states"]=={l:{"revision":meta["children"][l]["revision"],
                   "state":meta["children"][l]["state"]} for l in LANGS},"RESTORE_QUEUE")
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"restored":True,"pair_sha256":pair_pin,"fresh_media_audit":True,
            "review_states":checked["review_states"],"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("backup","verify","restore"):
        a=sub.add_parser(mode)
        a.add_argument("--pair-sha256",required=True)
        a.add_argument("--snapshot",type=Path,required=True)
        if mode!="backup":a.add_argument("--snapshot-sha256",required=True)
        if mode!="verify":
            a.add_argument("--root",type=Path,required=True)
            for name in ("request","captions","bundle","boards"):
                a.add_argument("--"+name,type=Path,required=True)
                a.add_argument("--"+name+"-sha256",required=True)
            a.add_argument("--pair",type=Path,required=True)
    args=p.parse_args()
    try:
        if args.mode=="verify":
            inspect(args.snapshot,args.snapshot_sha256,args.pair_sha256)
            result={"snapshot_integrity_passed":True,"fresh_media_audit":False,"publication_eligible":False}
        else:
            inputs=(args.root,private_file(args.request,bp.bc.MAX_REQUEST),args.request_sha256,
                    private_file(args.captions,bp.bc.MAX_CAPTIONS),args.captions_sha256,
                    args.bundle,args.bundle_sha256,private_file(args.boards,bp.MAX_BOARDS),args.boards_sha256)
            result=(backup(inputs,args.pair,args.pair_sha256,args.snapshot) if args.mode=="backup" else
                    restore(inputs,args.snapshot,args.snapshot_sha256,args.pair_sha256,args.pair))
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,sqlite3.Error,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
