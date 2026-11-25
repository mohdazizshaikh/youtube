"""Read-only loopback review of independently pinned paired mixed candidates.

Fresh child media audits at startup. Run paired_production_mix verify separately
with original parents/music/request for full deterministic recomposition.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import uvicorn
from tools import bilingual_review_dashboard as dash, paired_mix_snapshot as snap
from tools import pilot_run_verify as pv, pilot_snapshot as ps


def select_runs(mixed,pair_mix_pin):
    root=ps.local_dir(mixed)
    pv.require({p.name for p in root.iterdir()}==set(snap.LANGS)|{"pair_mix.json"},"MIXED_INVENTORY")
    obj=snap.pair_records(pv.read(root/"pair_mix.json",snap.MAX_JSON),pair_mix_pin)
    runs={}
    for lang in snap.LANGS:
        child=ps.local_dir(root/lang)
        pv.require({p.name for p in child.iterdir()}=={"run","mix.json"},"CHILD_INVENTORY")
        row=obj["tracks"][lang]
        receipt=snap.track_record(pv.read(child/"mix.json",snap.pm.pm.MAX_REQUEST),row)
        pv.require(receipt.get("human_listening_required") is True
                   and receipt.get("speech_intelligibility_verified") is False
                   and receipt.get("human_review_verified") is False
                   and receipt.get("visual_bytes_preserved") is True
                   and receipt.get("mode") in ("STATIC","DUCK"),"MIX_RECEIPT_FLAGS")
        for key in ("parent_manifest_sha256","request_sha256","mixed_master_sha256"):
            pv.pin(receipt[key])
        run=ps.local_dir(child/"run")
        packet=pv.document(run/"review_packet.json")
        pv.require(type(packet["scenes"]) is list and 2<=len(packet["scenes"])<=8,"SCENE_COUNT")
        for scene in packet["scenes"]:
            facts=scene["specialist_facts"]
            pv.require(facts.get("production_mix_audio_kind")=="MIXED_VOICE_AND_MUSIC"
                       and facts.get("production_mix_parent_manifest_sha256")==receipt["parent_manifest_sha256"]
                       and facts.get("production_mix_request_sha256")==receipt["request_sha256"]
                       and facts.get("production_mix_master_sha256")==receipt["mixed_master_sha256"]
                       and facts.get("production_mix_mode")==receipt["mode"],"MIX_DECLARATION")
        runs[lang]=(run,row["manifest_sha256"],row["video_sha256"])
    return runs,obj["duration_ms"]


def create_app(mixed,pair_mix_pin):
    return dash.create_selected_app(lambda:select_runs(mixed,pair_mix_pin),mixed=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mixed",type=Path,required=True)
    p.add_argument("--pair-mix-sha256",required=True)
    p.add_argument("--port",type=int,default=8767)
    a=p.parse_args()
    if not 1024<=a.port<=65535:p.error("port must be between 1024 and 65535")
    app=create_app(a.mixed,a.pair_mix_sha256)
    uvicorn.run(app,host="127.0.0.1",port=a.port,access_log=False,proxy_headers=False)


if __name__=="__main__":
    main()
