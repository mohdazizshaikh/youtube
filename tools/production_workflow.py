"""Bounded local production audit/recovery DAG; one explicit step at a time.

This is a narrow implementation slice of the canonical workflow specification,
not a general command runner, scheduler, distributed worker or release gate.
Stopped owner-local inputs only. Retain every returned checkpoint independently.
"""
from __future__ import annotations
import argparse
import json
import os
import re
from pathlib import Path

from tools import pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file
from tools.bilingual_pilot import json_bytes

PLAN="VIRALOS_LOCAL_PRODUCTION_WORKFLOW_V1"
RECEIPT="VIRALOS_LOCAL_PRODUCTION_JOB_RECEIPT_V1"
INTENT="VIRALOS_LOCAL_PRODUCTION_JOB_INTENT_V1"
MAX_PLAN=128000
MAX_JOBS=32
KINDS={"PILOT_AUDIT","PILOT_BACKUP","SNAPSHOT_AUDIT","PILOT_RESTORE"}
ARTIFACT_KINDS={"PILOT_BACKUP","PILOT_RESTORE"}


def leaf(value):
    pv.require(type(value) is str and re.fullmatch(r"[a-z][a-z0-9_-]{0,47}",value)
               and not re.fullmatch(r"con|prn|aux|nul|com[0-9]|lpt[0-9]",value),"UNSAFE_LEAF")
    return value


def validate(raw,plan_pin):
    obj=pv.decode(pinned(raw,plan_pin,MAX_PLAN))
    pv.require(type(obj) is dict and set(obj)=={"schema","jobs"} and obj["schema"]==PLAN,"PLAN_FIELDS")
    jobs=obj["jobs"]
    pv.require(type(jobs) is list and 1<=len(jobs)<=MAX_JOBS,"JOB_COUNT")
    by={}
    for row in jobs:
        pv.require(type(row) is dict and set(row)=={"id","kind","depends_on","input"},"JOB_FIELDS")
        name=leaf(row["id"])
        pv.require(name not in by,"DUPLICATE_JOB")
        kind=row["kind"]
        pv.require(type(kind) is str and kind in KINDS,"JOB_KIND")
        deps=row["depends_on"]
        pv.require(type(deps) is list and len(deps)<MAX_JOBS,"DEPENDENCIES")
        for dep in deps:leaf(dep)
        pv.require(len(set(deps))==len(deps) and name not in deps,"DEPENDENCY_DUPLICATE")
        arg=row["input"]
        if kind=="PILOT_AUDIT":
            pv.require(type(arg) is dict and set(arg)=={"run","manifest_sha256"},"AUDIT_INPUT")
            leaf(arg["run"])
            pv.pin(arg["manifest_sha256"])
        else:
            pv.require(type(arg) is dict and set(arg)=={"job"},"DEPENDENT_INPUT")
            pv.require(leaf(arg["job"]) in deps,"INPUT_DEPENDENCY_REQUIRED")
        by[name]=row
    for row in jobs:
        pv.require(all(d in by for d in row["depends_on"]),"UNKNOWN_DEPENDENCY")
        if row["kind"]!="PILOT_AUDIT":
            parent=by[row["input"]["job"]]
            expected="PILOT_AUDIT" if row["kind"]=="PILOT_BACKUP" else "PILOT_BACKUP"
            pv.require(parent["kind"]==expected,"DEPENDENCY_KIND")
            if row["kind"]=="PILOT_RESTORE":
                pv.require(any(by[d]["kind"]=="SNAPSHOT_AUDIT" and
                               by[d]["input"]["job"]==parent["id"] for d in row["depends_on"]),
                           "SNAPSHOT_AUDIT_DEPENDENCY_REQUIRED")
    ordered=[]
    done=set()
    while len(done)<len(jobs):
        ready=next((r for r in jobs if r["id"] not in done and set(r["depends_on"])<=done),None)
        pv.require(ready is not None,"DEPENDENCY_CYCLE")
        ordered.append(ready)
        done.add(ready["id"])
    return ordered


def write(path,raw):
    with path.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    pv.require(pv.read(path,len(raw))==raw,"WORKFLOW_WRITE")


