"""Stopped native production backup: original Hindi/English and native Hindi runs.

Font and native request remain separately pinned owner inputs. No release gate.
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import wave
from pathlib import Path
from fontTools.ttLib import TTLibError
from tools import native_hindi_pilot as nh, pilot_snapshot as ps, pilot_run_verify as pv
from tools import bilingual_pilot as bp
from tools.bilingual_snapshot import pair_records, state
from tools.narration_prepare import pinned, sha
from tools.narration_qc import private_file

SCHEMA="VIRALOS_NATIVE_PILOT_SNAPSHOT_V1"
KEYS=("original_hindi","english","native_hindi")


def receipt_records(pair_raw,pair_pin,native_raw,native_pin):
    runs=pair_records(pair_raw,pair_pin)
    native=pv.decode(pinned(native_raw,native_pin,nh.MAX_REQUEST))
    pv.require(type(native) is dict and native.get("schema")==nh.SCHEMA
               and native.get("parent_pair_sha256")==pair_pin
               and native.get("parent_hindi_manifest_sha256")==runs["hindi"]["manifest_sha256"]
               and native.get("english_manifest_sha256")==runs["english"]["manifest_sha256"]
               and native.get("duration_ms")==runs["hindi"]["duration_ms"]==runs["english"]["duration_ms"]
               and native.get("publication_eligible") is False
               and native.get("native_visual_accepted") is False
               and native.get("visual_mode") in nh.VISUAL_MODES,"NATIVE_BINDING")
    pins={"original_hindi":runs["hindi"]["manifest_sha256"],
          "english":runs["english"]["manifest_sha256"],"native_hindi":pv.pin(native["manifest_sha256"])}
    pv.require(len(set(pins.values()))==3,"DUPLICATE_CHILD")
    pv.pin(native["video_sha256"])
    pv.pin(native["font_sha256"])
    pv.pin(native["request_sha256"])
    return pins


def inspect(snapshot,snapshot_pin,pair_pin,native_pin):
    snapshot=ps.local_dir(snapshot)
    pv.require({p.name for p in snapshot.iterdir()}==set(KEYS)|{"pair.json","native.json","snapshot.json"},
               "SNAPSHOT_INVENTORY")
    pair_raw=pv.read(snapshot/"pair.json",bp.MAX_BOARDS)
    native_raw=pv.read(snapshot/"native.json",nh.MAX_REQUEST)
    pins=receipt_records(pair_raw,pair_pin,native_raw,native_pin)
    meta=pv.decode(pinned(pv.read(snapshot/"snapshot.json",nh.MAX_REQUEST),snapshot_pin,nh.MAX_REQUEST))
    pv.require(type(meta) is dict and set(meta)=={"schema","pair_sha256","native_sha256","children","publication_eligible"}
               and meta["schema"]==SCHEMA and meta["pair_sha256"]==pair_pin
               and meta["native_sha256"]==native_pin and meta["publication_eligible"] is False,
               "SNAPSHOT_SCHEMA")
    pv.require(type(meta["children"]) is dict and set(meta["children"])==set(KEYS),"CHILDREN")
    for key in KEYS:
        row=meta["children"][key]
        pv.require(type(row) is dict and set(row)=={"snapshot_sha256","manifest_sha256","revision","state"}
                   and row["manifest_sha256"]==pins[key] and type(row["revision"]) is int,"CHILD_FIELDS")
        child=ps.inspect(snapshot/key,row["snapshot_sha256"],pins[key])
        pv.require(state(child)=={"revision":row["revision"],"state":row["state"]},"CHILD_STATE")
    return meta


def source_runs(pair,native):
    return {"original_hindi":pair/"hindi","english":pair/"english","native_hindi":native/"hindi"}


def full_audit(pair,pair_pin,font,font_pin,request,request_pin,native,native_pin):
    checked=nh.verify(pair,pair_pin,font,font_pin,request,request_pin,native,native_pin)
    pair_raw=pv.read(pair/"pair.json",bp.MAX_BOARDS)
    native_raw=pv.read(native/"native.json",nh.MAX_REQUEST)
    pins=receipt_records(pair_raw,pair_pin,native_raw,native_pin)
    runs=source_runs(pair,native)
    states={key:state(pv.verify(runs[key],pins[key],fresh=False)) for key in KEYS}
    pv.require(states["native_hindi"]==checked["review_states"]["hindi"]
               and states["english"]==checked["review_states"]["english"],"STATE_CHANGED")
    return pair_raw,native_raw,pins,states


def backup(pair,pair_pin,font,font_pin,request,request_pin,native,native_pin,output):
    pair,native=ps.local_dir(pair),ps.local_dir(native)
    pv.require(not pair.is_relative_to(native) and not native.is_relative_to(pair),"SOURCE_OVERLAP")
    output=ps.new_dir(output,pair)
    ps.new_dir(output,native)
    pair_raw,native_raw,pins,states=full_audit(pair,pair_pin,font,font_pin,request,request_pin,native,native_pin)
    runs=source_runs(pair,native)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    children={}
    for key in KEYS:
        result=ps.backup(runs[key],output/key,pins[key])
        meta=ps.inspect(output/key,result["snapshot_sha256"],pins[key])
        pv.require(state(meta)==states[key],"STATE_CHANGED")
        children[key]={"snapshot_sha256":result["snapshot_sha256"],"manifest_sha256":pins[key],**states[key]}
    pv.require(full_audit(pair,pair_pin,font,font_pin,request,request_pin,native,native_pin)
               ==(pair_raw,native_raw,pins,states),"SOURCE_CHANGED")
    for key in KEYS:
        child=ps.inspect(output/key,children[key]["snapshot_sha256"],pins[key])
        pv.require(ps.inventory(runs[key])==child["files"],"SOURCE_BYTES_CHANGED")
    for name,raw in (("pair.json",pair_raw),("native.json",native_raw)):
        with (output/name).open("xb") as f:f.write(raw)
    ps.write_json(output/"snapshot.json",{"schema":SCHEMA,"pair_sha256":pair_pin,
                  "native_sha256":native_pin,"children":children,"publication_eligible":False})
    pin=pv.file_hash(output/"snapshot.json",nh.MAX_REQUEST)
    marker.unlink()
    try:inspect(output,pin,pair_pin,native_pin)
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"snapshot_sha256":pin,"pair_sha256":pair_pin,"native_sha256":native_pin,
            "review_states":states,"publication_eligible":False}


def restore(snapshot,snapshot_pin,pair_pin,native_pin,font,font_pin,request,request_pin,output):
    snapshot=ps.local_dir(snapshot)
    output=ps.new_dir(output,snapshot)
    meta=inspect(snapshot,snapshot_pin,pair_pin,native_pin)
    pair_raw=pv.read(snapshot/"pair.json",bp.MAX_BOARDS)
    native_raw=pv.read(snapshot/"native.json",nh.MAX_REQUEST)
    native_obj=pv.decode(native_raw)
    pv.require(native_obj["font_sha256"]==font_pin and native_obj["request_sha256"]==request_pin,
               "INPUT_BINDING")
    pinned(font,font_pin,nh.ht.MAX_FONT)
    pinned(request,request_pin,nh.MAX_REQUEST)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    pair,native=output/"pair",output/"native"
    pair.mkdir(mode=0o700)
    native.mkdir(mode=0o700)
    runs=source_runs(pair,native)
    for key in KEYS:
        row=meta["children"][key]
        result=ps.restore(snapshot/key,runs[key],row["snapshot_sha256"],row["manifest_sha256"])
        pv.require(state(result)=={"revision":row["revision"],"state":row["state"]},"RESTORE_STATE")
    for path,raw in ((pair/"pair.json",pair_raw),(native/"native.json",native_raw)):
        with path.open("xb") as f:f.write(raw)
    pv.require(inspect(snapshot,snapshot_pin,pair_pin,native_pin)==meta,"SNAPSHOT_CHANGED")
    _,_,_,states=full_audit(pair,pair_pin,font,font_pin,request,request_pin,native,native_pin)
    pv.require(states=={k:{"revision":meta["children"][k]["revision"],
               "state":meta["children"][k]["state"]} for k in KEYS},"RESTORE_STATE")
    marker.unlink()
    return {"restored":True,"pair_sha256":pair_pin,"native_sha256":native_pin,
            "fresh_media_audit":True,"review_states":states,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("backup","verify","restore"):
        a=sub.add_parser(mode)
        a.add_argument("--snapshot",type=Path,required=True)
        for name in ("pair","native"):a.add_argument("--"+name+"-sha256",required=True)
        if mode!="backup":a.add_argument("--snapshot-sha256",required=True)
        if mode!="verify":
            for name in ("font","request"):
                a.add_argument("--"+name,type=Path,required=True)
                a.add_argument("--"+name+"-sha256",required=True)
        if mode=="backup":
            a.add_argument("--pair",type=Path,required=True)
            a.add_argument("--native",type=Path,required=True)
        if mode=="restore":a.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.mode=="verify":
            inspect(a.snapshot,a.snapshot_sha256,a.pair_sha256,a.native_sha256)
            result={"snapshot_integrity_passed":True,"fresh_media_audit":False,"publication_eligible":False}
        else:
            font=private_file(a.font,nh.ht.MAX_FONT)
            request=private_file(a.request,nh.MAX_REQUEST)
            if a.mode=="backup":
                result=backup(a.pair,a.pair_sha256,font,a.font_sha256,request,a.request_sha256,
                              a.native,a.native_sha256,a.snapshot)
            else:
                result=restore(a.snapshot,a.snapshot_sha256,a.pair_sha256,a.native_sha256,
                               font,a.font_sha256,request,a.request_sha256,a.output)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,sqlite3.Error,wave.Error,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
