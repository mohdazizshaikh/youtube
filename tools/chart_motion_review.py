"""Paired chart-motion editorial handoff; immutable, independent language reviews.

No queue mutation, no inherited static approval, no publication authority.
Full original-input and motion-media verification before every operation.
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import subprocess
import wave
from pathlib import Path
from fontTools.ttLib import TTLibError
from tools import chart_pair_motion as cm, motion_review as mr
from tools import pilot_run_verify as pv, pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file
from tools.bilingual_pilot import json_bytes

PACKET="VIRALOS_CHART_MOTION_REVIEW_PACKET_V1"
REVIEW="VIRALOS_CHART_MOTION_REVIEW_V1"
RESULT="VIRALOS_CHART_MOTION_REVIEW_RESULT_V1"
HANDOFF="VIRALOS_CHART_MOTION_HANDOFF_V1"
PAIR_RESULT="VIRALOS_CHART_MOTION_PAIR_REVIEW_RESULT_V1"
LANGS=cm.LANGS
CHECKS=("source_accuracy","source_transcription","numeric_values","axis_and_units",
        "translation_accuracy","narration_accuracy","caption_accuracy","asset_rights",
        "originality","typography","highlight_order","visual_readability","motion_timing")


def packets_from(obj,motion_pin,chart_pin,parents):
    pv.pin(motion_pin)
    pv.pin(chart_pin)
    pv.require(type(obj) is dict and obj.get("schema")==cm.SCHEMA
               and obj.get("chart_pair_sha256")==chart_pin
               and obj.get("effect")=="VALUE_ROW_HIGHLIGHT_V1"
               and obj.get("fps")==25 and type(obj.get("fps")) is int
               and obj.get("timing_method")=="EQUAL_STAGE_NOT_WORD_ALIGNED"
               and obj.get("human_visual_review_required") is True
               and all(obj.get(k) is False for k in ("editorial_queue_created","publication_eligible",
                    "source_transcription_verified","word_alignment_verified")),"MOTION_BINDING")
    pv.require(type(obj["tracks"]) is dict and set(obj["tracks"])==set(LANGS)
               and type(parents) is dict and set(parents)==set(LANGS),"LANGUAGES")
    packets={}
    stages={}
    for lang in LANGS:
        track=obj["tracks"][lang]
        pv.require(type(track) is dict and set(track)=={"parent_manifest_sha256","parent_video_sha256",
            "motion_video_sha256","caption_sha256","duration_ms","stages","audit"},"TRACK_FIELDS")
        pv.require(track["duration_ms"]==obj["duration_ms"] and
                   pv.exact_int(track["duration_ms"],1200,60000) and track["duration_ms"]%40==0,
                   "TRACK_DURATION")
        audit=track["audit"]
        pv.require(audit.get("decoded_parent_audio_equal") is True
                   and audit.get("comparison_resolution")==[96,96]
                   and audit.get("full_resolution_pixels_verified") is False
                   and type(audit.get("frames_compared")) is int
                   and audit["frames_compared"]==track["duration_ms"]//40,"TRACK_AUDIT")
        p=mr.packet_track(track,motion_pin,parents[lang],stage_counts=(3,4,5),
                          checks=CHECKS,packet_schema=PACKET)
        p.update(language=lang,chart_pair_sha256=chart_pin,source_transcription_verified=False)
        # Preserve original evidence, including the chart declaration from the
        # static pilot; stage order is data-row order, not claimed speech timing.
        for row in p["scenes"]:
            evidence=row["source_declaration"]["specialist_facts"]
            declaration=pv.decode(evidence[cm.cp.KEY].encode())
            pv.require(declaration.get("language")==lang and declaration.get("scene")==row["scene"]
                       and declaration.get("source_transcription_verified") is False,
                       "CHART_EVIDENCE")
        stages[lang]=[[(s["start_ms"],s["end_ms"]) for s in row["stages"]] for row in p["scenes"]]
        packets[lang]=p
    pv.require(stages["hindi"]==stages["english"] and
               packets["hindi"]["synthetic_demo"]==packets["english"]["synthetic_demo"],
               "BILINGUAL_TIMING")
    pv.require(packets["hindi"]["parent_manifest_sha256"]!=packets["english"]["parent_manifest_sha256"],
               "DUPLICATE_PARENT")
    return packets


def packets(inputs,chart_pair,chart_pin,request,request_pin,candidate,motion_pin):
    checked=cm.verify(inputs,chart_pair,chart_pin,request,request_pin,candidate,motion_pin)
    pv.require(checked["fresh_media_audit"] is True and checked["publication_eligible"] is False,
               "MOTION_AUDIT")
    root=ps.local_dir(candidate)
    obj=pv.decode(pinned(pv.read(root/"motion_pair.json",pv.MAX_JSON),motion_pin,pv.MAX_JSON))
    parent=ps.local_dir(chart_pair)
    parents={l:pv.document(parent/l/"review_packet.json") for l in LANGS}
    return packets_from(obj,motion_pin,chart_pin,parents)


def template(packet):
    return mr.template(packet,checks=CHECKS,review_schema=REVIEW)


def payload(packets):
    files={}
    records={}
    for lang in LANGS:
        p=packets[lang]
        raw=json_bytes(p)
        tmp=json_bytes(template(p))
        pv.require(len(raw)<=pv.MAX_JSON and len(tmp)<=mr.MAX_REVIEW,"HANDOFF_SIZE")
        files[lang+"_packet.json"]=raw
        files[lang+"_review_template.json"]=tmp
        records[lang]={"packet_file_sha256":sha(raw),"packet_sha256":pv.canonical(p),
                       "template_sha256":sha(tmp)}
    meta={"schema":HANDOFF,"motion_pair_sha256":packets["hindi"]["motion_sha256"],
          "chart_pair_sha256":packets["hindi"]["chart_pair_sha256"],"languages":records,
          "publication_eligible":False}
    files["handoff.json"]=json_bytes(meta)
    return files,meta


def prepare(args,output):
    p=packets(*args)
    files,meta=payload(p)
    output=ps.new_dir(output,ps.local_dir(args[5]))
    for root in (args[0][0],args[0][2],args[1]):ps.new_dir(output,ps.local_dir(root))
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    for name,raw in files.items():mr.write_file(output/name,raw)
    marker.unlink()
    return {"handoff_sha256":sha(files["handoff.json"]),"languages":meta["languages"],
            "publication_eligible":False}


def verify(args,handoff,handoff_pin):
    root=ps.local_dir(handoff)
    pv.require({x.name for x in root.iterdir()}==
               {"handoff.json"}|{l+s for l in LANGS for s in ("_packet.json","_review_template.json")},
               "HANDOFF_INVENTORY")
    pinned(pv.read(root/"handoff.json",pv.MAX_JSON),handoff_pin,pv.MAX_JSON)
    p=packets(*args)
    files,_=payload(p)
    for name,raw in files.items():
        pv.require(pv.read(root/name,len(raw))==raw,"HANDOFF_BYTES")
    return p


def evaluate_packets(p,reviews,review_pins,handoff_pin):
    pv.pin(handoff_pin)
    pv.require(type(reviews) is dict and set(reviews)==set(LANGS)
               and type(review_pins) is dict and set(review_pins)==set(LANGS),"REVIEW_LANGUAGES")
    rows={}
    for lang in LANGS:
        result=mr.evaluate_packet(p[lang],reviews[lang],review_pins[lang],
                                  required_checks=CHECKS,review_schema=REVIEW,result_schema=RESULT)
        rows[lang]={**result,"language":lang}
    return {"schema":PAIR_RESULT,"handoff_sha256":handoff_pin,
            "motion_pair_sha256":p["hindi"]["motion_sha256"],"languages":rows,
            "both_self_attested_checklists_complete":all(x["self_attested_checklist_complete"] for x in rows.values()),
            "source_transcription_verified":False,"translation_verified":False,
            "human_review_verified":False,"publication_eligible":False}


def evaluate(args,handoff,handoff_pin,reviews,review_pins):
    return evaluate_packets(verify(args,handoff,handoff_pin),reviews,review_pins,handoff_pin)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("prepare","verify","evaluate"):
        a=sub.add_parser(mode)
        for name in ("pair","root","chart-request","hindi-font","english-font",
                     "chart-pair","request","motion","handoff"):
            a.add_argument("--"+name,type=Path,required=True)
        for name in ("pair","chart-request","hindi-font","english-font","chart-pair","request","motion"):
            a.add_argument("--"+name+"-sha256",required=True)
        if mode!="prepare":a.add_argument("--handoff-sha256",required=True)
        if mode=="evaluate":
            for lang in LANGS:
                a.add_argument("--"+lang+"-review",type=Path,required=True)
                a.add_argument("--"+lang+"-review-sha256",required=True)
            a.add_argument("--result",type=Path,required=True)
    a=p.parse_args()
    try:
        inputs=(a.pair,a.pair_sha256,a.root,private_file(a.chart_request,cm.cp.MAX_REQUEST),
                a.chart_request_sha256,
                {l:private_file(getattr(a,l+"_font"),cm.cp.chart.ht.MAX_FONT) for l in LANGS},
                {l:getattr(a,l+"_font_sha256") for l in LANGS})
        args=(inputs,a.chart_pair,a.chart_pair_sha256,private_file(a.request,cm.MAX_REQUEST),
              a.request_sha256,a.motion,a.motion_sha256)
        if a.mode=="prepare":result=prepare(args,a.handoff)
        elif a.mode=="verify":
            verify(args,a.handoff,a.handoff_sha256)
            result={"fresh_media_audit":True,"handoff_sha256":a.handoff_sha256,"publication_eligible":False}
        else:
            result=evaluate(args,a.handoff,a.handoff_sha256,
                     {l:private_file(getattr(a,l+"_review"),mr.MAX_REVIEW) for l in LANGS},
                     {l:getattr(a,l+"_review_sha256") for l in LANGS})
            target=ps.local_dir(a.result.absolute().parent)/a.result.name
            pv.require(target.suffix==".json","RESULT_EXTENSION")
            for root in (a.pair,a.root,a.chart_pair,a.motion,a.handoff):
                pv.require(not target.is_relative_to(ps.local_dir(root)),"RESULT_INSIDE_INPUT")
            raw=json_bytes(result)
            mr.write_file(target,raw)
            result={**result,"result_file_sha256":sha(raw)}
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,sqlite3.Error,
            subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
