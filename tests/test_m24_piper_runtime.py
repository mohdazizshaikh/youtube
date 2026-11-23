"""Piper adapter contract tests: fake local executable; NOT real speech acceptance."""
from __future__ import annotations
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
import pytest

from app.m24_piper_runtime import preflight_piper, synthesize_piper_draft

FAKE_PIPER = '''#!/usr/bin/env python3
import sys, wave, math, struct
from pathlib import Path
args = sys.argv
output = Path(args[args.index('--output_file') + 1])
assert '--model' in args and '--config' in args
text = sys.stdin.read()
assert text.strip()
with wave.open(str(output),'wb') as wav:
    wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(22050)
    samples=(int(6500*math.sin(2*math.pi*200*i/22050)) for i in range(22050))
    wav.writeframes(struct.pack('<'+'h'*22050,*samples))
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def owner(tmp_path):
    model=tmp_path/'voice.onnx';model.write_bytes(b'owner-supplied-non-real-onnx' * 3)
    config=tmp_path/'voice.onnx.json'
    config.write_text(json.dumps({'audio':{'sample_rate':22050},'language':{'code':'en_US'}}))
    binary=tmp_path/'fake_piper'
    binary.write_text(FAKE_PIPER)
    binary.chmod(binary.stat().st_mode|stat.S_IXUSR)
    profile={'backend':'piper','locale':'en-US','model_file':str(model),'sha256':sha(model),
             'config_file':str(config),'config_sha256':sha(config),'piper_binary_sha256':sha(binary),
             'rights_attested':True,'commercial_use_allowed_per_owner':True,
             'license_reference':'Owner demo test license ref (NOT actual voice rights)'}
    return tmp_path,model,config,binary,profile


def test_piper_hash_and_language_validation(owner):
    _,model,config,binary,profile=owner
    checked=preflight_piper(profile,'en-US',binary)
    assert checked['status'].startswith('PIPER_HASHES_') and checked['naturalness_accepted'] is False
    assert checked['outbound_network_sandboxed'] is False
    with pytest.raises(ValueError,match='locale'):
        preflight_piper(profile,'hi-IN',binary)
    config.write_text(config.read_text().replace('en_US','hi_IN'))
    with pytest.raises(ValueError,match='config hash'):
        preflight_piper(profile,'en-US',binary)
    profile['config_sha256']=sha(config)
    with pytest.raises(ValueError,match='language code'):
        preflight_piper(profile,'en-US',binary)


def test_piper_rights_and_consent_fail_closed(owner):
    _,model,config,binary,profile=owner
    profile['commercial_use_allowed_per_owner']=False
    with pytest.raises(ValueError,match='commercial'):
        preflight_piper(profile,'en-US',binary)
    profile['commercial_use_allowed_per_owner']=True
    profile.update(cloned_voice=True,speaker_consent=False)
    with pytest.raises(ValueError,match='consent'):
        preflight_piper(profile,'en-US',binary)
    profile['speaker_consent']=True
    model.write_bytes(model.read_bytes()+b'TAMPER')
    with pytest.raises(ValueError,match='model hash'):
        preflight_piper(profile,'en-US',binary)


def test_piper_binary_symlink_and_tamper(owner):
    root,model,config,binary,profile=owner
    binary.write_text(binary.read_text()+'\n# MODIFIED')
    with pytest.raises(ValueError,match='binary hash'):
        preflight_piper(profile,'en-US',binary)
    link=root/'piper_link'
    try:link.symlink_to(binary)
    except OSError:pytest.skip('Symlinks unavailable')
    with pytest.raises(ValueError,match='non-symlink'):
        preflight_piper(profile,'en-US',link)


@pytest.mark.skipif(os.name == 'nt', reason='POSIX fake Piper script; Windows contract is pure validation')
def test_actual_local_process_integration_synthetic_tone_not_human_voice(owner):
    root,model,config,binary,profile=owner
    if not __import__('shutil').which('ffmpeg'):pytest.skip('FFmpeg not installed')
    output=root/'narration.wav'
    result=synthesize_piper_draft(profile,'en-US',binary,'A locally authored original short narration.',output)
    assert output.is_file()
    assert result['status']=='DRAFT_SYNTHESIZED_OWNER_LISTENING_REQUIRED'
    assert result['audio_qa']['duration_ms']==1000
    assert result['audio_qa']['sample_rate_hz']==16000
    assert result['naturalness_accepted'] is False
    assert result['can_auto_publish'] is False
    with pytest.raises(ValueError,match='overwrites'):
        synthesize_piper_draft(profile,'en-US',binary,'A new sentence.',output)


def test_piper_input_validation_no_process(owner,monkeypatch):
    root,model,config,binary,profile=owner
    def no_call(*a,**kw):pytest.fail('A prohibited input triggered a subprocess')
    monkeypatch.setattr(subprocess,'run',no_call)
    for script in ['', 'X'*651, 'No permitted ASCII \x00 in this narration']:
        with pytest.raises(ValueError):
            synthesize_piper_draft(profile,'en-US',binary,script,root/'new.wav',ffmpeg='not-called')
    profile['locale']='hi-IN';config.write_text(config.read_text().replace('en_US','hi_IN'))
    profile['config_sha256']=sha(config)
    with pytest.raises(ValueError,match='Devanagari'):
        synthesize_piper_draft(profile,'hi-IN',binary,'This is romanized only.',root/'hindi.wav',ffmpeg='not-called')


def test_piper_command_failure_and_timeout(owner,monkeypatch):
    root,model,config,binary,profile=owner
    def fail(*args,**kw):return subprocess.CompletedProcess(args,4,stdout='',stderr='internal text')
    monkeypatch.setattr(subprocess,'run',fail)
    with pytest.raises(RuntimeError,match='status 4'):
        synthesize_piper_draft(profile,'en-US',binary,'Original narration.',root/'out.wav',ffmpeg='unused')
    assert not (root/'out.wav').exists()
    def timeout(*args,**kw):raise subprocess.TimeoutExpired(args[0],kw['timeout'])
    monkeypatch.setattr(subprocess,'run',timeout)
    with pytest.raises(RuntimeError,match='timed out'):
        synthesize_piper_draft(profile,'en-US',binary,'Original narration.',root/'out.wav',ffmpeg='unused')
    assert not (root/'out.wav').exists()


def test_existing_preflight_hashes_large_models_as_a_stream(owner,monkeypatch):
    from app.m24_audio import validate_voice_profile
    _,model,config,binary,profile=owner
    result=validate_voice_profile(profile,'en-US')
    assert result['available'] is True and result['naturalness_human_accepted'] is False


@pytest.mark.skipif(os.name == 'nt', reason='POSIX lab fake executable only')
def test_operator_cli_generates_nonpublishable_voice_evidence(owner):
    import sys
    root,model,config,binary,profile=owner
    if not __import__('shutil').which('ffmpeg'):pytest.skip('FFmpeg not installed')
    src=root/'script.txt';src.write_text('An original narrated story about permitted illustrative graphics.',encoding='utf-8')
    profile_path=root/'profile.json';profile_path.write_text(json.dumps(profile),encoding='utf-8')
    report=root/'report.json';wav=root/'cli_voice.wav'
    cli=Path(__file__).resolve().parents[1]/'tools'/'m24_synthesize_piper.py'
    p=subprocess.run([sys.executable,str(cli),'--profile',str(profile_path),'--binary',str(binary),
                      '--locale','en-US','--text-file',str(src),'--output-wav',str(wav),
                      '--report',str(report)],capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    record=json.loads(report.read_text('utf-8'))
    assert record['audio_sha256']==sha(wav) and record['naturalness_accepted'] is False
    assert 'An original narrated story' not in report.read_text('utf-8')
