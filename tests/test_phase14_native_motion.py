import hashlib,json
from pathlib import Path
import pytest
try:
    from tools import phase14_native_motion as n, phase14_editorial_tasks as e
except ImportError:
    import phase14_native_motion as n, phase14_editorial_tasks as e

@pytest.mark.parametrize('count',[30,256,367,2700])
def test_progress(count):
    p=[n.progress(i,count) for i in range(count)]
    assert p[0]==1 and p[-1]==256 and p==sorted(p)

@pytest.mark.parametrize('frame,count',[(True,30),(-1,30),(30,30),(0,29),(0,2701)])
def test_invalid_progress(frame,count):
    with pytest.raises(ValueError):n.progress(frame,count)

def test_digest():
    assert len(n.A)==len(n.B)==len(n.X)==256
    assert n.TOTAL==125 and sum(n.X)==125
    assert n.X==tuple(int(a!=b) for a,b in zip(n.A,n.B))

def test_cached_shot(tmp_path,monkeypatch):
    pin='a'*64;v='b'*64
    (tmp_path/'shot0.mp4').write_bytes(b'fake')
    d=dict(run_sha256=pin,beat=0,frames=30,video_sha256=v,publication_authorized=False)
    (tmp_path/'shot0.json').write_text(json.dumps(d))
    monkeypatch.setattr(n,'verify_clip',lambda *args:v)
    assert n.shot(tmp_path,pin,'en',0,30,'unused')==('reused',d)
    with pytest.raises(ValueError):n.shot(tmp_path,'c'*64,'en',0,30,'unused')

def test_partial_refused(tmp_path):
    (tmp_path/'shot0.partial.mp4').touch()
    with pytest.raises(ValueError):
        # Isolate checkpoint behavior from host font installation.
        from unittest.mock import patch
        with patch.object(n,'layout',return_value=(None,None)):
            n.shot(tmp_path,'a'*64,'en',0,30,'unused')

def make_config(root):
    def save(name,obj):
        p=root/name;p.write_text(json.dumps(obj));return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    locales={}
    for l in ('en','hi'):
        p=('a' if l=='en' else 'b')*64;rows=[dict(shot=i,start_frame=i*30,end_frame=(i+1)*30,freeze_frames=30 if i==0 else 0,expected='semantic_motion_expected',review_status='UNEXPECTED_FREEZE_REVIEW' if i==0 else 'NO_FREEZE_DETECTED') for i in range(24)]
        sc=dict(schema='VIRALOS_VARIABLE_SCENE_QC_V1',video_sha256=p,frames=720,shots=rows,freeze_frames=30,freeze_fraction=round(30/720,6),unexpected_freeze_shots=1,original_review_flags=['STATIC_OR_FREEZE_REVIEW'],semantic_quality_verified=False,publication_authorized=False)
        hand=dict(schema='VIRALOS_SEMANTIC_HANDOFF_V1',locale=l,video_sha256=p,frames=720,chapters=[dict(start_frame=i*90) for i in range(8)],freeze_fraction=sc['freeze_fraction'],unexpected_freeze_shots=1,review_flags=sc['original_review_flags'],production_accepted=False,publication_authorized=False)
        locales[l]=dict(scene=save(l+'scene.json',sc),handoff=save(l+'hand.json',hand))
    cfg=save('config.json',dict(schema='VIRALOS_EDITORIAL_TASK_CONFIG_V1',locales=locales));return cfg

def test_editorial_tasks(tmp_path):
    c=make_config(tmp_path);out=tmp_path/'out.json'
    r=e.tasks(c['path'],c['sha256'],out)
    assert r['task_count']==48 and r['motion_review_count']==2 and not r['publication_authorized']
    assert all(x['status']=='OPEN' for x in r['tasks'])
    assert all(x['freeze_frames']==30 for x in r['tasks'][:2])
    with pytest.raises(ValueError):e.tasks(c['path'],c['sha256'],out)

def test_editorial_tamper(tmp_path):
    c=make_config(tmp_path);(tmp_path/'enscene.json').write_text('{}')
    with pytest.raises(ValueError):e.tasks(c['path'],c['sha256'],tmp_path/'out.json')

def test_hex_values():
    assert n.HEX==tuple(hashlib.sha256(x).hexdigest() for x in (b'hello',b'Hello'))
    assert all(len(x)==64 for x in n.HEX)

@pytest.mark.parametrize('chapter',[True,2,5,'3'])
def test_unsupported_chapter(chapter):
    with pytest.raises(ValueError):n.run('en','unused','unused','a'*64,'unused','unused',chapter=chapter)
