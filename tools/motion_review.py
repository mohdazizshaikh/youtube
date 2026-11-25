"""Separate immutable motion editorial handoff. No inherited approval or publishing."""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import subprocess
import unicodedata
import wave
from pathlib import Path

from fontTools.ttLib import TTLibError
from tools import native_flow_motion as motion, pilot_run_verify as pv, pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file
from tools.bilingual_pilot import json_bytes

PACKET="VIRALOS_MOTION_REVIEW_PACKET_V1"
REVIEW="VIRALOS_MOTION_REVIEW_V1"
RESULT="VIRALOS_MOTION_REVIEW_RESULT_V1"
MAX_REVIEW=256000
CHECKS=("source_accuracy","narration_accuracy","caption_accuracy","asset_rights",
        "originality","native_typography","highlight_order","visual_readability","motion_timing")
VALUES=("PASS","REVISE","NOT_REVIEWED")


def packet_from(receipt,motion_pin,parent):
    pv.pin(motion_pin)
    pv.require(receipt["schema"]==motion.SCHEMA and receipt["publication_eligible"] is False
               and receipt["editorial_queue_created"] is False,"MOTION_RECEIPT")
    return packet_track(receipt,motion_pin,parent)


def packet_track(receipt,motion_pin,parent,*,stage_counts=(3,),checks=CHECKS,packet_schema=PACKET):
    pv.pin(motion_pin)
    pv.require(parent["manifest_sha256"]==receipt["parent_manifest_sha256"]
               and parent["video_sha256"]==receipt["parent_video_sha256"]
               and parent["publication_eligible"] is False,"PARENT_PACKET")
    rows=parent["scenes"]
    stages=receipt["stages"]
    pv.require(type(rows) is list and type(stages) is list and 2<=len(rows)==len(stages)<=8,"SCENE_COUNT")
    scenes=[]
    cursor=0
    for i,(row,parts) in enumerate(zip(rows,stages),1):
        pv.require(type(row["scene"]) is int and row["scene"]==i
                   and row["start_ms"]==cursor and type(row["end_ms"]) is int,"SCENE_ORDER")
        pv.require(type(parts) is list and len(parts) in stage_counts,"STAGES")
        sequence=[]
        for j,part in enumerate(parts,1):
            pv.require(type(part) is dict and set(part)=={"frames","png_sha256"}
                       and pv.exact_int(part["frames"],5,250),"STAGE")
            end=cursor+part["frames"]*40
            sequence.append({"step":j,"start_ms":cursor,"end_ms":end,
                             "png_sha256":pv.pin(part["png_sha256"])})
            cursor=end
        pv.require(cursor==row["end_ms"],"STAGE_TIMING")
        entry={"scene":i,"parent_scene_sha256":pv.pin(row["scene_sha256"]),
               "source_declaration":row,"stages":sequence}
        entry["scene_sha256"]=pv.canonical(entry)
        scenes.append(entry)
    pv.require(cursor==receipt["duration_ms"] and type(parent["synthetic_demo"]) is bool,
               "MOTION_DURATION")
    return {"schema":packet_schema,"motion_sha256":motion_pin,
            "video_sha256":pv.pin(receipt["motion_video_sha256"]),
            "caption_sha256":pv.pin(receipt["caption_sha256"]),
            "parent_manifest_sha256":receipt["parent_manifest_sha256"],
            "duration_ms":cursor,"synthetic_demo":parent["synthetic_demo"],
            "scenes":scenes,"checks":list(checks),"timing_method":"EQUAL_STAGE_NOT_WORD_ALIGNED",
            "human_review_verified":False,"publication_eligible":False}


def packet(inputs,candidate,motion_pin):
    candidate=ps.local_dir(candidate)
    motion.verify(inputs,candidate,motion_pin)
    receipt=pv.decode(pinned(pv.read(candidate/"motion.json",pv.MAX_JSON),motion_pin,pv.MAX_JSON))
    parent=pv.document(ps.local_dir(inputs[6])/"hindi"/"review_packet.json")
    return packet_from(receipt,motion_pin,parent)


def template(obj,*,checks=CHECKS,review_schema=REVIEW):
    return {"schema":review_schema,"motion_sha256":obj["motion_sha256"],
            "packet_sha256":pv.canonical(obj),"reviewer":"","scenes":[
                {"scene":r["scene"],"scene_sha256":r["scene_sha256"],
                 "checks":dict.fromkeys(checks,"NOT_REVIEWED"),"notes":""} for r in obj["scenes"]]}


def clean_text(value,limit):
    return type(value) is str and len(value)<=limit and all(
        unicodedata.category(c)[0]!="C" or c in "\n\t\u200c\u200d" for c in value)


