"""Two-language artifact inspector uses synthetic audio/FFmpeg demo fixtures only."""
import copy
import hashlib
import math
import struct
import wave
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from app.m25_bilingual_delivery import evaluate_bilingual_delivery
from app.m24_voice_acceptance import evaluate_voice_review
from app.m24_audio import wav_audio_qa

SHA=lambda b:hashlib.sha256(b).hexdigest()
FFTOOLS=bool(shutil.which('ffprobe') and shutil.which('ffmpeg'))


def fake_voice(path, *, freq=220, seconds=1.0):
    frames=int(16000*seconds)
    samples=(int(6000*math.sin(2*math.pi*freq*i/16000)) for i in range(frames))
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
        w.writeframes(struct.pack('<'+'h'*frames,*samples))
    return path


def draft_for(path, locale='en-US', script='original text'):
    return {'status':'DRAFT_SYNTHESIZED_OWNER_LISTENING_REQUIRED','locale':locale,
            'model_sha256':SHA(b'model'),'config_sha256':SHA(b'config'),
            'binary_sha256':SHA(b'piper'),'text_sha256':SHA(script.encode('utf8')),
            'audio_sha256':SHA(path.read_bytes()),'audio_qa':wav_audio_qa(path)}


def reviews_for(language='en'):
    return [{'reviewer_id':f'Synthetic reviewer {i}', 'native_language':language,
             'listened_to_entire_audio':True,'checked_against_original_script':True,
             'checked_names_numbers_units':True,'checked_pronunciation_and_pacing':True,
             'checked_speaker_consent_and_usage_rights':True,
             'naturalness_score':5,'intelligibility_score':5,'artifact_free_score':5,
             'notes':'This is a synthetic unit test. No actual human reviewed this sample.'}
            for i in range(2)]


def _file(root, filename, payload):
    p=root/filename
    p.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(payload,str):p.write_text(payload,encoding='utf8')
    else:p.write_bytes(payload)
    return {'path':filename,'sha256':SHA(p.read_bytes())}


def _manifest(root):
    common={'schema':'VIRALOS_M25_BILINGUAL_DELIVERY_V1','format':'SHORT',
            'source_script_sha256':SHA(b'source-script'),
            'source_dependency_sha256':SHA(b'research-and-evidence'), 'variants':[]}
    words={'hi-IN':'यह मूल हिंदी व्याख्या केवल तकनीकी परीक्षण के लिए है।',
           'en-US':'This is original English narration for a technical test.'}
    for i,loc in enumerate(('hi-IN','en-US')):
        stem=f'{i}/{loc}'
        wav=root/stem/'voice.wav';wav.parent.mkdir(parents=True,exist_ok=True)
        fake_voice(wav,freq=200+50*i,seconds=1.25)
        text=words[loc]
        review=evaluate_voice_review(draft_for(wav,loc,text),wav,reviews_for('hi' if i==0 else 'en'))
        voice=_file(root,stem+'/voice.wav',wav.read_bytes())
        text=words[loc]
        captions=f'1\n00:00:00,000 --> 00:00:01,250\n{text}\n'
        v=root/stem/'video.mp4'
        if FFTOOLS:
            result=subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                                    '-f','lavfi','-i',f'color=c=black:s=320x240:r=24:d=1.25',
                                    '-i',str(wav),'-c:v','libx264','-pix_fmt','yuv420p',
                                    '-c:a','aac','-shortest',str(v)],capture_output=True,timeout=30)
            assert result.returncode==0,result.stderr
        else:v.write_bytes(b'FFprobe mocked in tests without FFmpeg installed'+bytes([i]))
        record={'locale':loc,'source_script_sha256':common['source_script_sha256'],
                'source_dependency_sha256':common['source_dependency_sha256'],
                'script':_file(root,stem+'/script.txt',text),
                'captions':_file(root,stem+'/caption.srt',captions),
                'voice':voice,
                'video':_file(root,stem+'/video.mp4',v.read_bytes()),
                'rights_manifest':_file(root,stem+'/rights.json',json.dumps({'owner_rights_reviewed':True,
                    'source_references':['SYNTHETIC DEMO ONLY / NOT COMMERCIAL RIGHTS']})),
                'voice_review':_file(root,stem+'/review.json',json.dumps(review)),
                'reviewer_id':f'Synthetic reviewer for {loc}',
                'review_notes':'This is a synthetic project test. It does not prove real release rights.',
                'checks':dict.fromkeys(['owner_checked_script_facts_and_names',
                  'native_speaker_checked_subtitles_and_graphics',
                  'owner_watched_full_video_and_listened',
                  'owner_checked_media_rights_and_music',
                  'owner_checked_ai_disclosures_and_originality'],True)}
        common['variants'].append(record)
    return common


@pytest.mark.skipif(not FFTOOLS, reason='Actual FFmpeg required for demonstration MP4')
def test_bilingual_technical_pair_verifies_real_local_mp4_bytes_and_owner_flags(tmp_path):
    manifest=_manifest(tmp_path)
    result=evaluate_bilingual_delivery(manifest,tmp_path)
    assert result['status']=='OFFLINE_TWO_LOCALE_FILES_VERIFIED_OWNER_REVIEW_ATTESTED'
    assert result['blockers']==[] and len(result['technical_results'])==2
    assert all('h264' in item['video_codecs'] for item in result['technical_results'])
    assert not result['publish_ready']
    assert not result['video_audio_contains_exact_reviewed_voice_proven']
    assert not result['media_rights_legally_certified']