def roots(source,workspace):
    source,workspace=ps.local_dir(source),ps.local_dir(workspace)
    pv.require(not workspace.is_relative_to(source) and not source.is_relative_to(workspace),
               "OVERLAPPING_ROOTS")
    return source,workspace


def initialize(source,workspace,raw,plan_pin):
    jobs=validate(raw,plan_pin)
    source=ps.local_dir(source)
    workspace=ps.new_dir(workspace,source)
    # Resolve all original run paths before writing anything. Never traverse
    # a user-specified multi-component path or a symlink/reparse leaf.
    for job in jobs:
        if job["kind"]=="PILOT_AUDIT":
            ps.local_dir(source/job["input"]["run"])
    workspace.mkdir(mode=0o700)
    marker=workspace/"INCOMPLETE"
    marker.touch(exist_ok=False)
    (workspace/"receipts").mkdir(mode=0o700)
    (workspace/"artifacts").mkdir(mode=0o700)
    write(workspace/"plan.json",raw)
    marker.unlink()
    return {"plan_sha256":plan_pin,"jobs":len(jobs),"checkpoint_sha256":None,
            "publication_eligible":False}


def audit(source,job):
    arg=job["input"]
    run=ps.local_dir(source/arg["run"])
    pin=arg["manifest_sha256"]
    report=pv.verify(run,pin,fresh=True)
    pv.require(report["fresh_media_audit"] is True and report["integrity_passed"] is True
               and report["publication_eligible"] is False,"FRESH_AUDIT_REQUIRED")
    inventory=ps.inventory(run)
    pv.require(inventory["draft/manifest.json"]["sha256"]==pin,"MANIFEST_PIN")
    pv.require(pv.verify(run,pin)=={**report,"fresh_media_audit":False}
               and ps.inventory(run)==inventory,"SOURCE_CHANGED")
    return {"run":arg["run"],"manifest_sha256":pin,"inventory_sha256":pv.canonical(inventory),
            "queue_revision":report["queue_revision"],"queue_state":report["queue_state"],
            "synthetic_demo":report["synthetic_demo"],"fresh_media_audit":True}


def snapshot_report(workspace,job,parent,snapshot_pin):
    pin=pv.pin(snapshot_pin)
    meta=ps.inspect(workspace/"artifacts"/job["id"],pin,parent["manifest_sha256"])
    pv.require(pv.canonical(meta["files"])==parent["inventory_sha256"] and
               meta["queue_revision"]==parent["queue_revision"] and
               meta["queue_state"]==parent["queue_state"],"SNAPSHOT_PARENT_CHANGED")
    return {"snapshot_sha256":pin,"manifest_sha256":parent["manifest_sha256"],
            "inventory_sha256":parent["inventory_sha256"],"queue_revision":meta["queue_revision"],
            "queue_state":meta["queue_state"],"files":len(meta["files"])}


def restored_report(workspace,job,parent):
    snapshot=ps.local_dir(workspace/"artifacts"/job["input"]["job"])
    meta=ps.inspect(snapshot,parent["snapshot_sha256"],parent["manifest_sha256"])
    output=ps.local_dir(workspace/"artifacts"/job["id"])
    checked=pv.verify(output,parent["manifest_sha256"],fresh=True)
    records=ps.inventory(output)
    pv.require(checked["fresh_media_audit"] is True and checked["integrity_passed"] is True and
               checked["publication_eligible"] is False and
               checked["queue_revision"]==meta["queue_revision"] and
               checked["queue_state"]==meta["queue_state"],"RESTORE_AUDIT")
    pv.require(set(records)==set(meta["files"]) and
               all(records[k]==v for k,v in meta["files"].items() if k!="catalog.json"),
               "RESTORE_BYTES")
    pv.require(ps.inspect(snapshot,parent["snapshot_sha256"],parent["manifest_sha256"])==meta
               and ps.inventory(output)==records and
               pv.verify(output,parent["manifest_sha256"])=={**checked,"fresh_media_audit":False},
               "RESTORE_CHANGED")
    return {"snapshot_sha256":parent["snapshot_sha256"],"manifest_sha256":parent["manifest_sha256"],
            "restored_inventory_sha256":pv.canonical(records),"queue_revision":checked["queue_revision"],
            "queue_state":checked["queue_state"],"fresh_media_audit":True}


