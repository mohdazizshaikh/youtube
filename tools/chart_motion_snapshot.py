"""Offline chart-motion pair and handoff snapshot with independently pinned receipts.

Original inputs and completed review/result files must be retained separately.
Stopped private storage only; no live-writer or power-loss guarantee.
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import subprocess
import wave
from pathlib import Path
from fontTools.ttLib import TTLibError
from tools import chart_motion_review as review, chart_pair_motion as cm
from tools import pilot_run_verify as pv, pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file
from tools.bilingual_pilot import json_bytes

SCHEMA="VIRALOS_CHART_MOTION_SNAPSHOT_V1"
LANGS=cm.LANGS
LIMITS={"motion/motion_pair.json":pv.MAX_JSON,"handoff/handoff.json":pv.MAX_JSON}
for lang in LANGS:
    LIMITS.update({f"motion/{lang}/motion.mp4":cm.motion.MAX_VIDEO,
                   f"motion/{lang}/captions.vtt":128000,
                   f"handoff/{lang}_packet.json":pv.MAX_JSON,
                   f"handoff/{lang}_review_template.json":review.mr.MAX_REVIEW})


def inventory(candidate,handoff):
    roots={"motion":ps.local_dir(candidate),"handoff":ps.local_dir(handoff)}
    pv.require({p.name for p in roots["motion"].iterdir()}==set(LANGS)|{"motion_pair.json"},
               "MOTION_INVENTORY")
    for lang in LANGS:
        folder=roots["motion"]/lang
        pv.plain(folder,True)
        pv.require({p.name for p in folder.iterdir()}=={"motion.mp4","captions.vtt"},"TRACK_INVENTORY")
    pv.require({p.name for p in roots["handoff"].iterdir()}==
               {name.split("/",1)[1] for name in LIMITS if name.startswith("handoff/")},
               "HANDOFF_INVENTORY")
    result={}
    for name,limit in LIMITS.items():
        folder,leaf=name.split("/",1)
        path=roots[folder]/leaf
        size=pv.plain(path).st_size
        pv.require(pv.exact_int(size,1,limit),"FILE_SIZE")
        result[name]={"bytes":size,"sha256":pv.file_hash(path,limit)}
    return result


def validate_meta(raw,snapshot_pin,motion_pin,handoff_pin):
    pv.pin(motion_pin)
    pv.pin(handoff_pin)
    obj=pv.decode(pinned(raw,snapshot_pin,pv.MAX_JSON))
    pv.require(type(obj) is dict and set(obj)=={"schema","motion_pair_sha256","handoff_sha256",
               "files","publication_eligible"} and obj["schema"]==SCHEMA
               and obj["motion_pair_sha256"]==motion_pin and obj["handoff_sha256"]==handoff_pin
               and obj["publication_eligible"] is False,"SNAPSHOT_BINDING")
    rows=obj["files"]
    pv.require(type(rows) is dict and set(rows)==set(LIMITS),"SNAPSHOT_FILES")
    for name,row in rows.items():
        pv.require(type(row) is dict and set(row)=={"bytes","sha256"}
                   and pv.exact_int(row["bytes"],1,LIMITS[name]),"FILE_RECORD")
        pv.pin(row["sha256"])
    pv.require(rows["motion/motion_pair.json"]["sha256"]==motion_pin and
               rows["handoff/handoff.json"]["sha256"]==handoff_pin,"RECEIPT_PINS")
    return obj


def binding(candidate,handoff,files,motion_pin,handoff_pin):
    motion=pv.decode(pinned(pv.read(candidate/"motion_pair.json",pv.MAX_JSON),motion_pin,pv.MAX_JSON))
    meta=pv.decode(pinned(pv.read(handoff/"handoff.json",pv.MAX_JSON),handoff_pin,pv.MAX_JSON))
    pv.require(type(motion) is dict and motion.get("schema")==cm.SCHEMA and
               motion.get("publication_eligible") is False and motion.get("editorial_queue_created") is False
               and motion.get("effect")=="VALUE_ROW_HIGHLIGHT_V1" and
               type(motion.get("tracks")) is dict and set(motion["tracks"])==set(LANGS),"MOTION_BINDING")
    pv.pin(motion["chart_pair_sha256"])
    pv.require(type(meta) is dict and set(meta)=={"schema","motion_pair_sha256","chart_pair_sha256",
               "languages","publication_eligible"} and meta["schema"]==review.HANDOFF
               and meta["publication_eligible"] is False and meta["motion_pair_sha256"]==motion_pin
               and meta["chart_pair_sha256"]==motion["chart_pair_sha256"]
               and type(meta["languages"]) is dict and set(meta["languages"])==set(LANGS),"HANDOFF_BINDING")
    parents={}
    packets={}
    for lang in LANGS:
        track=motion["tracks"][lang]
        packet=pv.document(handoff/(lang+"_packet.json"))
        pv.require(type(packet) is dict and packet.get("schema")==review.PACKET and
                   packet.get("language")==lang and packet.get("motion_sha256")==motion_pin and
                   packet.get("chart_pair_sha256")==motion["chart_pair_sha256"]
                   and packet.get("publication_eligible") is False and
                   packet.get("video_sha256")==track["motion_video_sha256"]==
                       files[f"motion/{lang}/motion.mp4"]["sha256"] and
                   packet.get("caption_sha256")==track["caption_sha256"]==
                       files[f"motion/{lang}/captions.vtt"]["sha256"],"TRACK_BINDING")
        # Reconstruct the embedded parent declaration and rederive both packets.
        # This checks internal consistency, not independent parent authenticity.
        parents[lang]={"manifest_sha256":track["parent_manifest_sha256"],
                       "video_sha256":track["parent_video_sha256"],"publication_eligible":False,
                       "synthetic_demo":packet["synthetic_demo"],
                       "scenes":[row["source_declaration"] for row in packet["scenes"]]}
        packets[lang]=packet
    pv.require(review.packets_from(motion,motion_pin,motion["chart_pair_sha256"],parents)==packets,
               "PACKET_BINDING")
    expected,_=review.payload(packets)
    for name,raw in expected.items():
        pv.require(pv.read(handoff/name,len(raw))==raw,"HANDOFF_BYTES")


def inspect(snapshot,snapshot_pin,motion_pin,handoff_pin,*,_building=False):
    snapshot=ps.local_dir(snapshot)
    expected={"motion","handoff","snapshot.json"}
    if _building:expected.add("INCOMPLETE")
    pv.require({x.name for x in snapshot.iterdir()}==expected,"SNAPSHOT_INVENTORY")
    obj=validate_meta(pv.read(snapshot/"snapshot.json",pv.MAX_JSON),snapshot_pin,motion_pin,handoff_pin)
    pv.require(inventory(snapshot/"motion",snapshot/"handoff")==obj["files"],"SNAPSHOT_BYTES")
    binding(snapshot/"motion",snapshot/"handoff",obj["files"],motion_pin,handoff_pin)
    return obj


def destination(output,args,*sources):
    for root in (*sources,args[0][0],args[0][2],args[1]):
        output=ps.new_dir(output,ps.local_dir(root))
    return output


def make_folders(root):
    for folder in ("motion","handoff","motion/hindi","motion/english"):
        (root/folder).mkdir(mode=0o700)


def backup(args,handoff,handoff_pin,output):
    candidate,handoff=ps.local_dir(args[5]),ps.local_dir(handoff)
    motion_pin=args[6]
    output=destination(output,args,candidate,handoff)
    before=review.verify(args,handoff,handoff_pin)
    records=inventory(candidate,handoff)
    binding(candidate,handoff,records,motion_pin,handoff_pin)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    make_folders(output)
    roots={"motion":candidate,"handoff":handoff}
    for name,row in records.items():
        folder,leaf=name.split("/",1)
        ps.copy_exact(roots[folder]/leaf,output/name,row,LIMITS[name])
    pv.require(review.verify(args,handoff,handoff_pin)==before and
               inventory(candidate,handoff)==records,"SOURCE_CHANGED")
    raw=json_bytes({"schema":SCHEMA,"motion_pair_sha256":motion_pin,"handoff_sha256":handoff_pin,
                    "files":records,"publication_eligible":False})
    review.mr.write_file(output/"snapshot.json",raw)
    pin=sha(raw)
    inspect(output,pin,motion_pin,handoff_pin,_building=True)
    marker.unlink()
    return {"snapshot_sha256":pin,"motion_pair_sha256":motion_pin,"handoff_sha256":handoff_pin,
            "publication_eligible":False}


def restore(args,snapshot,snapshot_pin,handoff_pin,output):
    # args uses None for old motion path; only original parent inputs are needed.
    snapshot=ps.local_dir(snapshot)
    motion_pin=args[6]
    output=destination(output,args,snapshot)
    obj=inspect(snapshot,snapshot_pin,motion_pin,handoff_pin)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    make_folders(output)
    for name,row in obj["files"].items():
        ps.copy_exact(snapshot/name,output/name,row,LIMITS[name])
    restored_args=(*args[:5],output/"motion",motion_pin)
    review.verify(restored_args,output/"handoff",handoff_pin)
    pv.require(inventory(output/"motion",output/"handoff")==obj["files"] and
               inspect(snapshot,snapshot_pin,motion_pin,handoff_pin)==obj,"RESTORE_CHANGED")
    marker.unlink()
    return {"restored":True,"fresh_media_audit":True,"motion_pair_sha256":motion_pin,
            "handoff_sha256":handoff_pin,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("backup","verify","restore"):
        a=sub.add_parser(mode)
        a.add_argument("--snapshot",type=Path,required=True)
        a.add_argument("--motion-sha256",required=True)
        a.add_argument("--handoff-sha256",required=True)
        if mode!="backup":a.add_argument("--snapshot-sha256",required=True)
        if mode!="verify":
            for name in ("pair","root","chart-request","hindi-font","english-font","chart-pair","request"):
                a.add_argument("--"+name,type=Path,required=True)
            for name in ("pair","chart-request","hindi-font","english-font","chart-pair","request"):
                a.add_argument("--"+name+"-sha256",required=True)
            if mode=="backup":
                a.add_argument("--motion",type=Path,required=True)
                a.add_argument("--handoff",type=Path,required=True)
            else:a.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.mode=="verify":
            inspect(a.snapshot,a.snapshot_sha256,a.motion_sha256,a.handoff_sha256)
            result={"snapshot_integrity_passed":True,"fresh_media_audit":False,"publication_eligible":False}
        else:
            inputs=(a.pair,a.pair_sha256,a.root,private_file(a.chart_request,cm.cp.MAX_REQUEST),
                    a.chart_request_sha256,
                    {l:private_file(getattr(a,l+"_font"),cm.cp.chart.ht.MAX_FONT) for l in LANGS},
                    {l:getattr(a,l+"_font_sha256") for l in LANGS})
            args=(inputs,a.chart_pair,a.chart_pair_sha256,private_file(a.request,cm.MAX_REQUEST),
                  a.request_sha256,getattr(a,"motion",None),a.motion_sha256)
            result=(backup(args,a.handoff,a.handoff_sha256,a.snapshot) if a.mode=="backup" else
                    restore(args,a.snapshot,a.snapshot_sha256,a.handoff_sha256,a.output))
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,sqlite3.Error,
            subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
