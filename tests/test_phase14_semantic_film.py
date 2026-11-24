"""Regression contracts for bilingual semantic diagrams and report recovery."""
import copy,json
from pathlib import Path
import pytest
from PIL import ImageFont
try:
    from tools import phase14_semantic_film as f,phase14_recovery_qc as r,phase14_scene_review as s
except ImportError:
    import phase14_semantic_film as f,phase14_recovery_qc as r,phase14_scene_review as s

PIN='a'*64
@pytest.mark.parametrize('n',[30,31,339,457,2700])
def test_schedule(n):
    a=f.schedule(n);assert len(a)==12 and min(a)>0 and sum(a)==n and max(a)-min(a)<=1

def test_digest():assert len(f.BITS)==256 and f.DIFFER==125

def test_motion():
    fs={n:ImageFont.load_default(size=n) for n in (17,19,22,25,29,34,38)}
    for i in range(8):
        a=f.frame('en',i,0,0,'Title','Beat',fs);b=f.frame('en',i,0,11,'Title','Beat',fs)
        assert a.size==(960,540) and a.tobytes()!=b.tobytes()

def data():
    rows=[dict(chapter=f'{i//3+1:02}',beat=i%3,start_frame=i*30,end_frame=(i+1)*30,samples=48000,padding_samples=0) for i in range(24)]
    t=dict(frames=720,shots=rows,publication_authorized=False,video_sha256=PIN)
    q=dict(schema='VIRALOS_SIGNAL_QC_V1',publication_authorized=False,audit=dict(video_sha256=PIN,decode_pass=True,numeric_audio_gate_pass=True,frames=720),visual=dict(freeze_events=[dict(event='start',seconds=0),dict(event='end',seconds=2),dict(event='start',seconds=23)]),review_flags=['STATIC_OR_FREEZE_REVIEW'])
    return q,t

def test_shots():
    q,t=data();assert f.validate_shots(t)[1]==720;t['shots'][3]['start_frame']=1
    with pytest.raises(ValueError):f.validate_shots(t)

def test_variable():
    q,t=data();t['shots']=[dict(start_frame=0,end_frame=60),dict(start_frame=60,end_frame=690),dict(start_frame=690,end_frame=720)]
    x=r.variable(q,t,[s.EXPECTATIONS[1],s.EXPECTATIONS[0],s.EXPECTATIONS[1]])
    assert x['freeze_frames']==90 and x['unexpected_freeze_shots']==2 and x['original_review_flags']==q['review_flags'] and not x['publication_authorized']

@pytest.mark.parametrize('mut',[lambda q,t,p:t.update(video_sha256='b'*64),lambda q,t,p:t['shots'][1].update(start_frame=2),lambda q,t,p:p.pop(),lambda q,t,p:t.update(publication_authorized=True),lambda q,t,p:q['audit'].update(frames=721)])
def test_variable_reject(mut):
    q,t=data();p=[s.EXPECTATIONS[1]]*24;mut(q,t,p)
    with pytest.raises(ValueError):r.variable(q,t,p)

def config(tmp):
    def entry(n,x):
        p=tmp/n;p.write_bytes(s.encoded(x));return dict(path=str(p),sha256=s.sha(p.read_bytes()))
    q,t=data();x=dict(qc=entry('q.json',q),timeline=entry('t.json',t),policy=[s.EXPECTATIONS[0]]*24,video_sha256=PIN)
    return entry('config.json',dict(schema='VIRALOS_REVIEW_ORCHESTRATION_V1',locales=dict(en=x,hi=x),preflight=entry('pre.json',dict(schema='VIRALOS_PHASE14_PREFLIGHT_V1',publication_authorized=False,review_dependencies_detected=True))))

def test_recovery(tmp_path):
    c=config(tmp_path);src=tmp_path/'old';s.run(c['path'],c['sha256'],src,'scene');(src/'RUNNING').write_text(c['sha256']);(src/'hi_scene.json').write_text('{}');before={p.name:p.read_bytes() for p in src.iterdir()}
    out=tmp_path/'new';report=r.recover(c['path'],c['sha256'],src,out)
    assert report['stages']['en_scene.json']['state']=='EXACT_MATCH_RECOMPUTED';assert report['stages']['hi_scene.json']['state']=='MISMATCH_RECOMPUTED_REVIEW_REQUIRED';assert report['stages']['en_readiness.json']['state']=='MISSING_RECOMPUTED';assert before=={p.name:p.read_bytes() for p in src.iterdir()};assert not report['publication_authorized']
    with pytest.raises(ValueError):r.recover(c['path'],c['sha256'],src,out)

def test_bad_lock(tmp_path):
    c=config(tmp_path);src=tmp_path/'old';s.run(c['path'],c['sha256'],src,'scene');(src/'RUNNING').write_text('bad')
    with pytest.raises(ValueError):r.recover(c['path'],c['sha256'],src,tmp_path/'new')

def test_mux_keeps_all_audio_packets(monkeypatch):
    calls=[]
    monkeypatch.setattr(f.subprocess,'run',lambda cmd,**kw:calls.append((cmd,kw)))
    f.mux('visual.mp4','source.mp4','final.mp4');cmd,kw=calls[0]
    assert '-frames:v' not in cmd and '-shortest' not in cmd and '-t' not in cmd
    assert cmd[cmd.index('-c')+1]=='copy' and cmd.count('-map')==2 and kw['check'] is True
