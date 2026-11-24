"""Regression tests for the semantic experiment and report orchestration."""
import hashlib,json
from pathlib import Path
import pytest
try:
    from tools import phase14_scene_review as s, phase14_semantic_motion as m
except ImportError:
    import phase14_scene_review as s, phase14_semantic_motion as m

PIN='a'*64

def data():
    rows=[dict(chapter=f'{i//3+1:02}',beat=i%3,start_frame=i*30,end_frame=(i+1)*30,samples=48000,padding_samples=0) for i in range(24)]
    q=dict(schema='VIRALOS_SIGNAL_QC_V1',publication_authorized=False,audit=dict(video_sha256=PIN,decode_pass=True,numeric_audio_gate_pass=True,frames=720),visual=dict(freeze_events=[dict(event='start',seconds=0),dict(event='end',seconds=2),dict(event='start',seconds=23)]),review_flags=['STATIC_OR_FREEZE_REVIEW'])
    return q,dict(frames=720,shots=rows,publication_authorized=False)

def test_experiment():
    a,b,bits=m.experiment();assert a==hashlib.sha256(b'hello').hexdigest();assert b==hashlib.sha256(b'Hello').hexdigest();assert len(bits)==256 and sum(bits)==125

def test_expected_and_unexpected():
    q,t=data();policy=[s.EXPECTATIONS[0]]*24;policy[1]=s.EXPECTATIONS[1]
    r=s.assess(q,t,policy);assert r['freeze_frames']==90 and r['unexpected_freeze_shots']==1 and r['expected_static_review_shots']==2
    assert r['freeze_intervals'][-1]['closed_at_eof'] and not r['publication_authorized'] and not r['semantic_quality_verified']
    assert r['shots'][2]['review_status']=='NO_FREEZE_DETECTED'

@pytest.mark.parametrize('events',[[{'event':'end','seconds':1}],[{'event':'start','seconds':1},{'event':'start','seconds':2}],[{'event':'start','seconds':25}],[{'event':'start','seconds':float('nan')}],[{'event':'start','seconds':1},{'event':'end','seconds':0}],[{'event':'start','seconds':True}]])
def test_bad_events(events):
    with pytest.raises(ValueError):s.intervals(events,720)

@pytest.mark.parametrize('mutate',[lambda q,t,p:t['shots'][3].update(start_frame=1),lambda q,t,p:q['audit'].update(frames=721),lambda q,t,p:p.__setitem__(0,'ignore'),lambda q,t,p:q.update(publication_authorized=True),lambda q,t,p:t['shots'][0].update(samples=True)])
def test_reject_timeline(mutate):
    q,t=data();p=[s.EXPECTATIONS[0]]*24;mutate(q,t,p)
    with pytest.raises(ValueError):s.assess(q,t,p)

def config(tmp):
    def entry(name,obj):
        p=tmp/name;p.write_bytes(s.encoded(obj));return dict(path=str(p),sha256=s.sha(p.read_bytes()))
    q,t=data();x=dict(qc=entry('qc.json',q),timeline=entry('timeline.json',t),policy=[s.EXPECTATIONS[0]]*24,video_sha256=PIN)
    return entry('config.json',dict(schema='VIRALOS_REVIEW_ORCHESTRATION_V1',locales=dict(en=x,hi=x),preflight=entry('preflight.json',dict(schema='VIRALOS_PHASE14_PREFLIGHT_V1',publication_authorized=False,review_dependencies_detected=True))))

def test_resume(tmp_path):
    c=config(tmp_path);o=tmp_path/'out';a=s.run(c['path'],c['sha256'],o,'scene');assert a['stages']['en']['scene']=='created';assert not (o/'en_readiness.json').exists()
    b=s.run(c['path'],c['sha256'],o);assert b['stages']['hi']['scene']=='reused';assert b['stages']['en']['readiness']=='created';assert not json.loads((o/'en_readiness.json').read_bytes())['production_accepted']
    assert s.run(c['path'],c['sha256'],o)['stages']['en']['readiness']=='reused'

def test_tamper(tmp_path):
    c=config(tmp_path);o=tmp_path/'out';s.run(c['path'],c['sha256'],o,'scene');(o/'en_scene.json').write_text('{}')
    with pytest.raises(ValueError):s.run(c['path'],c['sha256'],o)
    assert (o/'en_scene.json').read_text()=='{}'

def test_lock(tmp_path):
    c=config(tmp_path);o=tmp_path/'out';o.mkdir();(o/'RUNNING').touch()
    with pytest.raises(FileExistsError):s.run(c['path'],c['sha256'],o)
    assert (o/'RUNNING').exists()

def test_changed_input(tmp_path):
    c=config(tmp_path);(tmp_path/'qc.json').write_text('{}')
    with pytest.raises(ValueError):s.run(c['path'],c['sha256'],tmp_path/'out')

def test_animation_bounds():
    from PIL import ImageFont
    fonts=[ImageFont.load_default(size=i) for i in (32,24,17)]
    # Use Pillow's bundled font, avoid relying on installed OS fonts in CI.
    assert m.frame(2,0,fonts).size==(960,540)
    assert m.frame(2,0,fonts).tobytes()!=m.frame(2,1,fonts).tobytes()
    with pytest.raises(ValueError):m.frame(3,0,fonts)
