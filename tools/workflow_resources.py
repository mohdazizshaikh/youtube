"""Opt-in pinned resource admission for the stopped local workflow.

Observations and conservative logical-byte estimates, not reservations or OS
quotas. No worker pool, GPU detection, or automated retry. Existing unguarded
workflow CLI remains compatible.
"""
from __future__ import annotations
import argparse
import ctypes
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from tools import production_workflow as w
from tools import pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file

SCHEMA="VIRALOS_LOCAL_WORKFLOW_RESOURCE_POLICY_V1"
MIB=1024*1024
GIB=1024*MIB
MAX_POLICY=16000
# Per-artifact allowance for filesystem overhead, snapshot receipt and catalog.
OVERHEAD=8*MIB


def validate(raw,policy_pin,plan_pin):
    pv.pin(plan_pin)
    obj=pv.decode(pinned(raw,policy_pin,MAX_POLICY))
    pv.require(type(obj) is dict and set(obj)=={"schema","plan_sha256","min_cpu_count",
        "min_available_memory_mib","min_workspace_free_mib","min_temp_free_mib",
        "max_job_artifact_mib","max_total_artifact_mib"} and obj["schema"]==SCHEMA
        and obj["plan_sha256"]==plan_pin,"RESOURCE_POLICY_BINDING")
    for key,lo,hi in (("min_cpu_count",1,256),("min_available_memory_mib",128,262144),
        ("min_workspace_free_mib",64,1048576),("min_temp_free_mib",64,1048576),
        ("max_job_artifact_mib",8,2048),("max_total_artifact_mib",8,65536)):
        pv.require(pv.exact_int(obj[key],lo,hi),"RESOURCE_POLICY_RANGE")
    pv.require(obj["max_job_artifact_mib"]<=obj["max_total_artifact_mib"],"RESOURCE_BUDGET_ORDER")
    return obj


def embedded_policy(thresholds,plan_pin):
    pv.require(type(thresholds) is dict and set(thresholds)=={
        "min_cpu_count","min_available_memory_mib","min_workspace_free_mib",
        "min_temp_free_mib","max_job_artifact_mib","max_total_artifact_mib"},"EMBEDDED_POLICY_FIELDS")
    obj={"schema":SCHEMA,"plan_sha256":plan_pin,**thresholds}
    raw=w.json_bytes(obj)
    return validate(raw,sha(raw),plan_pin)


def plan_policy(raw,plan_pin):
    obj=pv.decode(pinned(raw,plan_pin,w.MAX_PLAN))
    if obj.get("schema")==w.PLAN_V2:return embedded_policy(obj["resources"],plan_pin)
    return None


def enforce_plan(source,workspace,plan_pin,jobs,completed):
    policy=plan_policy(pv.read(workspace/"plan.json",w.MAX_PLAN),plan_pin)
    if policy is not None:require_admitted(assessment(source,workspace,jobs,completed,policy))


def linux_available(raw):
    pv.require(type(raw) is str and len(raw)<=128000,"MEMORY_REPORT")
    rows=re.findall(r"(?m)^MemAvailable:\s+([0-9]+) kB$",raw)
    pv.require(len(rows)==1 and len(rows[0])<=16,"MEMORY_REPORT")
    value=int(rows[0])*1024
    pv.require(pv.exact_int(value,1,2**63-1),"MEMORY_REPORT")
    return value


def available_memory():
    if sys.platform.startswith("linux"):
        with open("/proc/meminfo","r",encoding="ascii") as f:
            return linux_available(f.read(128001))
    if sys.platform=="win32":
        class Status(ctypes.Structure):
            _fields_=[("length",ctypes.c_uint32),("load",ctypes.c_uint32)]+[
                (name,ctypes.c_uint64) for name in ("total_phys","avail_phys","total_page",
                "avail_page","total_virtual","avail_virtual","avail_extended")]
        obj=Status()
        obj.length=ctypes.sizeof(obj)
        fn=ctypes.WinDLL("kernel32",use_last_error=True).GlobalMemoryStatusEx
        fn.argtypes=[ctypes.POINTER(Status)]
        fn.restype=ctypes.c_int
        pv.require(fn(ctypes.byref(obj))!=0,"MEMORY_PROBE_FAILED")
        pv.require(pv.exact_int(obj.avail_phys,1,2**63-1),"MEMORY_REPORT")
        return obj.avail_phys
    raise ValueError("UNSUPPORTED_MEMORY_PROBE")


def observe(workspace):
    temp=Path(tempfile.gettempdir()).resolve(strict=True)
    return {"cpu_count":os.cpu_count(),"available_memory_bytes":available_memory(),
            "workspace_free_bytes":shutil.disk_usage(workspace).free,
            "temp_free_bytes":shutil.disk_usage(temp).free}


