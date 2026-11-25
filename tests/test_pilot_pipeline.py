import json
import shutil
import wave
import math
import struct
from pathlib import Path
import pytest
from tools import pilot_pipeline as p
from tools.domain_storyboard import demo_spec
from app.domain_draft_video import digest
from app.domain_review_queue import status


def inputs(tmp_path):
    assets=tmp_path/'inputs'; assets.mkdir()
    scenes=[]
    for i in range(2):
        name=f'voice{i}.wav'
        with wave.open(str(assets/name),'wb') as w:
            w.setparams((1,2,16000,0,'NONE','not compressed'))
            w.writeframes(b''.join(struct.pack('<h',int(4000*math.sin(j*.12))) for j in range(8101)))
        scenes.append({'board':demo_spec('technology','SHORT').model_dump(),'narration_file':name,'narration_sha256':digest((assets/name).read_bytes()),'narration_text':'Synthetic technical example.','rights_attested':True})
    plan=tmp_path/'plan.json';plan.write_text(json.dumps({'scenes':scenes}));return plan,assets


def test_private_output(tmp_path):
    with pytest.raises(ValueError): p.private_output(p.ROOT/'new')
    with pytest.raises(ValueError): p.private_output(tmp_path)
    with pytest.raises(ValueError): p.private_output(tmp_path/'new',(tmp_path,))
    assert p.private_output(tmp_path/'new')==tmp_path/'new'


def test_bad_input_no_output(tmp_path):
    plan,assets=inputs(tmp_path); (assets/'voice0.wav').write_bytes(b'bad')
    with pytest.raises(ValueError):p.build(plan,assets,tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='local media tools required')
def test_pipeline(tmp_path):
    plan,assets=inputs(tmp_path);out=tmp_path/'out';r=p.build(plan,assets,out)
    assert r['technical_audit_passed'] and r['review_pending'] and not r['publication_eligible']
    assert not (out/'INCOMPLETE').exists()
    assert status(out/'reviews.sqlite')['counts']['PENDING']==1
    assert digest((out/'draft'/'draft.mp4').read_bytes())==r['video_sha256']
    with pytest.raises(ValueError):p.build(plan,assets,out)


def test_failed_render_marked_incomplete(tmp_path,monkeypatch):
    plan,assets=inputs(tmp_path)
    def fail(*args):raise RuntimeError('render failure')
    monkeypatch.setattr(p,'compose',fail)
    with pytest.raises(RuntimeError):p.build(plan,assets,tmp_path/'out')
    assert (tmp_path/'out'/'INCOMPLETE').exists() and not (tmp_path/'out'/'run.json').exists()


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='local media tools required')
def test_real_cpu_pilot_snapshot_roundtrip(tmp_path):
    from tools.pilot_run_verify import verify
    from tools.pilot_snapshot import backup, restore
    plan, assets = inputs(tmp_path)
    run = tmp_path/'run'
    r = p.build(plan, assets, run)
    pin = r['manifest_sha256']
    assert verify(run, pin, fresh=True)['fresh_media_audit']
    snap = tmp_path/'snapshot'
    saved = backup(run, snap, pin)
    result = restore(snap, tmp_path/'restored', saved['snapshot_sha256'], pin)
    assert result['fresh_media_audit'] and not result['publication_eligible']
    assert verify(tmp_path/'restored', pin, fresh=True)['queue_state'] == 'PENDING'
