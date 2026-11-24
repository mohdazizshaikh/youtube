import json
import shutil
import subprocess
from pathlib import Path
import pytest
from app.domain_draft_video import DraftPlan, compose, digest
from app.domain_draft_audit import audit
from test_domain_draft_video import sample

pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='local FFmpeg required')

@pytest.fixture(scope='module')
def base(tmp_path_factory):
    p=tmp_path_factory.mktemp('auditbase'); assets=p/'assets';assets.mkdir()
    compose(DraftPlan.model_validate(sample(assets)),assets,p/'draft')
    return p

@pytest.fixture
def bundle(base,tmp_path):
    p=tmp_path/'bundle';shutil.copytree(base,p)
    return p/'draft',p/'assets'


def pin(d):return digest((d/'manifest.json').read_bytes())

def update(d, name=None, change=None):
    m=json.loads((d/'manifest.json').read_text())
    if name:m['files_sha256'][name]=digest((d/name).read_bytes())
    if change:change(m)
    (d/'manifest.json').write_text(json.dumps(m),encoding='utf8')


def test_actual_video_audit(bundle):
    d,a=bundle;r=audit(d,a,pin(d))
    assert r['technical_audit_passed'] and len(r['scene_checks'])==2
    assert not r['publication_eligible'] and not r['all_frames_or_words_verified']


def test_pin_required(bundle):
    d,a=bundle
    with pytest.raises(ValueError,match='pin mismatch'):audit(d,a,'0'*64)

@pytest.mark.parametrize('case',['extra','missing','caption','changed_source','timing','release_flag','wrong_wav'])
def test_fail_closed(bundle,case):
    d,a=bundle
    if case=='extra':(d/'extra.txt').write_text('unexpected')
    if case=='missing':(d/'scene_01.png').unlink()
    if case=='caption':
        (d/'captions.vtt').write_text('WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nDifferent\n');update(d,'captions.vtt')
    if case=='changed_source':(a/'voice0.wav').write_bytes(b'tamper')
    if case=='timing':update(d,change=lambda m:m['scenes'][0].update(end_ms=10))
    if case=='release_flag':update(d,change=lambda m:m.update(publication_eligible=True))
    if case=='wrong_wav':
        import wave
        with wave.open(str(d/'narration.wav'),'rb') as f:params=f.getparams();frames=f.readframes(f.getnframes())
        with wave.open(str(d/'narration.wav'),'wb') as f:f.setparams(params);f.writeframes(b'\0'*len(frames))
        update(d,'narration.wav')
    with pytest.raises(ValueError):audit(d,a,pin(d))

@pytest.mark.parametrize('kind',['audio','visual'])
def test_rehashed_wrong_actual_media(bundle,kind):
    d,a=bundle;target=d/'draft.mp4';tmp=d.parent/'new.mp4'
    if kind=='audio':
        cmd=['-i',str(target),'-f','lavfi','-i','sine=frequency=330:sample_rate=16000','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-t','1.04']
    else:
        cmd=['-f','lavfi','-i','color=c=black:s=720x1280:r=25','-i',str(target),'-map','0:v','-map','1:a','-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-c:a','copy','-t','1.04']
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y',*cmd,str(tmp)],check=True,timeout=30)
    tmp.replace(target);update(d,'draft.mp4')
    with pytest.raises(ValueError,match='acoustic mismatch' if kind=='audio' else 'visual mismatch'):audit(d,a,pin(d))
