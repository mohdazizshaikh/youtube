import hashlib
import math
import shutil
import struct
import wave
import pytest
from pydantic import ValidationError
from app.domain_draft_video import DraftPlan, compose, _read_pcm
from tools.domain_storyboard import demo_spec


def wav(path, n=8101, rate=16000):
    with wave.open(str(path),'wb') as w:
        w.setparams((1,2,rate,0,'NONE','not compressed'))
        w.writeframes(b''.join(struct.pack('<h',int(4000*math.sin(i*.12))) for i in range(n)))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample(tmp_path, fmt='SHORT'):
    return {'scenes':[{'board':demo_spec('sports',fmt).model_dump(),'narration_file':f'voice{i}.wav','narration_sha256':wav(tmp_path/f'voice{i}.wav'), 'narration_text':f'Synthetic audio cue {i}', 'rights_attested':True} for i in range(2)]}


@pytest.mark.parametrize('case',['traversal','different_format','different_domain','duplicate','rights','numeric_rights','injection','demo_mismatch'])
def test_invalid_plan(tmp_path,case):
    p=sample(tmp_path);s=p['scenes'][1]
    if case=='traversal':s['narration_file']='../voice1.wav'
    if case=='different_format':s['board']['format']='LONG'
    if case=='different_domain':s['board']=demo_spec('science','SHORT').model_dump()
    if case=='duplicate':s['narration_file']='voice0.wav'
    if case=='rights':s['rights_attested']=False
    if case=='numeric_rights':s['rights_attested']=1
    if case=='injection':s['narration_text']='cue --> injection'
    if case=='demo_mismatch':s['board']['synthetic_demo']=False
    with pytest.raises(ValidationError):DraftPlan.model_validate(p)


def test_pcm_padding(tmp_path):
    s=DraftPlan.model_validate(sample(tmp_path)).scenes[0]
    pcm,frames=_read_pcm(tmp_path,s)
    assert frames==13 and len(pcm)==13*640*2 and pcm[-2:]==b'\0\0'


def test_tamper_fails_before_output(tmp_path):
    p=DraftPlan.model_validate(sample(tmp_path));(tmp_path/'voice1.wav').write_bytes(b'invalid')
    with pytest.raises(ValueError):compose(p,tmp_path,tmp_path/'output')
    assert not (tmp_path/'output').exists()


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='local FFmpeg required')
@pytest.mark.parametrize('fmt',['SHORT','LONG'])
def test_real_multi_scene_render(tmp_path,fmt):
    raw=sample(tmp_path,fmt);raw['scenes'][0]['narration_text']='Review <draft> & sources';p=DraftPlan.model_validate(raw);out=tmp_path/'output';r=compose(p,tmp_path,out)
    assert r['frames']==26 and r['duration_ms']==1040 and r['stream_qc_passed']
    assert r['scenes'][0]['end_ms']==r['scenes'][1]['start_ms']==520
    assert not r['publication_eligible'] and not r['caption_word_alignment_verified']
    for name,h in r['files_sha256'].items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==h
    assert '00:00:00.520 --> 00:00:01.040' in (out/'captions.vtt').read_text()
    assert 'Review &lt;draft&gt; &amp; sources' in (out/'captions.vtt').read_text()
    with pytest.raises(FileExistsError):compose(p,tmp_path,out)


def test_non_pcm_rejected(tmp_path):
    p=sample(tmp_path);p['scenes'][1]['narration_sha256']=wav(tmp_path/'voice1.wav',rate=8000)
    with pytest.raises(ValueError,match='PCM16'):compose(DraftPlan.model_validate(p),tmp_path,tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_invalid_render_cleanup(tmp_path,monkeypatch):
    import app.domain_draft_video as d
    plan=DraftPlan.model_validate(sample(tmp_path));out=tmp_path/'output'
    monkeypatch.setattr(d.shutil,'which',lambda name:name)
    def fail(*args,**kwargs):raise RuntimeError('fixture failure')
    monkeypatch.setattr(d,'render_board',fail)
    with pytest.raises(RuntimeError,match='fixture failure'):compose(plan,tmp_path,out)
    assert not out.exists()
