"""Stopped motion candidate + handoff snapshot. Original inputs remain separately retained."""
from __future__ import annotations
import argparse
import json
import sqlite3
import subprocess
import wave
from pathlib import Path
from fontTools.ttLib import TTLibError
from tools import motion_review as review,native_flow_motion as motion,pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha

SCHEMA="VIRALOS_MOTION_SNAPSHOT_V1"
LIMITS={"motion/motion.mp4":motion.MAX_VIDEO,"motion/motion.json":pv.MAX_JSON,
        "motion/captions.vtt":128000,"handoff/packet.json":pv.MAX_JSON,
        "handoff/review_template.json":review.MAX_REVIEW}


def inventory(root):
    result={}
    for folder in ("motion","handoff"):
        pv.plain(root/folder,True)
        pv.require({p.name for p in (root/folder).iterdir()}==
                   {k.split("/")[1] for k in LIMITS if k.startswith(folder+"/")},"PAYLOAD_INVENTORY")
    for name,limit in LIMITS.items():
        path=root/name
        result[name]={"bytes":pv.plain(path).st_size,"sha256":pv.file_hash(path,limit)}
    return result


def validate_meta(raw,snapshot_pin,motion_pin,packet_pin):
    pv.pin(motion_pin)
    pv.pin(packet_pin)
    obj=pv.decode(pinned(raw,snapshot_pin,pv.MAX_JSON))
    pv.require(type(obj) is dict and set(obj)=={"schema","motion_sha256","packet_file_sha256","files","publication_eligible"}
               and obj["schema"]==SCHEMA and obj["motion_sha256"]==motion_pin
               and obj["packet_file_sha256"]==packet_pin and obj["publication_eligible"] is False,"SNAPSHOT_BINDING")
    rows=obj["files"]
    pv.require(type(rows) is dict and set(rows)==set(LIMITS),"SNAPSHOT_FILES")
    for name,row in rows.items():
        pv.require(type(row) is dict and set(row)=={"bytes","sha256"}
                   and pv.exact_int(row["bytes"],1,LIMITS[name]),"FILE_RECORD")
        pv.pin(row["sha256"])
    pv.require(rows["motion/motion.json"]["sha256"]==motion_pin and
               rows["handoff/packet.json"]["sha256"]==packet_pin,"FILE_PIN")
    return obj


def inspect(snapshot,snapshot_pin,motion_pin,packet_pin):
    snapshot=ps.local_dir(snapshot)
    pv.require({x.name for x in snapshot.iterdir()}=={"motion","handoff","snapshot.json"},"SNAPSHOT_INVENTORY")
    meta=validate_meta(pv.read(snapshot/"snapshot.json",pv.MAX_JSON),snapshot_pin,motion_pin,packet_pin)
    pv.require(inventory(snapshot)==meta["files"],"SNAPSHOT_BYTES")
    receipt=pv.document(snapshot/"motion"/"motion.json")
    obj=pv.document(snapshot/"handoff"/"packet.json")
    pv.require(receipt.get("schema")==motion.SCHEMA and obj.get("schema")==review.PACKET
               and receipt.get("publication_eligible") is False and obj.get("publication_eligible") is False
               and obj.get("motion_sha256")==motion_pin
               and obj.get("video_sha256")==receipt.get("motion_video_sha256")==meta["files"]["motion/motion.mp4"]["sha256"]
               and obj.get("caption_sha256")==receipt.get("caption_sha256")==meta["files"]["motion/captions.vtt"]["sha256"],
               "PAYLOAD_BINDING")
    pv.require(pv.read(snapshot/"handoff"/"review_template.json",review.MAX_REVIEW)==
               review.json_bytes(review.template(obj)),"TEMPLATE_BINDING")
    return meta


def output_path(output,inputs,*sources):
    for root in (*sources,inputs[0],inputs[6]):
        output=ps.new_dir(output,ps.local_dir(root))
    return output


