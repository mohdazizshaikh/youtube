"""Stopped chart-pair snapshot and fresh restore. Source files and fonts retained separately."""
from __future__ import annotations
import argparse
import json
import sqlite3
import subprocess
import wave
from pathlib import Path
from fontTools.ttLib import TTLibError
from tools import bilingual_chart_pilot as cp, chart_review_dashboard as dashboard
from tools import pilot_snapshot as ps, pilot_run_verify as pv
from tools.bilingual_snapshot import state
from tools.paired_mix_snapshot import write_raw
from tools.narration_prepare import pinned
from tools.narration_qc import private_file

SCHEMA="VIRALOS_CHART_PAIR_SNAPSHOT_V1"
LANGS=cp.LANGS

def inspect(snapshot,snapshot_pin,chart_pair_pin):
    snapshot=ps.local_dir(snapshot)
    pv.require({p.name for p in snapshot.iterdir()}==set(LANGS)|{"chart_pair.json","snapshot.json"},
               "CHART_SNAPSHOT_INVENTORY")
    raw=pv.read(snapshot/"chart_pair.json",cp.MAX_REQUEST)
    runs=dashboard.records(raw,chart_pair_pin)["runs"]
    meta=pv.decode(pinned(pv.read(snapshot/"snapshot.json",cp.MAX_REQUEST),snapshot_pin,cp.MAX_REQUEST))
    pv.require(type(meta) is dict and set(meta)=={"schema","chart_pair_sha256","children","publication_eligible"}
               and meta["schema"]==SCHEMA and meta["chart_pair_sha256"]==chart_pair_pin
               and meta["publication_eligible"] is False,"CHART_SNAPSHOT_SCHEMA")
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
        pv.require(child["files"]["draft/draft.mp4"]["sha256"]==runs[lang]["video_sha256"],"CHILD_VIDEO")
    return meta


def distinct_output(output,source,inputs):
    output=ps.new_dir(output,source)
    # Original pair and private chart input directory stay separate.
    for path in (inputs[0],inputs[2]):
        ps.new_dir(output,ps.local_dir(path))
    return output


def backup(inputs,pair,chart_pair_pin,output):
    pair=ps.local_dir(pair)
    output=distinct_output(output,pair,inputs)
    before=cp.verify(inputs,pair,chart_pair_pin)
    raw=pv.read(pair/"chart_pair.json",cp.MAX_REQUEST)
    runs=dashboard.records(raw,chart_pair_pin)["runs"]
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
    pv.require(cp.verify(inputs,pair,chart_pair_pin)==before,"PAIR_CHANGED")
    # Recheck exact original DB bytes, not just revision numbers.
    for lang in LANGS:
        child=ps.inspect(output/lang,children[lang]["snapshot_sha256"],children[lang]["manifest_sha256"])
        pv.require(ps.inventory(pair/lang)==child["files"],"SOURCE_CHANGED")
    write_raw(output/"chart_pair.json",raw)
    meta={"schema":SCHEMA,"chart_pair_sha256":chart_pair_pin,"children":children,"publication_eligible":False}
    ps.write_json(output/"snapshot.json",meta)
    snapshot_pin=pv.file_hash(output/"snapshot.json",cp.MAX_REQUEST)
    marker.unlink()
    try:
        inspect(output,snapshot_pin,chart_pair_pin)
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"snapshot_sha256":snapshot_pin,"chart_pair_sha256":chart_pair_pin,
            "review_states":before["review_states"],"publication_eligible":False}


def restore(inputs,snapshot,snapshot_pin,chart_pair_pin,output):
    snapshot=ps.local_dir(snapshot)
    output=distinct_output(output,snapshot,inputs)
    meta=inspect(snapshot,snapshot_pin,chart_pair_pin)
    # Validate original audio and board requests before any output.
    obj=dashboard.records(pv.read(snapshot/"chart_pair.json",cp.MAX_REQUEST),chart_pair_pin)
    pv.require(obj["pair_sha256"]==inputs[1] and obj["request_sha256"]==inputs[4],"INPUT_BINDING")
    cp.prepare(*inputs)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    for lang in LANGS:
        row=meta["children"][lang]
        result=ps.restore(snapshot/lang,output/lang,row["snapshot_sha256"],row["manifest_sha256"])
        pv.require(state(result)=={"revision":row["revision"],"state":row["state"]},"RESTORE_QUEUE")
    raw=pinned(pv.read(snapshot/"chart_pair.json",cp.MAX_REQUEST),chart_pair_pin,cp.MAX_REQUEST)
    write_raw(output/"chart_pair.json",raw)
    pv.require(inspect(snapshot,snapshot_pin,chart_pair_pin)==meta,"SNAPSHOT_CHANGED")
    marker.unlink()
    try:
        checked=cp.verify(inputs,output,chart_pair_pin)
        pv.require(checked["review_states"]=={l:{"revision":meta["children"][l]["revision"],
                   "state":meta["children"][l]["state"]} for l in LANGS},"RESTORE_QUEUE")
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"restored":True,"chart_pair_sha256":chart_pair_pin,"fresh_media_audit":True,
            "review_states":checked["review_states"],"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("backup","verify","restore"):
        a=sub.add_parser(mode)
        a.add_argument("--chart-pair-sha256",required=True)
        a.add_argument("--snapshot",type=Path,required=True)
        if mode!="backup":a.add_argument("--snapshot-sha256",required=True)
        if mode!="verify":
            for name in ("pair","root","request","hindi-font","english-font","chart-pair"):
                a.add_argument("--"+name,type=Path,required=True)
            for name in ("pair","request","hindi-font","english-font"):
                a.add_argument("--"+name+"-sha256",required=True)
    a=p.parse_args()
    try:
        if a.mode=="verify":
            inspect(a.snapshot,a.snapshot_sha256,a.chart_pair_sha256)
            result={"snapshot_integrity_passed":True,"fresh_media_audit":False,"publication_eligible":False}
        else:
            inputs=(a.pair,a.pair_sha256,a.root,private_file(a.request,cp.MAX_REQUEST),a.request_sha256,
                    {l:private_file(getattr(a,l+"_font"),cp.chart.ht.MAX_FONT) for l in LANGS},
                    {l:getattr(a,l+"_font_sha256") for l in LANGS})
            result=(backup(inputs,a.chart_pair,a.chart_pair_sha256,a.snapshot) if a.mode=="backup" else
                    restore(inputs,a.snapshot,a.snapshot_sha256,a.chart_pair_sha256,a.chart_pair))
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,sqlite3.Error,
            subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
