"""Explicit stopped-run two-queue review transaction with resumable reconciliation.

Not cross-database atomic. Original request and immutable plan pins are required.
No reviewer text stored in the plan. Never grants publication authority.
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from app import domain_review_queue as queue
from app.domain_draft_review import evaluate
from tools import bilingual_review_preflight as pre, bilingual_review_dashboard as dash
from tools import pilot_run_verify as pv, pilot_snapshot as ps, bilingual_pilot as bp
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file

SCHEMA="VIRALOS_BILINGUAL_REVIEW_TRANSACTION_V1"
MAX_PLAN=32000
LANGS=dash.LANGS
STATES={"DEMO_BLOCKED","SELF_ATTESTED","NEEDS_REVISION","INCOMPLETE"}


def history(run,pin):
    path=run/"reviews.sqlite"
    with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True,timeout=2)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        rows=db.execute("SELECT revision,review_sha256,state,blocker_count FROM submissions "
                        "WHERE manifest_sha256=? ORDER BY revision LIMIT 100001",(pin,)).fetchall()
    pv.require(len(rows)<=100000,"HISTORY_SIZE")
    return [list(row) for row in rows]


def proposal(result):
    blockers=result["blockers"]
    state=("DEMO_BLOCKED" if result["synthetic_demo"] else
           "SELF_ATTESTED" if result["self_attested_editorial_checklist_complete"] else
           "NEEDS_REVISION" if any(x["reason"]=="REVISE" for x in blockers) else "INCOMPLETE")
    return {"review_sha256":pv.pin(result["review_sha256"]),"proposed_state":state,
            "blocker_count":len(blockers)}


def validate_plan(raw,plan_pin,request_pin,pair_pin,native_pin,*,schema=SCHEMA,binding="pair_sha256"):
    obj=pv.decode(pinned(raw,plan_pin,MAX_PLAN))
    pv.require(type(obj) is dict and set(obj)=={"schema","request_sha256",binding,
               "native_sha256","languages","publication_eligible"},"PLAN_FIELDS")
    pv.require(obj["schema"]==schema and obj["request_sha256"]==request_pin
               and obj[binding]==pair_pin and obj["native_sha256"]==native_pin
               and obj["publication_eligible"] is False,"PLAN_BINDING")
    pv.require(type(obj["languages"]) is dict and set(obj["languages"])==set(LANGS),"PLAN_LANGUAGES")
    for row in obj["languages"].values():
        pv.require(type(row) is dict and set(row)=={"manifest_sha256","expected_revision",
                   "review_sha256","proposed_state","blocker_count","history_sha256"},"PLAN_ROW")
        for name in ("manifest_sha256","review_sha256","history_sha256"):pv.pin(row[name])
        pv.require(pv.exact_int(row["expected_revision"],0,99999)
                   and pv.exact_int(row["blocker_count"],0,10000)
                   and row["proposed_state"] in STATES,"PLAN_VALUES")
    return obj


def prepare(pair,pair_pin,request,request_pin,native=None,native_pin=None):
    reviews=pre.validate(request,request_pin,pair_pin,native_pin)
    selector=lambda:dash.select_runs(pair,pair_pin,native,native_pin)
    return prepare_selected(selector,reviews,request_pin,{"schema":SCHEMA,"pair_sha256":pair_pin,"native_sha256":native_pin})


def prepare_selected(selector,reviews,request_pin,identity):
    result=pre.preflight_selected(selector,reviews,request_pin)
    runs,duration=selector()
    rows={}
    for lang in LANGS:
        row=result["languages"][lang]
        run,pin,_=runs[lang]
        hist=history(run,pin)
        pv.require(len(hist)==row["expected_revision"] and
                   all(x[1]!=row["review_sha256"] for x in hist),"HISTORY_CHANGED")
        rows[lang]={**row,"history_sha256":pv.canonical(hist)}
    obj={**identity,"request_sha256":request_pin,"languages":rows,"publication_eligible":False}
    reconcile_selected(selector,reviews,obj)
    return bp.json_bytes(obj)


def classify(hist,current_revision,current_state,row):
    rev=row["expected_revision"]
    pv.require(current_revision==len(hist),"REVISION_HISTORY")
    pv.require(len(hist) in (rev,rev+1),"REVISION_CONFLICT")
    pv.require(pv.canonical(hist[:rev])==row["history_sha256"],"HISTORY_PREFIX")
    pv.require(all(x[1]!=row["review_sha256"] for x in hist[:rev]),"DUPLICATE_REVIEW")
    if len(hist)==rev:
        return "PENDING"
    expected=[rev+1,row["review_sha256"],row["proposed_state"],row["blocker_count"]]
    pv.require(hist[-1]==expected and current_state==row["proposed_state"],"COMMIT_CONFLICT")
    return "RECORDED"


def reconcile(pair,pair_pin,request,request_pin,plan,plan_pin,native=None,native_pin=None):
    reviews=pre.validate(request,request_pin,pair_pin,native_pin)
    obj=validate_plan(plan,plan_pin,request_pin,pair_pin,native_pin)
    return reconcile_selected(lambda:dash.select_runs(pair,pair_pin,native,native_pin),reviews,obj)


def reconcile_selected(selector,reviews,obj):
    runs,duration=selector()
    before=dash.snapshot(runs,duration,fresh=True)
    statuses={}
    for lang in LANGS:
        run,pin,_=runs[lang]
        row=obj["languages"][lang]
        envelope=reviews[lang]
        pv.require(pin==row["manifest_sha256"] and envelope["revision"]==row["expected_revision"],
                   "PLAN_REVIEW_BINDING")
        result=evaluate(run/"draft",run/"assets",pin,envelope["review"])
        pv.require(proposal(result)=={k:row[k] for k in ("review_sha256","proposed_state","blocker_count")},
                   "PROPOSAL_CHANGED")
        current=before["languages"][lang]
        statuses[lang]=classify(history(run,pin),current["revision"],current["state"],row)
    pv.require(selector()==(runs,duration)
               and dash.snapshot(runs,duration)=={**before,"fresh_media_audit":False},"STATE_CHANGED")
    # A legal interruption can only occur after Hindi, before English.
    pv.require(not(statuses["hindi"]=="PENDING" and statuses["english"]=="RECORDED"),"ORDER_CONFLICT")
    return statuses


def apply(pair,pair_pin,request,request_pin,plan,plan_pin,native=None,native_pin=None):
    reviews=pre.validate(request,request_pin,pair_pin,native_pin)
    obj=validate_plan(plan,plan_pin,request_pin,pair_pin,native_pin)
    return apply_selected(lambda:dash.select_runs(pair,pair_pin,native,native_pin),reviews,obj,plan_pin)


def apply_selected(selector,reviews,obj,plan_pin):
    for lang in LANGS:
        statuses=reconcile_selected(selector,reviews,obj)
        if statuses[lang]=="RECORDED":
            continue
        runs,_=selector()
        run,pin,_=runs[lang]
        row=reviews[lang]
        pv.require(pin==obj["languages"][lang]["manifest_sha256"],"PLAN_REVIEW_BINDING")
        queue.submit(run/"reviews.sqlite",run/"draft",run/"assets",pin,row["revision"],row["review"])
    statuses=reconcile_selected(selector,reviews,obj)
    pv.require(all(x=="RECORDED" for x in statuses.values()),"PARTIAL_TRANSACTION")
    return {"transaction_sha256":plan_pin,"languages":statuses,"completed":True,
            "cross_database_atomic":False,"human_review_verified":False,"publication_eligible":False}


def plan_path(path,pair,native):
    path=Path(path).absolute()
    parent=ps.local_dir(path.parent)
    target=parent/path.name
    pv.require(path.suffix==".json","PLAN_EXTENSION")
    for root in (pair,native):
        if root is not None:
            pv.require(not target.is_relative_to(ps.local_dir(root)),"PLAN_INSIDE_RUN")
    return target


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("prepare","status","apply"):
        a=sub.add_parser(mode)
        for name in ("pair","request","plan"):a.add_argument("--"+name,type=Path,required=True)
        a.add_argument("--pair-sha256",required=True)
        a.add_argument("--request-sha256",required=True)
        a.add_argument("--native",type=Path)
        a.add_argument("--native-sha256")
        if mode!="prepare":a.add_argument("--plan-sha256",required=True)
        if mode=="apply":a.add_argument("--confirm-independent-writes",action="store_true",required=True)
    a=p.parse_args()
    try:
        target=plan_path(a.plan,a.pair,a.native)
        req=private_file(a.request,pre.MAX_REQUEST)
        common=(a.pair,a.pair_sha256,req,a.request_sha256)
        if a.mode=="prepare":
            raw=prepare(*common,a.native,a.native_sha256)
            with target.open("xb") as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            result={"transaction_sha256":sha(raw),"queues_modified":False,"publication_eligible":False}
        else:
            args=(*common,private_file(target,MAX_PLAN),a.plan_sha256,a.native,a.native_sha256)
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