def intent_bytes(plan_pin,job,checkpoint):
    return json_bytes({"schema":INTENT,"plan_sha256":plan_pin,"job_id":job["id"],
                       "previous_sha256":checkpoint,"publication_eligible":False})


def receipt(plan_pin,index,job,previous,completed,report):
    return {"schema":RECEIPT,"plan_sha256":plan_pin,"sequence":index,
            "job_id":job["id"],"kind":job["kind"],"state":"SUCCEEDED",
            "previous_sha256":previous,
            "dependency_receipts":{d:completed[d][0] for d in job["depends_on"]},
            "report":report,"publication_eligible":False}


def recheck(source,workspace,job,completed,stored=None):
    kind=job["kind"]
    if kind=="PILOT_AUDIT":
        return audit(source,job)
    parent=completed[job["input"]["job"]][1]
    if kind=="PILOT_BACKUP":
        if stored is None:
            out=workspace/"artifacts"/job["id"]
            result=ps.backup(source/parent["run"],out,parent["manifest_sha256"])
            pin=result["snapshot_sha256"]
        else:
            pin=stored["snapshot_sha256"]
        return snapshot_report(workspace,job,parent,pin)
    if kind=="PILOT_RESTORE":
        if stored is None:
            ps.restore(workspace/"artifacts"/job["input"]["job"],
                       workspace/"artifacts"/job["id"],parent["snapshot_sha256"],
                       parent["manifest_sha256"])
        return restored_report(workspace,job,parent)
    # SNAPSHOT_AUDIT is read-only; the snapshot dependency was itself
    # rechecked against its original audit during chain replay.
    meta=ps.inspect(workspace/"artifacts"/job["input"]["job"],
                    parent["snapshot_sha256"],parent["manifest_sha256"])
    pv.require(pv.canonical(meta["files"])==parent["inventory_sha256"],"SNAPSHOT_INVENTORY_CHANGED")
    return {**parent,"snapshot_integrity_passed":True,"fresh_media_audit":False}


def load(source,workspace,plan_pin,checkpoint,*,intent=False,recovery=False):
    pv.require(not recovery or intent,"RECOVERY_INTENT_REQUIRED")
    source,workspace=roots(source,workspace)
    expected={"plan.json","receipts","artifacts"}
    if intent:expected.add("ACTIVE_JOB.json")
    pv.require({x.name for x in workspace.iterdir()}==expected,"WORKSPACE_INCOMPLETE_OR_ACTIVE")
    if intent:pv.plain(workspace/"ACTIVE_JOB.json")
    jobs=validate(pv.read(workspace/"plan.json",MAX_PLAN),plan_pin)
    for name in ("receipts","artifacts"):pv.plain(workspace/name,True)
    entries={p.name for p in (workspace/"receipts").iterdir()}
    count=len(entries)
    pv.require(count<=len(jobs) and entries=={f"{i:02}.json" for i in range(1,count+1)},
               "RECEIPT_SEQUENCE")
    if recovery and count and sha(pv.read(workspace/"receipts"/f"{count:02}.json",pv.MAX_JSON))!=checkpoint:
        # At most one uncommitted receipt may follow the externally pinned tip.
        count-=1
    if count:
        pv.pin(checkpoint)
    else:
        pv.require(checkpoint is None,"INITIAL_CHECKPOINT")
    # Check the external chain tip and all hashes BEFORE running verifiers.
    raw_rows=[pv.read(workspace/"receipts"/f"{i:02}.json",pv.MAX_JSON) for i in range(1,count+1)]
    previous=None
    completed={}
    for index,(job,raw) in enumerate(zip(jobs,raw_rows),1):
        obj=pv.decode(raw)
        pv.require(type(obj) is dict and type(obj.get("report")) is dict,"RECEIPT_FIELDS")
        expected_row=receipt(plan_pin,index,job,previous,completed,obj["report"])
        pv.require(raw==json_bytes(expected_row),"RECEIPT_BINDING")
        previous=sha(raw)
        completed[job["id"]]=(previous,obj["report"])
    pv.require(previous==checkpoint,"CHECKPOINT_PIN")
    artifacts={j["id"] for j in jobs[:count] if j["kind"] in ARTIFACT_KINDS}
    actual={x.name for x in (workspace/"artifacts").iterdir()}
    if intent:
        pv.require(count<len(jobs),"NO_ACTIVE_JOB")
        pending=jobs[count]
        pv.require(pv.read(workspace/"ACTIVE_JOB.json",pv.MAX_JSON)==
                   intent_bytes(plan_pin,pending,checkpoint),"INTENT_BINDING")
        if recovery and pending["kind"] in ARTIFACT_KINDS:
            # Only the exact active artifact is allowed in addition to the
            # committed inventory. Recovery will independently audit it.
            pv.require(actual in (artifacts,artifacts|{pending["id"]}),"ARTIFACT_INVENTORY")
        else:pv.require(actual==artifacts,"ARTIFACT_INVENTORY")
    else:pv.require(actual==artifacts,"ARTIFACT_INVENTORY")
    # Freshly verify every succeeded job in order. A changed queue, source,
    # snapshot or external checkpoint fails closed before the next job.
    verified={}
    for job in jobs[:count]:
        digest,stored=completed[job["id"]]
        current=recheck(source,workspace,job,verified,stored)
        pv.require(current==stored,"COMPLETED_JOB_CHANGED")
        verified[job["id"]]=(digest,current)
    return source,workspace,jobs,verified


