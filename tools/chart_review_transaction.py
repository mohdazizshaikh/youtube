"""Source-verified chart review transaction; two independent stopped-run writes.

Original chart inputs and both independently trusted request/plan pins are
mandatory. No cross-database atomicity, hostile-writer or publication guarantee.
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import subprocess
import wave
from pathlib import Path
from fontTools.ttLib import TTLibError

from tools import bilingual_chart_pilot as cp, chart_review_dashboard as dash
from tools import bilingual_review_transaction as tx, bilingual_review_preflight as pre
from tools import pilot_run_verify as pv, pilot_snapshot as ps
from tools.narration_prepare import pinned, sha
from tools.narration_qc import private_file

REQUEST="VIRALOS_CHART_REVIEW_REQUEST_V1"
SCHEMA="VIRALOS_CHART_REVIEW_TRANSACTION_V1"


def validate(raw,request_pin,chart_pair_pin):
    pv.pin(chart_pair_pin)
    obj=pv.decode(pinned(raw,request_pin,pre.MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","chart_pair_sha256","reviews"}
               and obj["schema"]==REQUEST and obj["chart_pair_sha256"]==chart_pair_pin,
               "CHART_REVIEW_BINDING")
    return pre.validate_reviews(obj["reviews"])


def checked_plan(raw,plan_pin,request_pin,chart_pair_pin):
    return tx.validate_plan(raw,plan_pin,request_pin,chart_pair_pin,None,
                            schema=SCHEMA,binding="chart_pair_sha256")


def verified_selector(inputs,chart_pair,chart_pair_pin):
    """Bind original-input re-audit to the same child selection and queue state."""
    checked=cp.verify(inputs,chart_pair,chart_pair_pin)
    pv.require(checked["fresh_media_audit"] is True and checked["publication_eligible"] is False
               and checked["chart_pair_sha256"]==chart_pair_pin,"CHART_SOURCE_AUDIT")
    runs,duration=dash.select_runs(chart_pair,chart_pair_pin)
    pv.require(duration==checked["duration_ms"],"CHART_DURATION")
    current=dash.dash.snapshot(runs,duration)
    pv.require({lang:{"revision":row["revision"],"state":row["state"]}
                for lang,row in current["languages"].items()}==checked["review_states"],
               "CHART_QUEUE_CHANGED")
    # Only paths and immutable media pins are frozen. Reconciliation validates
    # queue history independently after each write.
    def select():
        selected=dash.select_runs(chart_pair,chart_pair_pin)
        pv.require(selected==(runs,duration),"CHART_SELECTION_CHANGED")
        return selected
    return select


def prepare(inputs,chart_pair,chart_pair_pin,request,request_pin):
    reviews=validate(request,request_pin,chart_pair_pin)
    selector=verified_selector(inputs,chart_pair,chart_pair_pin)
    return tx.prepare_selected(selector,reviews,request_pin,
             {"schema":SCHEMA,"chart_pair_sha256":chart_pair_pin,"native_sha256":None})


def reconcile(inputs,chart_pair,chart_pair_pin,request,request_pin,plan,plan_pin):
    reviews=validate(request,request_pin,chart_pair_pin)
    obj=checked_plan(plan,plan_pin,request_pin,chart_pair_pin)
    selector=verified_selector(inputs,chart_pair,chart_pair_pin)
    return tx.reconcile_selected(selector,reviews,obj)


def apply(inputs,chart_pair,chart_pair_pin,request,request_pin,plan,plan_pin):
    reviews=validate(request,request_pin,chart_pair_pin)
    obj=checked_plan(plan,plan_pin,request_pin,chart_pair_pin)
    selector=verified_selector(inputs,chart_pair,chart_pair_pin)
    # Calls are deliberately independent. If the second write fails, retry
    # with the exact same pinned plan; do not manufacture a new revision.
    return tx.apply_selected(selector,reviews,obj,plan_pin)


def plan_path(path,inputs,chart_pair):
    target=tx.plan_path(path,chart_pair,inputs[0])
    pv.require(not target.is_relative_to(ps.local_dir(inputs[2])),"PLAN_INSIDE_CHART_INPUT")
    return target


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("prepare","status","apply"):
        a=sub.add_parser(mode)
        for name in ("pair","root","chart-request","hindi-font","english-font",
                     "chart-pair","review-request","plan"):
            a.add_argument("--"+name,type=Path,required=True)
        for name in ("pair","chart-request","hindi-font","english-font","chart-pair","review-request"):
            a.add_argument("--"+name+"-sha256",required=True)
        if mode!="prepare":a.add_argument("--plan-sha256",required=True)
        if mode=="apply":a.add_argument("--confirm-independent-writes",action="store_true",required=True)
    a=p.parse_args()
    try:
        inputs=(a.pair,a.pair_sha256,a.root,private_file(a.chart_request,cp.MAX_REQUEST),
                a.chart_request_sha256,
                {l:private_file(getattr(a,l+"_font"),cp.chart.ht.MAX_FONT) for l in cp.LANGS},
                {l:getattr(a,l+"_font_sha256") for l in cp.LANGS})
        target=plan_path(a.plan,inputs,a.chart_pair)
        common=(inputs,a.chart_pair,a.chart_pair_sha256,
                private_file(a.review_request,pre.MAX_REQUEST),a.review_request_sha256)
        if a.mode=="prepare":
            raw=prepare(*common)
            with target.open("xb") as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            pv.require(pv.read(target,tx.MAX_PLAN)==raw,"PLAN_WRITE")
            result={"transaction_sha256":sha(raw),"queues_modified":False,
                    "original_chart_inputs_verified":True,"publication_eligible":False}
        else:
            args=(*common,private_file(target,tx.MAX_PLAN),a.plan_sha256)
            result=apply(*args) if a.mode=="apply" else {"languages":reconcile(*args),
                      "queues_modified":False,"publication_eligible":False}
            result={**result,"original_chart_inputs_verified":True}
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,sqlite3.Error,
            subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,
                          "check_transaction_status_before_retry":True,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
