"""All review declarations in tests are synthetic, not real listening evidence."""
import hashlib
import json
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest
from app.m24_audio import wav_audio_qa
from app.m24_voice_acceptance import evaluate_voice_review

SHA=lambda b:hashlib.sha256(b).hexdigest()


def fake_voice(path, *, freq=220, seconds=1.0):
    frames=int(16000*seconds)
    samples=(int(6000*math.sin(2*math.pi*freq*i/16000)) for i in range(frames))
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
        w.writeframes(struct.pack('<'+'h'*frames,*samples))
    return path


def draft_for(path, locale='en-US'):
    return {'status':'DRAFT_SYNTHESIZED_OWNER_LISTENING_REQUIRED','locale':locale,
            'model_sha256':SHA(b'model'),'config_sha256':SHA(b'config'),
            'binary_sha256':SHA(b'piper'),'text_sha256':SHA(b'original text'),
            'audio_sha256':SHA(path.read_bytes()),'audio_qa':wav_audio_qa(path)}


def reviews_for(language='en'):
    return [{'reviewer_id':f'Synthetic reviewer {i}', 'native_language':language,
             'listened_to_entire_audio':True,'checked_against_original_script':True,
             'checked_names_numbers_units':True,'checked_pronunciation_and_pacing':True,
             'checked_speaker_consent_and_usage_rights':True,
             'naturalness_score':5,'intelligibility_score':5,'artifact_free_score':5,
             'notes':'This is an illustrative unit test, NOT an actual human listening declaration.'}
            for i in range(2)]


def test_voice_review_bytes_and_attestations_not_certification(tmp_path):
    wav=fake_voice(tmp_path/'voice.wav')
    result=evaluate_voice_review(draft_for(wav),wav,reviews_for())
    assert result['status']=='HUMAN_LISTENING_ATTESTED_NOT_INDEPENDENTLY_VERIFIED'
    assert result['blockers']==[] and result['reviewer_count']==2
    assert not result['naturalness_independently_certified']
    assert not result['listening_actually_performed_verified_by_software']
    assert not result['youtube_upload_authorized']
    assert 'Synthetic reviewer 0' not in json.dumps(result)
    assert 'This is an illustrative' not in json.dumps(result)


def test_voice_tamper_or_wrong_provenance_blocks(tmp_path):
    wav=fake_voice(tmp_path/'original.wav');draft=draft_for(wav)
    other=fake_voice(tmp_path/'changed.wav',freq=300)
    with pytest.raises(ValueError,match='differs'):
        evaluate_voice_review(draft,other,reviews_for())
    draft['audio_qa']['audio_sha256']='0'*64
    with pytest.raises(ValueError,match='Recorded and measured'):
        evaluate_voice_review(draft,wav,reviews_for())
    draft=draft_for(wav);draft['status']='UNKNOWN'
    with pytest.raises(ValueError,match='Piper draft'):
        evaluate_voice_review(draft,wav,reviews_for())


def test_native_language_two_independent_listeners_required(tmp_path):
    wav=fake_voice(tmp_path/'hindi.wav')
    draft=draft_for(wav,'hi-IN')
    result=evaluate_voice_review(draft,wav,reviews_for('en'))
    assert result['status']=='VOICE_REVIEW_NOT_READY'
    assert any('NOT_TARGET_NATIVE_LANGUAGE' in x for x in result['blockers'])
    once=evaluate_voice_review(draft,wav,reviews_for('hi')[:1])
    assert 'AT_LEAST_TWO_DISTINCT_NATIVE_LISTENERS_REQUIRED' in once['blockers']
    duplicate=reviews_for('hi');duplicate[1]['reviewer_id']=duplicate[0]['reviewer_id'].upper()
    with pytest.raises(ValueError,match='Repeated'):
        evaluate_voice_review(draft,wav,duplicate)


def test_low_scores_flags_and_schema_fail_closed(tmp_path):
    wav=fake_voice(tmp_path/'wav.wav');draft=draft_for(wav)
    data=reviews_for();data[0]['naturalness_score']=3
    data[1]['checked_pronunciation_and_pacing']=False
    result=evaluate_voice_review(draft,wav,data)
    assert result['status']=='VOICE_REVIEW_NOT_READY'
    assert any('BELOW_4' in s for s in result['blockers'])
    assert any('NOT_ATTESTED' in s for s in result['blockers'])
    del data[0]['notes']
    with pytest.raises(ValueError,match='fields'):
        evaluate_voice_review(draft,wav,data)


def test_voice_owner_cli_no_overwrite_or_content_leak(tmp_path):
    wav=fake_voice(tmp_path/'narration.wav')
    draft=tmp_path/'draft.json';draft.write_text(json.dumps(draft_for(wav)))
    reviews=tmp_path/'reviewers.json';reviews.write_text(json.dumps(reviews_for()))
    out=tmp_path/'review-report.json'
    cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'tools'/'m24_review_voice.py'),
         '--draft-report',str(draft),'--wav',str(wav),'--reviews',str(reviews),'--output',str(out)]
    first=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
    assert first.returncode==0, first.stderr
    record=json.loads(out.read_text())
    assert record['audio_sha256']==SHA(wav.read_bytes())
    assert 'Synthetic reviewer' not in out.read_text()
    second=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
    assert second.returncode!=0
