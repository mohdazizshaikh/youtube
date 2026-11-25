"""Explicit stopped mixed-pair review transactions, distinct from original-pair plans.

Separate queue writes only. Full paired remix verification is a separate prerequisite.
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
from pathlib import Path
from tools import mixed_review_dashboard as dash, bilingual_review_transaction as tx
from tools import bilingual_review_preflight as pre, pilot_run_verify as pv
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file

REQUEST="VIRALOS_MIXED_REVIEW_REQUEST_V1"
SCHEMA="VIRALOS_MIXED_REVIEW_TRANSACTION_V1"


def validate(raw,request_pin,mix_pin):
    pv.pin(mix_pin)
    obj=pv.decode(pinned(raw,request_pin,pre.MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","pair_mix_sha256","reviews"}
               and obj["schema"]==REQUEST and obj["pair_mix_sha256"]==mix_pin,"MIX_REQUEST_BINDING")
    return pre.validate_reviews(obj["reviews"])


def prepare(mixed,mix_pin,request,request_pin):
    reviews=validate(request,request_pin,mix_pin)
    return tx.prepare_selected(lambda:dash.select_runs(mixed,mix_pin),reviews,request_pin,
                 {"schema":SCHEMA,"pair_mix_sha256":mix_pin,"native_sha256":None})


def checked_plan(raw,plan_pin,request_pin,mix_pin):
    return tx.validate_plan(raw,plan_pin,request_pin,mix_pin,None,schema=SCHEMA,binding="pair_mix_sha256")


def reconcile(mixed,mix_pin,request,request_pin,plan,plan_pin):
    reviews=validate(request,request_pin,mix_pin)
    obj=checked_plan(plan,plan_pin,request_pin,mix_pin)
    return tx.reconcile_selected(lambda:dash.select_runs(mixed,mix_pin),reviews,obj)


def apply(mixed,mix_pin,request,request_pin,plan,plan_pin):
    reviews=validate(request,request_pin,mix_pin)
    obj=checked_plan(plan,plan_pin,request_pin,mix_pin)
    return tx.apply_selected(lambda:dash.select_runs(mixed,mix_pin),reviews,obj,plan_pin)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("prepare","status","apply"):
        a=sub.add_parser(mode)
        for name in ("mixed","request","plan"):a.add_argument("--"+name,type=Path,required=True)
        a.add_argument("--pair-mix-sha256",required=True)
        a.add_argument("--request-sha256",required=True)
        if mode!="prepare":a.add_argument("--plan-sha256",required=True)
        if mode=="apply":a.add_argument("--confirm-independent-writes",action="store_true",required=True)
    a=p.parse_args()
    try:
        path=tx.plan_path(a.plan,a.mixed,None)
        common=(a.mixed,a.pair_mix_sha256,private_file(a.request,pre.MAX_REQUEST),a.request_sha256)
        if a.mode=="prepare":
            raw=prepare(*common)
            with path.open("xb") as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            result={"transaction_sha256":sha(raw),"queues_modified":False,"publication_eligible":False}
        else:
            args=(*common,private_file(path,tx.MAX_PLAN),a.plan_sha256)
            result=apply(*args) if a.mode=="apply" else {"languages":reconcile(*args),
                     "queues_modified":False,"publication_eligible":False}
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,sqlite3.Error,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,
                          "check_transaction_status_before_retry":True,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
