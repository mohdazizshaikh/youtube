"""Read-only chart-pair editorial comparison; original chart recomposition is separate."""
from __future__ import annotations
import argparse
import re
from pathlib import Path
import uvicorn
from tools import bilingual_chart_pilot as cp, bilingual_review_dashboard as dash
from tools import pilot_run_verify as pv, pilot_snapshot as ps
from tools.narration_prepare import pinned

LANGS=cp.LANGS


def records(raw,pair_pin):
    obj=pv.decode(pinned(raw,pair_pin,cp.MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","pair_sha256","request_sha256",
        "duration_ms","scenes","runs","visual_mode","caption_timing","source_transcription_verified",
        "translation_verified","human_review_verified","publication_eligible"}
        and obj["schema"]==cp.SCHEMA and obj["visual_mode"]=="BILINGUAL_SOURCE_BOUND_CHARTS"
        and obj["caption_timing"]=="SCENE_LEVEL_ONLY"
        and all(obj[k] is False for k in ("source_transcription_verified","translation_verified",
                                           "human_review_verified","publication_eligible")),"CHART_RECEIPT")
    pv.pin(obj["pair_sha256"])
    pv.pin(obj["request_sha256"])
    pv.require(pv.exact_int(obj["duration_ms"],40,120000) and obj["duration_ms"]%40==0,"DURATION")
    rows=obj["scenes"]
    pv.require(type(rows) is list and 2<=len(rows)<=8,"SCENES")
    for i,row in enumerate(rows,1):
        pv.require(type(row) is dict and set(row)=={"scene","source_id","source_sha256","data_sha256",
            "chart_request_sha256","chart_sha256"} and type(row["scene"]) is int and row["scene"]==i
            and type(row["source_id"]) is str and re.fullmatch(r"[A-Z][A-Z0-9]{0,7}",row["source_id"]),
            "SCENE_FIELDS")
        for k in ("source_sha256","data_sha256","chart_request_sha256","chart_sha256"):pv.pin(row[k])
    runs=obj["runs"]
    pv.require(type(runs) is dict and set(runs)==set(LANGS),"RUNS")
    for row in runs.values():
        pv.require(type(row) is dict and set(row)=={"manifest_sha256","video_sha256","duration_ms"}
                   and type(row["duration_ms"]) is int and row["duration_ms"]==obj["duration_ms"],"RUN_FIELDS")
        pv.pin(row["manifest_sha256"])
        pv.pin(row["video_sha256"])
    pv.require(runs["hindi"]["manifest_sha256"]!=runs["english"]["manifest_sha256"],"DUPLICATE_RUN")
    return obj


def scene_binding(packet,record,obj,lang):
    facts=packet["specialist_facts"]
    declaration=pv.decode(facts[cp.KEY].encode())
    pv.require(type(declaration) is dict and set(declaration)=={"schema","scene","language",
            "parent_board_sha256","source_id","source_sha256","data_sha256","chart_request_sha256",
            "chart_receipt_sha256","png_sha256","pair_sha256","pilot_request_sha256",
            "source_transcription_verified"} and declaration["schema"]=="VIRALOS_CHART_SCENE_DECLARATION_V1"
            and type(declaration["scene"]) is int and declaration["scene"]==record["scene"]==packet["scene"]
            and declaration["language"]==lang and declaration["pair_sha256"]==obj["pair_sha256"]
            and declaration["pilot_request_sha256"]==obj["request_sha256"]
            and declaration["chart_receipt_sha256"]==record["chart_sha256"]
            and declaration["png_sha256"]==packet["board_sha256"]
            and declaration["source_transcription_verified"] is False
            and all(declaration[k]==record[k] for k in ("source_id","source_sha256","data_sha256","chart_request_sha256")),
            "CHART_DECLARATION")
    pv.pin(declaration["parent_board_sha256"])
    pv.pin(declaration["png_sha256"])
    pv.require(any(s["source_id"]==record["source_id"] for s in packet["sources"]) and
               any(l["source_id"]==record["source_id"] and l["relation"]=="SUPPORTS"
                   for c in packet["claims"] for l in c["links"]),"SOURCE_DECLARATION")


def select_runs(root,pair_pin):
    root=ps.local_dir(root)
    pv.require({p.name for p in root.iterdir()}==set(LANGS)|{"chart_pair.json"},"CHART_PAIR_INVENTORY")
    obj=records(pv.read(root/"chart_pair.json",cp.MAX_REQUEST),pair_pin)
    runs={}
    for lang in LANGS:
        run=ps.local_dir(root/lang)
        row=obj["runs"][lang]
        packet=pv.document(run/"review_packet.json")
        pv.require(packet["manifest_sha256"]==row["manifest_sha256"] and
                   packet["video_sha256"]==row["video_sha256"] and
                   type(packet["scenes"]) is list and len(packet["scenes"])==len(obj["scenes"]),"PACKET_BINDING")
        for scene,record in zip(packet["scenes"],obj["scenes"]):scene_binding(scene,record,obj,lang)
        runs[lang]=(run,row["manifest_sha256"],row["video_sha256"])
    return runs,obj["duration_ms"]


def create_app(root,pair_pin):
    return dash.create_selected_app(lambda:select_runs(root,pair_pin),chart=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chart-pair",type=Path,required=True)
    p.add_argument("--chart-pair-sha256",required=True)
    p.add_argument("--port",type=int,default=8768)
    a=p.parse_args()
    if not 1024<=a.port<=65535:p.error("port must be between 1024 and 65535")
    uvicorn.run(create_app(a.chart_pair,a.chart_pair_sha256),host="127.0.0.1",
                port=a.port,access_log=False,proxy_headers=False)


if __name__=="__main__":
    main()
