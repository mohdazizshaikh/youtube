import json, hashlib, shutil, subprocess
from pathlib import Path
import pytest
try:
    from tools import phase14_delivery as d, phase14_proxy_review as r, phase14_shot_batch as b, phase14_scene_review as s
except ImportError:
    import phase14_delivery as d, phase14_proxy_review as r, phase14_shot_batch as b, phase14_scene_review as s

@pytest.fixture
def source(tmp_path):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):pytest.skip('FFmpeg required')
    p=tmp_path/'source.mp4'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i','testsrc2=size=1920x1080:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','2','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac',str(p)],check=True,timeout=30)
    return p

@pytest.fixture
def shots(source,tmp_path):
    h=b.frame_hashes(source,60);rows=[]
    for i,(a,z) in enumerate(((0,23),(23,60))):
        t=dict(id=f'en-{i+1:02}',start_frame=a,end_frame=z,status='OPEN',video_sha256=d.digest(source));folder=tmp_path/t['id'];rec,_=b.shot(folder,source,d.digest(source),t,h,'a'*64);rows.append((folder,rec,s.sha(s.encoded(rec))))
    return rows

def test_actual_proxy_resume(shots,tmp_path):
    folder,rec,pin=shots[0];out=tmp_path/'proxy';a=d.proxy(out,folder,rec,pin)
    assert a['frames']==23 and a['decode_pass'] and not a['browser_playback_verified'] and not a['publication_authorized']
    assert d.proxy(out,folder,rec,pin)==a
    (out/'receipt.json').write_text('{}')
    with pytest.raises(ValueError,match='receipt mismatch'):d.proxy(out,folder,rec,pin)

def test_actual_reassembly(source,shots,tmp_path):
    out=tmp_path/'assembled';rec=d.reassemble(out,source,d.digest(source),60,shots)
    assert rec['frames']==60 and rec['all_shot_sequences_match'] and rec['exact_audio_packets_match']
    assert b.frame_hashes(out/'reassembled.mp4',60)==b.frame_hashes(source,60)
    assert not rec['publication_authorized']

def test_partial_proxy_rejected(shots,tmp_path):
    out=tmp_path/'partial';out.mkdir();(out/'INCOMPLETE').touch()
    with pytest.raises(ValueError,match='partial proxy'):d.proxy(out,*shots[0])
    assert (out/'INCOMPLETE').exists()

@pytest.fixture
def row():return dict(task=dict(id='hi-01',video_sha256='a'*64,start_frame=10,end_frame=30),proxy_sha256='b'*64)

def note(row):
    x=r.template(row,'c'*64);x.update(source_frame=11,category='motion',note='Review visual timing');return x

def test_note_identity_revision(row):
    n=note(row);assert r.validate_note(n,row,'c'*64,0)['status']=='OPEN'
    with pytest.raises(ValueError,match='stale'):r.validate_note(n,row,'c'*64,1)
    n['proxy_sha256']='d'*64
    with pytest.raises(ValueError,match='identity'):r.validate_note(n,row,'c'*64,0)

@pytest.mark.parametrize('patch',[{'source_frame':30},{'source_frame':True},{'category':'approve'},{'note':' '},{'note':'x'*1001},{'note':'bad\x00'}])
def test_note_invalid(row,patch):
    n=note(row);n.update(patch)
    with pytest.raises(ValueError):r.validate_note(n,row,'c'*64,0)

def test_template_is_incomplete(row):
    with pytest.raises(ValueError):r.validate_note(r.template(row,'c'*64),row,'c'*64,0)

def test_append_chain(tmp_path,row,monkeypatch):
    monkeypatch.setattr(r,'load',lambda *a:{'hi-01':(row,'c'*64)})
    n=note(row);p=tmp_path/'submission.json';p.write_bytes(s.encoded(n));args=('unused','unused','a'*64,tmp_path/'ledger',p,d.digest(p))
    assert r.append(*args)['revision']==1
    with pytest.raises(ValueError,match='stale'):r.append(*args)
    n['expected_revision']=1;p.write_bytes(s.encoded(n));args=(*args[:-1],d.digest(p));assert r.append(*args)['revision']==2
    item=tmp_path/'ledger'/'note-0001.json';x=json.loads(item.read_bytes());x['previous_sha256']='f'*64;item.write_bytes(s.encoded(x))
    with pytest.raises(ValueError,match='chain mismatch'):r.append(*args)
