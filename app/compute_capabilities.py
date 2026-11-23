"""CPU-first job routing contract; GPU is never implicitly assumed available.

No GPU model is loaded, downloaded, executed or declared production-validated.
This contract intentionally distinguishes a driver probe from a tested adapter.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from fastapi import HTTPException

CPU_JOBS=frozenset({'CPU_STUDIO_RENDER','CPU_ORIGINAL_DIAGRAM','OWNER_WAV_CAPTIONS','OFFLINE_TEXT_QC'})
GPU_JOBS=frozenset({'LOCAL_IMAGE_GENERATION','LOCAL_VIDEO_GENERATION'})

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Worker(Strict):
    worker_id: str=Field(min_length=2,max_length=100)
    backend: Literal['CPU','NVIDIA_CUDA']
    cpu_cores: int=Field(ge=1,le=512)
    ram_mb: int=Field(ge=1024,le=1048576)
    vram_mb: int=Field(default=0,ge=0,le=1048576)
    driver_observed: bool=False
    adapter_live_tested: bool=False

class ModelLicense(Strict):
    model_id: str=Field(min_length=2,max_length=150)
    model_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')
    license_name: str=Field(min_length=3,max_length=250)
    rights_attested_by_owner: bool
    commercial_use_allowed_per_owner: bool
    min_vram_mb: int=Field(ge=1024,le=1048576)
    model_local_and_hash_checked: bool
    generation_adapter_tested: bool

class ComputeRequest(Strict):
    job_kind: Literal['CPU_STUDIO_RENDER','CPU_ORIGINAL_DIAGRAM','OWNER_WAV_CAPTIONS','OFFLINE_TEXT_QC',
                      'LOCAL_IMAGE_GENERATION','LOCAL_VIDEO_GENERATION']
    workers: list[Worker]=Field(min_length=1,max_length=40)
    model: ModelLicense|None=None
    allow_cpu_fallback: bool=True


def select_worker(request:ComputeRequest)->dict:
    if request.job_kind in CPU_JOBS:
        cpus=[w for w in request.workers if w.backend=='CPU' and w.ram_mb>=2048]
        if not cpus:return {'status':'BLOCKED','reason':'NO_COMPATIBLE_CPU_WORKER', 'model_executed':False}
        w=sorted(cpus,key=lambda item:(-item.ram_mb,-item.cpu_cores,item.worker_id))[0]
        return {'status':'ROUTE_SPEC_READY_NOT_EXECUTED','backend':'CPU','worker_id':w.worker_id,
                'model_executed':False,'tested_gpu_capability_claimed':False}
    if request.job_kind in GPU_JOBS:
        model=request.model
        if model is None:return {'status':'BLOCKED','reason':'LICENSED_LOCAL_MODEL_MANIFEST_REQUIRED','model_executed':False}
        if not (model.rights_attested_by_owner and model.commercial_use_allowed_per_owner
                and model.model_local_and_hash_checked and model.generation_adapter_tested):
            return {'status':'BLOCKED','reason':'MODEL_LICENSE_HASH_OR_ADAPTER_UNVERIFIED','model_executed':False}
        available=[w for w in request.workers if w.backend=='NVIDIA_CUDA' and w.driver_observed
                   and w.adapter_live_tested and w.vram_mb>=model.min_vram_mb]
        if available:
            w=sorted(available,key=lambda item:(-item.vram_mb,item.worker_id))[0]
            return {'status':'ROUTE_SPEC_READY_NOT_EXECUTED','backend':'NVIDIA_CUDA','worker_id':w.worker_id,
                    'model_executed':False,'tested_gpu_capability_claimed':False}
        return {'status':'BLOCKED','reason':'NO_OWNER_VALIDATED_GPU_WORKER_OR_VRAM_INSUFFICIENT',
                'no_silent_cpu_degradation_for_gpu_only_job':True,'model_executed':False}
    raise ValueError('Unknown job type')


def register_compute(app):
    @app.get('/api/compute/v1/capabilities')
    def compute_caps():
        return {'cpu_supported_jobs':sorted(CPU_JOBS),'gpu_jobs_declared_not_executed':sorted(GPU_JOBS),
                'cuda_provider_implemented':False,'live_gpu_tested_here':False,
                'remote_worker_dispatch_enabled':False,'model_downloads_automatic':False,
                'one_project_identity_across_cpu_gpu':True}

    @app.post('/api/compute/v1/route-dry-run')
    def dry_run(b:ComputeRequest):
        return select_worker(b)