def evaluate(policy,observed,next_bytes,total_bytes):
    pv.require(type(observed) is dict and set(observed)=={"cpu_count","available_memory_bytes",
               "workspace_free_bytes","temp_free_bytes"},"RESOURCE_OBSERVATION")
    for k,v in observed.items():pv.require(pv.exact_int(v,0,2**63-1),"RESOURCE_OBSERVATION")
    pv.require(pv.exact_int(next_bytes,0,2**63-1) and pv.exact_int(total_bytes,0,2**63-1),
               "RESOURCE_ESTIMATE")
    # Reserve temp headroom on both volumes, even when shared. Conservative
    # rather than guessing filesystem identity or FFmpeg scratch usage.
    checks={
        "cpu":observed["cpu_count"]>=policy["min_cpu_count"],
        "memory":observed["available_memory_bytes"]>=policy["min_available_memory_mib"]*MIB,
        "workspace_disk":observed["workspace_free_bytes"]>=(
            policy["min_workspace_free_mib"]+policy["min_temp_free_mib"])*MIB+next_bytes,
        "temp_disk":observed["temp_free_bytes"]>=policy["min_temp_free_mib"]*MIB,
        "job_artifact_budget":next_bytes<=policy["max_job_artifact_mib"]*MIB,
        "total_artifact_budget":total_bytes+next_bytes<=policy["max_total_artifact_mib"]*MIB,
    }
    return {"admitted":all(checks.values()),"checks":checks,"observed":observed,
            "next_artifact_estimated_bytes":next_bytes,"committed_artifact_estimated_bytes":total_bytes,
            "hard_resource_limits_enforced":False,"publication_eligible":False}


def size(records):
    ps.validate_records(records)
    return sum(row["bytes"] for row in records.values())+OVERHEAD


def estimate(source,workspace,jobs,completed):
    total=0
    for job in jobs[:len(completed)]:
        kind=job["kind"]
        if kind=="PILOT_BACKUP":
            report=completed[job["id"]][1]
            meta=ps.inspect(workspace/"artifacts"/job["id"],report["snapshot_sha256"],
                            report["manifest_sha256"])
            total+=size(meta["files"])
        elif kind=="PILOT_RESTORE":
            total+=size(ps.inventory(ps.local_dir(workspace/"artifacts"/job["id"])))
    next_bytes=0
    if len(completed)<len(jobs):
        job=jobs[len(completed)]
        if job["kind"]=="PILOT_BACKUP":
            parent=completed[job["input"]["job"]][1]
            records=ps.inventory(ps.local_dir(source/parent["run"]))
            pv.require(pv.canonical(records)==parent["inventory_sha256"],"RESOURCE_SOURCE_CHANGED")
            next_bytes=size(records)
        elif job["kind"]=="PILOT_RESTORE":
            parent=completed[job["input"]["job"]][1]
            meta=ps.inspect(workspace/"artifacts"/job["input"]["job"],parent["snapshot_sha256"],
                            parent["manifest_sha256"])
            next_bytes=size(meta["files"])
    return next_bytes,total


def require_admitted(report):
    pv.require(report["admitted"] is True,"RESOURCE_ADMISSION_BLOCKED")


def initial(source,workspace,policy):
    source,workspace=w.roots(source,workspace)
    # Cheap host probe before expensive replay. Later checks add exact logical
    # artifact estimates derived from independently verified prerequisites.
    return source,workspace,evaluate(policy,observe(workspace),0,0)


def assessment(source,workspace,jobs,completed,policy):
    next_bytes,total=estimate(source,workspace,jobs,completed)
    return {**evaluate(policy,observe(workspace),next_bytes,total),
            "next_job":jobs[len(completed)]["id"] if len(completed)<len(jobs) else None}


def preflight(source,workspace,plan_pin,checkpoint,raw,policy_pin):
    policy=validate(raw,policy_pin,plan_pin)
    source,workspace,report=initial(source,workspace,policy)
    if not report["admitted"]:
        return {**report,"prerequisites_replayed":False,"policy_sha256":policy_pin}
    source,workspace,jobs,completed=w.load(source,workspace,plan_pin,checkpoint)
    report=assessment(source,workspace,jobs,completed,policy)
    return {**report,"prerequisites_replayed":True,"policy_sha256":policy_pin}


def guarded_step(source,workspace,plan_pin,checkpoint,raw,policy_pin):
    policy=validate(raw,policy_pin,plan_pin)
    source,workspace,report=initial(source,workspace,policy)
    require_admitted(report)
    def admission(source,workspace,jobs,completed):
        require_admitted(assessment(source,workspace,jobs,completed,policy))
    result=w.step(source,workspace,plan_pin,checkpoint,admission=admission)
    return {**result,"resource_policy_sha256":policy_pin,"resource_admission_checked":True,
            "hard_resource_limits_enforced":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("preflight","step"):
        a=sub.add_parser(mode)
        for name in ("source-root","workspace","policy"):a.add_argument("--"+name,type=Path,required=True)
        a.add_argument("--plan-sha256",required=True)
        a.add_argument("--checkpoint-sha256")
        a.add_argument("--policy-sha256",required=True)
    a=p.parse_args()
    try:
        args=(a.source_root,a.workspace,a.plan_sha256,a.checkpoint_sha256,
              private_file(a.policy,MAX_POLICY),a.policy_sha256)
        result=(preflight if a.mode=="preflight" else guarded_step)(*args)
    except Exception as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,
                          "inspect_active_intent_before_retry":True,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0 if result.get("admitted",True) else 2


if __name__=="__main__":
    raise SystemExit(main())
