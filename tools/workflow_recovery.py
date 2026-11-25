"""Explicit stopped-workspace recovery of an interrupted local workflow job.

No destructive rollback, blind retry, arbitrary commands, or publication.
An incomplete/missing write artifact is never finalized by this tool.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools import production_workflow as w
from tools import pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file
from tools.bilingual_pilot import json_bytes

SCHEMA="VIRALOS_LOCAL_WORKFLOW_RECOVERY_V1"
MAX_RECOVERY=16000


def candidate(source,workspace,plan_pin,checkpoint,snapshot_pin=None):
    source,workspace,jobs,completed=w.load(source,workspace,plan_pin,checkpoint,intent=True,recovery=True)
    index=len(completed)+1
    job=jobs[index-1]
    marker=workspace/"ACTIVE_JOB.json"
    intent=w.intent_bytes(plan_pin,job,checkpoint)
    pv.require(pv.read(marker,pv.MAX_JSON)==intent,"INTENT_BINDING")
    if job["kind"]=="PILOT_BACKUP":
        # The operator must supply the independently retained snapshot pin.
        # Never infer trust from a snapshot.json found after a crash.
        pv.pin(snapshot_pin)
        parent=completed[job["input"]["job"]][1]
        report=w.snapshot_report(workspace,job,parent,snapshot_pin)
        action="ADOPT_VERIFIED_BACKUP"
    elif job["kind"]=="PILOT_RESTORE":
        pv.require(snapshot_pin is None,"UNEXPECTED_SNAPSHOT_PIN")
        parent=completed[job["input"]["job"]][1]
        report=w.restored_report(workspace,job,parent)
        action="ADOPT_VERIFIED_RESTORE"
    else:
        pv.require(snapshot_pin is None,"UNEXPECTED_SNAPSHOT_PIN")
        # Read-only jobs may be freshly rechecked without repeating writes.
        report=w.recheck(source,workspace,job,completed)
        action="RECHECK_READ_ONLY"
    raw=json_bytes(w.receipt(plan_pin,index,job,checkpoint,completed,report))
    target=workspace/"receipts"/f"{index:02}.json"
    present=target.exists() or target.is_symlink()
    if present:pv.require(pv.read(target,pv.MAX_JSON)==raw,"UNCOMMITTED_RECEIPT_MISMATCH")
    obj={"schema":SCHEMA,"plan_sha256":plan_pin,"previous_sha256":checkpoint,
         "intent_sha256":sha(intent),"job_id":job["id"],"sequence":index,
         "action":action,"snapshot_sha256":snapshot_pin,"candidate_checkpoint_sha256":sha(raw),
         "receipt_already_present":present,"publication_eligible":False}
    return obj,raw,source,workspace,jobs,completed


def prepare(source,workspace,plan_pin,checkpoint=None,snapshot_pin=None):
    obj,*_=candidate(source,workspace,plan_pin,checkpoint,snapshot_pin)
    return json_bytes(obj)


def apply(source,workspace,plan_pin,checkpoint,recovery,recovery_pin):
    obj=pv.decode(pinned(recovery,recovery_pin,MAX_RECOVERY))
    pv.require(type(obj) is dict and set(obj)=={"schema","plan_sha256","previous_sha256","intent_sha256",
               "job_id","sequence","action","snapshot_sha256","candidate_checkpoint_sha256",
               "receipt_already_present","publication_eligible"} and obj["schema"]==SCHEMA
               and obj["plan_sha256"]==plan_pin and obj["previous_sha256"]==checkpoint
               and obj["publication_eligible"] is False,"RECOVERY_BINDING")
    actual,raw,source,workspace,jobs,completed=candidate(
        source,workspace,plan_pin,checkpoint,obj["snapshot_sha256"])
    # If interrupted between writing receipt and removing intent, the same
    # pinned plan may be applied again, but only with the exact expected bytes.
    if actual["receipt_already_present"] and obj["receipt_already_present"] is False:
        actual["receipt_already_present"]=False
    pv.require(json_bytes(actual)==recovery,"RECOVERY_PLAN_CHANGED")
    marker=workspace/"ACTIVE_JOB.json"
    pv.require(sha(pv.read(marker,pv.MAX_JSON))==obj["intent_sha256"],"INTENT_CHANGED")
    target=workspace/"receipts"/f'{obj["sequence"]:02}.json'
    if not (target.exists() or target.is_symlink()):w.write(target,raw)
    pv.require(pv.read(target,pv.MAX_JSON)==raw,"RECOVERY_RECEIPT_BYTES")
    # All succeeded receipts and artifacts, including the recovered job, must
    # be valid before the active marker is removed.
    index=obj["sequence"]
    job=jobs[index-1]
    completed[job["id"]]=(sha(raw),pv.decode(raw)["report"])
    marker.unlink()
    return {**w.summary(jobs,completed,sha(raw)),"recovered_job":job["id"],
            "recovery_action":obj["action"],"production_write_repeated":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("prepare","apply"):
        a=sub.add_parser(mode)
        for name in ("source-root","workspace","recovery"):
            a.add_argument("--"+name,type=Path,required=True)
        a.add_argument("--plan-sha256",required=True)
        a.add_argument("--checkpoint-sha256")
        if mode=="prepare":a.add_argument("--snapshot-sha256")
        else:
            a.add_argument("--recovery-sha256",required=True)
            a.add_argument("--confirm-recovery",action="store_true",required=True)
    a=p.parse_args()
    try:
        source,workspace=w.roots(a.source_root,a.workspace)
        path=ps.local_dir(a.recovery.absolute().parent)/a.recovery.name
        pv.require(path.suffix==".json" and not path.is_relative_to(source)
                   and not path.is_relative_to(workspace),"RECOVERY_PATH")
        common=(source,workspace,a.plan_sha256,a.checkpoint_sha256)
        if a.mode=="prepare":
            raw=prepare(*common,a.snapshot_sha256)
            w.write(path,raw)
            result={"recovery_sha256":sha(raw),"recovery_plan":pv.decode(raw),
                    "workflow_modified":False,"publication_eligible":False}
        else:
            result=apply(*common,private_file(path,MAX_RECOVERY),a.recovery_sha256)
    except Exception as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,
                          "manual_inspection_required":True,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
