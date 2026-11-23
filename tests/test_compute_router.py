from fastapi.testclient import TestClient
from app.compute_capabilities import ComputeRequest,select_worker
from app.main import app

def cpu():return {'worker_id':'local-desktop','backend':'CPU','cpu_cores':8,'ram_mb':32768}
def gpu():return {'worker_id':'gpu-future','backend':'NVIDIA_CUDA','cpu_cores':8,'ram_mb':32768,'vram_mb':24576,
                  'driver_observed':True,'adapter_live_tested':True}
def model():return {'model_id':'owner-licensed-video','model_sha256':'d'*64,'license_name':'Owner reviewed local license',
                    'rights_attested_by_owner':True,'commercial_use_allowed_per_owner':True,
                    'min_vram_mb':16000,'model_local_and_hash_checked':True,'generation_adapter_tested':True}

def test_cpu_route_preferred_and_no_implicit_gpu_claim():
    q=ComputeRequest(job_kind='CPU_STUDIO_RENDER',workers=[gpu(),cpu()])
    r=select_worker(q)
    assert r['backend']=='CPU' and r['model_executed'] is False
    assert r['status']=='ROUTE_SPEC_READY_NOT_EXECUTED'

def test_gpu_only_requires_live_test_license_model_and_vram():
    r=select_worker(ComputeRequest(job_kind='LOCAL_VIDEO_GENERATION',workers=[cpu()],model=model()))
    assert r['status']=='BLOCKED'
    assert r['no_silent_cpu_degradation_for_gpu_only_job']
    r=select_worker(ComputeRequest(job_kind='LOCAL_IMAGE_GENERATION',workers=[cpu(),gpu()],model={**model(),'model_local_and_hash_checked':False}))
    assert r['status']=='BLOCKED'
    r=select_worker(ComputeRequest(job_kind='LOCAL_IMAGE_GENERATION',workers=[cpu(),gpu()],model=model()))
    assert r['backend']=='NVIDIA_CUDA' and r['model_executed'] is False

def test_public_api_only_dry_run_never_model_execution():
    with TestClient(app) as client:
        caps=client.get('/api/compute/v1/capabilities').json()
        assert not caps['cuda_provider_implemented'] and not caps['model_downloads_automatic']
        result=client.post('/api/compute/v1/route-dry-run',json={'job_kind':'LOCAL_VIDEO_GENERATION','workers':[cpu()]}).json()
        assert result['status']=='BLOCKED'
