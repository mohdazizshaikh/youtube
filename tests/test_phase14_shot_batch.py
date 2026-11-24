import json, hashlib, subprocess
from pathlib import Path
import pytest
try:
    from tools import phase14_shot_batch as b, phase14_shot_index as ix
except ImportError:
    import phase14_shot_batch as b, phase14_shot_index as ix

@pytest.fixture
def clip(tmp_path):
    # Real lossless encoded 30-frame fixture; skip only where FFmpeg is absent.
    import shutil
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):pytest.skip('FFmpeg not available')
    p=tmp_path/'source.mp4'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i','testsrc2=size=1920x1080:rate=30','-frames:v','30','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p',str(p)],check=True,timeout=30)
    return p

def test_frame_hash_contract(clip):
    h=b.frame_hashes(clip,30);assert len(h)==30 and len(set(h))==30
    with pytest.raises(ValueError):b.frame_hashes(clip,29)

def test_lossless_extract_and_resume(clip,tmp_path):
    h=b.frame_hashes(clip,30);t=dict(id='en-01',start_frame=3,end_frame=27,status='OPEN')
    args=(tmp_path/'shot',clip,hashlib.sha256(clip.read_bytes()).hexdigest(),t,h,'a'*64)
    r,st=b.shot(*args);assert st=='created' and r['frames']==24 and r['decoded_pixels_match'] and not r['publication_authorized']
    assert b.shot(*args)==(r,'revalidated')
    (tmp_path/'shot'/'receipt.json').write_text('{}')
    with pytest.raises(ValueError,match='cached receipt'):b.shot(*args)

def test_partial_preserved(clip,tmp_path):
    d=tmp_path/'partial';d.mkdir();(d/'INCOMPLETE').write_text('partial')
    with pytest.raises(ValueError,match='incomplete shot'):b.shot(d,clip,'a'*64,dict(start_frame=0,end_frame=30),b.frame_hashes(clip,30),'b'*64)
    assert (d/'INCOMPLETE').read_text()=='partial'

def test_wrong_source_frame_rejected(clip,tmp_path):
    h=b.frame_hashes(clip,30);h[0]='0'*64
    with pytest.raises(ValueError,match='decoded shot differs'):b.shot(tmp_path/'bad',clip,'a'*64,dict(start_frame=0,end_frame=30),h,'b'*64)
    assert (tmp_path/'bad'/'INCOMPLETE').exists()

def test_index_requires_complete_batch(tmp_path):
    report=tmp_path/'batch.json';tasks=tmp_path/'tasks.json'
    report.write_text(json.dumps(dict(shots=[],schema='VIRALOS_SHOT_BATCH_RESULT_V1',publication_authorized=False,production_accepted=False,human_review_required=True,shot_count=0,operation_count=0)))
    tasks.write_text('{"tasks": []}')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='complete batch'):ix.index(tmp_path,report,digest(report),tasks,digest(tasks),tmp_path/'index.html')

def test_index_active_lock(tmp_path):
    (tmp_path/'RUNNING').touch()
    with pytest.raises(ValueError,match='active'):ix.index(tmp_path,'x','a'*64,'y','b'*64,tmp_path/'index.html')
