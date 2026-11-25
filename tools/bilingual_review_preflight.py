"""Validate both independent review submissions without modifying either queue."""
from __future__ import annotations
import argparse
import json
import sqlite3
from pathlib import Path
from app.domain_draft_review import evaluate
from tools import bilingual_review_dashboard as dashboard, pilot_run_verify as pv
from tools.narration_prepare import pinned, sha
from tools.narration_qc import private_file

SCHEMA="VIRALOS_BILINGUAL_REVIEW_PREFLIGHT_REQUEST_V1"
MAX_REQUEST=256000


def validate(raw,request_pin,pair_pin,native_pin):
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","pair_sha256","native_sha256","reviews"}
               and obj["schema"]==SCHEMA and obj["pair_sha256"]==pair_pin
               and obj["native_sha256"]==native_pin,"REQUEST_BINDING")
    pv.require(type(obj["reviews"]) is dict and set(obj["reviews"])==set(dashboard.LANGS),"REVIEW_LANGUAGES")
    for row in obj["reviews"].values():
        pv.require(type(row) is dict and set(row)=={"revision","review"}
                   and type(row["revision"]) is int and 0<=row["revision"]<100000
                   and type(row["review"]) is dict,"REVIEW_ENVELOPE")
    return obj["reviews"]


def preflight(pair,pair_pin,request,request_pin,native=None,native_pin=None):
    reviews=validate(request,request_pin,pair_pin,native_pin)
    runs,duration=dashboard.select_runs(pair,pair_pin,native,native_pin)
    before=dashboard.snapshot(runs,duration,fresh=True)
    reports={}
    for lang in dashboard.LANGS:
        row=reviews[lang]
        run,pin,_=runs[lang]
        pv.require(row["revision"]==before["languages"][lang]["revision"],"STALE_REVISION")
        result=evaluate(run/"draft",run/"assets",pin,row["review"])
        review_pin=pv.pin(result["review_sha256"])
        # Read-only URI, never use queue.status which opens a writable connection.
        with sqlite3.connect((run/"reviews.sqlite").resolve().as_uri()+"?mode=ro",uri=True) as db:
            exists=db.execute("SELECT 1 FROM submissions WHERE manifest_sha256=? AND review_sha256=?",
                              (pin,review_pin)).fetchone()
        pv.require(exists is None,"REVIEW_ALREADY_RECORDED")
        blockers=result["blockers"]
        state=("DEMO_BLOCKED" if result["synthetic_demo"] else
               "SELF_ATTESTED" if result["self_attested_editorial_checklist_complete"] else
               "NEEDS_REVISION" if any(b["reason"]=="REVISE" for b in blockers) else "INCOMPLETE")
        reports[lang]={"manifest_sha256":pin,"expected_revision":row["revision"],
                       "review_sha256":review_pin,"proposed_state":state,"blocker_count":len(blockers)}
    pv.require(dashboard.select_runs(pair,pair_pin,native,native_pin)==(runs,duration)
               and dashboard.snapshot(runs,duration)=={**before,"fresh_media_audit":False},"REVIEW_CHANGED")
    return {"schema":"VIRALOS_BILINGUAL_REVIEW_PREFLIGHT_V1","request_sha256":request_pin,
            "languages":reports,"both_envelopes_valid":True,"queues_modified":False,
            "human_review_verified":False,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pair",type=Path,required=True)
    p.add_argument("--pair-sha256",required=True)
    p.add_argument("--native",type=Path)
    p.add_argument("--native-sha256")
    p.add_argument("--request",type=Path,required=True)
    p.add_argument("--request-sha256",required=True)
    a=p.parse_args()
    try:result=preflight(a.pair,a.pair_sha256,private_file(a.request,MAX_REQUEST),
                         a.request_sha256,a.native,a.native_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,sqlite3.Error,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