@pytest.mark.skipif(not FFTOOLS, reason='Actual FFmpeg required for demonstration MP4')
def test_bilingual_rejects_modified_video_or_wrong_cross_locale_source(tmp_path):
    m=_manifest(tmp_path)
    (tmp_path/m['variants'][0]['video']['path']).write_bytes(b'tampered')
    with pytest.raises(ValueError,match='Modified evidence'):
        evaluate_bilingual_delivery(m,tmp_path)
    m=_manifest(tmp_path);m['variants'][1]['source_dependency_sha256']='0'*64
    with pytest.raises(ValueError,match='Mixed or stale'):
        evaluate_bilingual_delivery(m,tmp_path)


@pytest.mark.skipif(not FFTOOLS, reason='Actual FFmpeg required for demonstration MP4')
def test_bilingual_rejects_caption_mismatch_and_rights_gap(tmp_path):
    m=_manifest(tmp_path)
    x=m['variants'][0]['captions']
    x['sha256']=_file(tmp_path,x['path'],'1\n00:00:00,000 --> 00:00:01,250\nगलत कैप्शन\n')['sha256']
    with pytest.raises(ValueError,match='transcript'):
        evaluate_bilingual_delivery(m,tmp_path)
    m=_manifest(tmp_path);m['variants'][1]['checks']['owner_checked_media_rights_and_music']=False
    report=evaluate_bilingual_delivery(m,tmp_path)
    assert any('NOT_ATTESTED' in x for x in report['blockers'])
    assert report['status']=='BLOCKED' and not report['publish_ready']


def test_reject_malformed_duplicate_locale_schema_path_and_missing_ffprobe(tmp_path):
    m=_manifest(tmp_path)
    m['variants'][1]['locale']='hi-IN'
    with pytest.raises(ValueError,match='Exactly one'):
        evaluate_bilingual_delivery(m,tmp_path)
    m=_manifest(tmp_path)
    m['variants'][0]['video']={'path':'../escape.mp4','sha256':'0'*64}
    with pytest.raises(ValueError,match='Unsafe'):
        evaluate_bilingual_delivery(m,tmp_path)
    m=_manifest(tmp_path)
    with pytest.raises(ValueError,match='FFprobe'):
        evaluate_bilingual_delivery(m,tmp_path,ffprobe='missing-ffprobe-not-installed')


@pytest.mark.skipif(not FFTOOLS, reason='Actual FFmpeg required for demonstration MP4')
def test_bilingual_cli_writes_append_only_hash_bound_report(tmp_path):
    import sys
    m=_manifest(tmp_path)
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(m))
    report=tmp_path/'audit.json'
    cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'tools'/'m25_audit_bilingual_delivery.py'),
         '--manifest',str(manifest),'--evidence-root',str(tmp_path),'--report',str(report)]
    first=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
    assert first.returncode==0,first.stderr
    assert json.loads(report.read_text())['publish_ready'] is False
    repeated=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
    assert repeated.returncode!=0


@pytest.mark.skipif(not FFTOOLS, reason='Real FFmpeg required for MP4 fixture')
def test_bilingual_rejects_voice_script_mismatch(tmp_path):
    manifest = _manifest(tmp_path)
    entry = manifest['variants'][0]
    old = tmp_path / entry['voice_review']['path']
    review = json.loads(old.read_text('utf8'))
    review['text_sha256'] = SHA(b'an unrelated script')
    entry['voice_review']['sha256'] = _file(tmp_path, entry['voice_review']['path'], json.dumps(review))['sha256']
    outcome = evaluate_bilingual_delivery(manifest, tmp_path)
    assert 'hi-IN:M24_VOICE_TEXT_NOT_BOUND_TO_REVIEWED_SCRIPT' in outcome['blockers']
    assert not outcome['publish_ready']


@pytest.mark.skipif(not FFTOOLS, reason='Real FFmpeg required for MP4 fixture')
@pytest.mark.parametrize('srt', [
    '1\n00:00:00,000 --> 00:00:02,000\nEXACT\n',
    '1\n00:00:00,000 --> 00:00:01,250\nEXACT\n\n2\n00:00:00,500 --> 00:00:01,200\nCAPTIONS\n',
    '1\n00:00:00,000 --> 00:00:01,250\nEXACT\n\n2\nMALFORMED\nCAPTIONS\n',
    '1\n00:00:00,000 --> 00:00:01,250\nEXACT\n\n1\n00:00:01,250 --> 00:00:01,400\nCAPTIONS\n',
])
def test_bilingual_rejects_bad_caption_timing_or_structure(tmp_path, srt):
    manifest = _manifest(tmp_path)
    entry = manifest['variants'][0]['captions']
    entry['sha256'] = _file(tmp_path, entry['path'], srt)['sha256']
    with pytest.raises(ValueError, match='SRT'):
        evaluate_bilingual_delivery(manifest, tmp_path)
