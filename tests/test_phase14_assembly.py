import copy
import json
from pathlib import Path
import pytest
try:
    from tools import phase14_assembly as a
except ImportError:
    import phase14_assembly as a

PLAN=Path(a.__file__).with_name('phase14_film_plan.json')

@pytest.fixture
def records():
    return a.timeline([16*48000+1]*24)


def test_plan_and_exact_script_coverage():
    assert a.film.sha(PLAN)==a.PLAN_SHA
    plan=json.loads(PLAN.read_text(encoding='utf-8'))
    shots=a.segments(plan)
    assert len(shots)==24
    assert sum(len(s['text'].split()) for s in shots)==932
    for i,s in enumerate(plan['scenes']):
        assert ' '.join(x['text'] for x in shots[i*3:i*3+3])==s['narration']


def test_timeline_frame_padding(records):
    assert records[0]['padding_samples']==1599
    assert records[-1]['end_frame']==24*481
    assert a.check_timeline(records)==11544
    assert all(x['end_frame']==y['start_frame'] for x,y in zip(records,records[1:]))

@pytest.mark.parametrize('mutate',[lambda r:r[1].update(start_frame=0),lambda r:r[2].update(padding_samples=0),lambda r:r[1].update(beat=2),lambda r:r[3].update(chapter='01'),lambda r:r[0].update(samples=True),lambda r:r.pop()])
def test_bad_timeline(records,mutate):
    mutate(records)
    with pytest.raises(ValueError): a.check_timeline(records)

@pytest.mark.parametrize('lengths',[[48000]*24,[90*48000]*24,[48000]*23,[48000]*23+[0]])
def test_bad_duration(lengths):
    with pytest.raises(ValueError): a.timeline(lengths)


def test_audit_hash_rejects_before_probe(tmp_path,records):
    p=tmp_path/'fake.mp4';p.write_bytes(b'not video')
    with pytest.raises(ValueError,match='hash mismatch'): a.audit(p,'0'*64,records)


def test_render_bad_plan_no_output(tmp_path):
    p=tmp_path/'plan.json';p.write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='pinned'): a.render(p,tmp_path/'out',Path('font'))
    assert not (tmp_path/'out').exists()


def test_render_no_overwrite(tmp_path):
    pytest.importorskip('PIL')
    with pytest.raises(FileExistsError): a.render(PLAN,tmp_path,Path('font'))


@pytest.mark.parametrize('mode',['extra','frames','resolution','audio','timing','nan','master'])
def test_audit_rejects_mismatched_media(tmp_path,records,monkeypatch,mode):
    from types import SimpleNamespace
    p=tmp_path/'fake.mp4';p.write_bytes(b'mock fixture');expected=a.film.sha(p)
    n=records[-1]['end_frame']; dur=str(n/30)
    v=dict(codec_type='video',codec_name='h264',width=1920,height=1080,avg_frame_rate='30/1',pix_fmt='yuv420p',nb_frames=str(n),duration=dur,start_time='0')
    au=dict(codec_type='audio',codec_name='aac',sample_rate='48000',channels=1,duration=dur,start_time='0')
    streams=[v,au]
    if mode=='extra': streams.append(dict(codec_type='subtitle'))
    if mode=='frames': v['nb_frames']=str(n-1)
    if mode=='resolution': v['width']=1280
    if mode=='audio': au['sample_rate']='44100'
    if mode=='timing': au['duration']='2'
    if mode=='nan': au['duration']='nan'
    monkeypatch.setattr(a.film,'run',lambda *args,**kwargs:SimpleNamespace(stdout=json.dumps({'streams':streams})))
    monkeypatch.setattr(a.quality,'measure',lambda p:{'input_i':-20,'input_tp':-2,'input_lra':2})
    with pytest.raises(ValueError): a.audit(p,expected,records,require_mastered=True)