def evaluate_packet(obj,raw,review_pin,*,required_checks=CHECKS,review_schema=REVIEW,result_schema=RESULT):
    r=pv.decode(pinned(raw,review_pin,MAX_REVIEW))
    pv.require(type(r) is dict and set(r)=={"schema","motion_sha256","packet_sha256","reviewer","scenes"}
               and r["schema"]==review_schema and r["motion_sha256"]==obj["motion_sha256"]
               and r["packet_sha256"]==pv.canonical(obj),"REVIEW_BINDING")
    pv.require(clean_text(r["reviewer"],120),"REVIEWER")
    rows=r["scenes"]
    expected=obj["scenes"]
    pv.require(type(rows) is list and len(rows)==len(expected),"REVIEW_COVERAGE")
    blockers=[]
    for actual,scene in zip(rows,expected):
        pv.require(type(actual) is dict and set(actual)=={"scene","scene_sha256","checks","notes"}
                   and type(actual["scene"]) is int and actual["scene"]==scene["scene"]
                   and actual["scene_sha256"]==scene["scene_sha256"],"REVIEW_SCENE")
        checks=actual["checks"]
        pv.require(type(checks) is dict and set(checks)==set(required_checks)
                   and all(v in VALUES for v in checks.values()),"REVIEW_CHECKS")
        pv.require(clean_text(actual["notes"],2000),"REVIEW_NOTES")
        pv.require("REVISE" not in checks.values() or bool(actual["notes"].strip()),"REVISION_NOTE")
        blockers.extend({"scene":scene["scene"],"check":k,"reason":checks[k]}
                        for k in required_checks if checks[k]!="PASS")
    if not r["reviewer"].strip():blockers.append({"reason":"REVIEWER_DECLARATION_MISSING"})
    if obj["synthetic_demo"]:blockers.append({"reason":"SYNTHETIC_DEMO_NOT_ELIGIBLE"})
    return {"schema":result_schema,"motion_sha256":obj["motion_sha256"],
            "packet_sha256":r["packet_sha256"],"review_sha256":review_pin,
            "video_sha256":obj["video_sha256"],"blockers":blockers,
            "self_attested_checklist_complete":not blockers,"reviewer_identity_verified":False,
            "human_review_verified":False,"word_alignment_verified":False,
            "publication_eligible":False}


def evaluate(inputs,candidate,motion_pin,raw,review_pin):
    return evaluate_packet(packet(inputs,candidate,motion_pin),raw,review_pin)


def write_file(path,raw):
    with path.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    pv.require(pv.read(path,len(raw))==raw,"WRITE_BYTES")


def prepare(inputs,candidate,motion_pin,output):
    obj=packet(inputs,candidate,motion_pin)
    output=ps.new_dir(output,ps.local_dir(candidate))
    for path in (inputs[0],inputs[6]):ps.new_dir(output,ps.local_dir(path))
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    raw=json_bytes(obj)
    write_file(output/"packet.json",raw)
    write_file(output/"review_template.json",json_bytes(template(obj)))
    marker.unlink()
    return {"packet_file_sha256":sha(raw),"packet_sha256":pv.canonical(obj),
            "publication_eligible":False}


def verify_handoff(inputs,candidate,motion_pin,handoff,packet_file_pin):
    handoff=ps.local_dir(handoff)
    pv.require({x.name for x in handoff.iterdir()}=={"packet.json","review_template.json"},"HANDOFF_INVENTORY")
    obj=packet(inputs,candidate,motion_pin)
    raw=pinned(pv.read(handoff/"packet.json",pv.MAX_JSON),packet_file_pin,pv.MAX_JSON)
    pv.require(raw==json_bytes(obj),"HANDOFF_PACKET")
    pv.require(pv.read(handoff/"review_template.json",MAX_REVIEW)==json_bytes(template(obj)),"HANDOFF_TEMPLATE")
    return obj


def add_inputs(a):
    for name in ("pair","font","visual-request","native","request","motion"):
        a.add_argument("--"+name,type=Path,required=True)
        a.add_argument("--"+name+"-sha256",required=True)


def get_inputs(a):
    return (a.pair,a.pair_sha256,private_file(a.font,motion.nh.ht.MAX_FONT),a.font_sha256,
            private_file(a.visual_request,motion.nh.MAX_REQUEST),a.visual_request_sha256,
            a.native,a.native_sha256,private_file(a.request,motion.MAX_REQUEST),a.request_sha256)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("prepare","verify","evaluate"):
        a=sub.add_parser(mode)
        add_inputs(a)
        a.add_argument("--handoff",type=Path,required=True)
        if mode!="prepare":a.add_argument("--packet-file-sha256",required=True)
        if mode=="evaluate":
            a.add_argument("--review",type=Path,required=True)
            a.add_argument("--review-sha256",required=True)
            a.add_argument("--result",type=Path,required=True)
    a=p.parse_args()
    try:
        inputs=get_inputs(a)
        common=(inputs,a.motion,a.motion_sha256,a.handoff)
        if a.mode=="prepare":result=prepare(*common)
        else:
            obj=verify_handoff(*common,a.packet_file_sha256)
            if a.mode=="verify":
                result={"fresh_media_audit":True,"packet_sha256":pv.canonical(obj),"publication_eligible":False}
            else:
                result=evaluate_packet(obj,private_file(a.review,MAX_REVIEW),a.review_sha256)
                target=ps.local_dir(a.result.absolute().parent)/a.result.name
                pv.require(target.suffix==".json","RESULT_EXTENSION")
                for root in (a.pair,a.native,a.motion,a.handoff):
                    pv.require(not target.is_relative_to(ps.local_dir(root)),"RESULT_INSIDE_INPUT")
                raw=json_bytes(result)
                write_file(target,raw)
                result={**result,"result_file_sha256":sha(raw)}
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,sqlite3.Error,wave.Error,
            subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