def backup(inputs,candidate,motion_pin,handoff,packet_pin,output):
    candidate,handoff=ps.local_dir(candidate),ps.local_dir(handoff)
    output=output_path(output,inputs,candidate,handoff)
    before=review.verify_handoff(inputs,candidate,motion_pin,handoff,packet_pin)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    records={}
    roots={"motion":candidate,"handoff":handoff}
    for folder in roots:(output/folder).mkdir(mode=0o700)
    for name,limit in LIMITS.items():
        folder,leaf=name.split("/")
        source=roots[folder]/leaf
        row={"bytes":pv.plain(source).st_size,"sha256":pv.file_hash(source,limit)}
        ps.copy_exact(source,output/name,row,limit)
        records[name]=row
    pv.require(review.verify_handoff(inputs,candidate,motion_pin,handoff,packet_pin)==before,"SOURCE_CHANGED")
    for name,row in records.items():
        folder,leaf=name.split("/")
        pv.require(pv.file_hash(roots[folder]/leaf,LIMITS[name])==row["sha256"],"SOURCE_BYTES_CHANGED")
    ps.write_json(output/"snapshot.json",{"schema":SCHEMA,"motion_sha256":motion_pin,
                   "packet_file_sha256":packet_pin,"files":records,"publication_eligible":False})
    pin=pv.file_hash(output/"snapshot.json",pv.MAX_JSON)
    marker.unlink()
    try:inspect(output,pin,motion_pin,packet_pin)
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"snapshot_sha256":pin,"motion_sha256":motion_pin,"packet_file_sha256":packet_pin,
            "publication_eligible":False}


def restore(inputs,snapshot,snapshot_pin,motion_pin,packet_pin,output):
    snapshot=ps.local_dir(snapshot)
    output=output_path(output,inputs,snapshot)
    meta=inspect(snapshot,snapshot_pin,motion_pin,packet_pin)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    for folder in ("motion","handoff"):(output/folder).mkdir(mode=0o700)
    for name,row in meta["files"].items():ps.copy_exact(snapshot/name,output/name,row,LIMITS[name])
    pv.require(inventory(output)==meta["files"] and inspect(snapshot,snapshot_pin,motion_pin,packet_pin)==meta,
               "RESTORE_BYTES")
    review.verify_handoff(inputs,output/"motion",motion_pin,output/"handoff",packet_pin)
    pv.require(inventory(output)==meta["files"],"RESTORE_CHANGED")
    marker.unlink()
    return {"restored":True,"fresh_media_audit":True,"motion_sha256":motion_pin,
            "packet_file_sha256":packet_pin,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("backup","verify","restore"):
        a=sub.add_parser(mode)
        a.add_argument("--snapshot",type=Path,required=True)
        a.add_argument("--packet-file-sha256",required=True)
        if mode!="backup":a.add_argument("--snapshot-sha256",required=True)
        if mode=="verify":a.add_argument("--motion-sha256",required=True)
        else:
            # Restore needs no old motion directory; add only original input paths.
            for name in ("pair","font","visual-request","native","request"):
                a.add_argument("--"+name,type=Path,required=True)
                a.add_argument("--"+name+"-sha256",required=True)
            a.add_argument("--motion-sha256",required=True)
            if mode=="backup":
                a.add_argument("--motion",type=Path,required=True)
                a.add_argument("--handoff",type=Path,required=True)
            else:a.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.mode=="verify":
            inspect(a.snapshot,a.snapshot_sha256,a.motion_sha256,a.packet_file_sha256)
            result={"snapshot_integrity_passed":True,"fresh_media_audit":False,"publication_eligible":False}
        else:
            inputs=review.get_inputs(a)
            result=(backup(inputs,a.motion,a.motion_sha256,a.handoff,a.packet_file_sha256,a.snapshot)
                    if a.mode=="backup" else restore(inputs,a.snapshot,a.snapshot_sha256,a.motion_sha256,
                    a.packet_file_sha256,a.output))
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,sqlite3.Error,wave.Error,
            subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