def summary(jobs,completed,checkpoint):
    next_job=jobs[len(completed)]["id"] if len(completed)<len(jobs) else None
    return {"checkpoint_sha256":checkpoint,"completed":len(completed),"total_jobs":len(jobs),
            "next_job":next_job,"workflow_complete":next_job is None,
            "jobs":[{"id":j["id"],"kind":j["kind"],
                     "state":"SUCCEEDED" if j["id"] in completed else
                     ("READY" if j["id"]==next_job else "QUEUED")}
                    for j in jobs],"publication_eligible":False}


def status(source,workspace,plan_pin,checkpoint=None):
    _,_,jobs,completed=load(source,workspace,plan_pin,checkpoint)
    return summary(jobs,completed,checkpoint)


def step(source,workspace,plan_pin,checkpoint=None,*,admission=None):
    source,workspace,jobs,completed=load(source,workspace,plan_pin,checkpoint)
    index=len(completed)+1
    if index>len(jobs):return summary(jobs,completed,checkpoint)
    job=jobs[index-1]
    if admission is not None:admission(source,workspace,jobs,completed)
    marker=workspace/"ACTIVE_JOB.json"
    write(marker,intent_bytes(plan_pin,job,checkpoint))
    # Recheck after exclusive intent acquisition. Any failure leaves the
    # intent and any partial output; never retry an ambiguous side effect.
    source,workspace,jobs,completed=load(source,workspace,plan_pin,checkpoint,intent=True)
    if admission is not None:admission(source,workspace,jobs,completed)
    report=recheck(source,workspace,job,completed)
    if job["kind"]=="PILOT_BACKUP":
        audit_job=next(j for j in jobs if j["id"]==job["input"]["job"])
        parent=completed[audit_job["id"]][1]
        pv.require(audit(source,audit_job)==parent,"SOURCE_CHANGED")
    row=receipt(plan_pin,index,job,checkpoint,completed,report)
    raw=json_bytes(row)
    write(workspace/"receipts"/f"{index:02}.json",raw)
    new_pin=sha(raw)
    completed[job["id"]]=(new_pin,report)
    marker.unlink()
    return summary(jobs,completed,new_pin)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("init","status","step"):
        a=sub.add_parser(mode)
        a.add_argument("--source-root",type=Path,required=True)
        a.add_argument("--workspace",type=Path,required=True)
        a.add_argument("--plan-sha256",required=True)
        if mode=="init":a.add_argument("--plan",type=Path,required=True)
        else:a.add_argument("--checkpoint-sha256")
    a=p.parse_args()
    try:
        if a.mode=="init":
            result=initialize(a.source_root,a.workspace,private_file(a.plan,MAX_PLAN),a.plan_sha256)
        else:
            result=(step if a.mode=="step" else status)(a.source_root,a.workspace,a.plan_sha256,
                                                         a.checkpoint_sha256)
    except Exception as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,
                          "manual_inspection_required":True,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
