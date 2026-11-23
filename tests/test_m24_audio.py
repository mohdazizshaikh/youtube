"""M2.4 real acoustic timing primitive, localization and rights regression tests."""
import io, math, struct, wave, hashlib
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.m24_audio import (ctc_viterbi, prefix_token_groups, split_words,
                           word_intervals, wav_audio_qa, validate_voice_profile)


class CharTokenizer:
    unk_token_id = 100
    def __init__(self):
        self.vocab = {c: i + 1 for i, c in enumerate('HIनमस्ते|')}
    def __call__(self, text, add_special_tokens=False):
        return {'input_ids': [self.vocab.get(c, 100) for c in text.replace(' ', '|')]}


def audio_file(tmp_path, volume=5000):
    wav = tmp_path / 'narration.wav'
    rate = 16000
    samples = [round(volume * math.sin(2 * math.pi * 330 * i / rate)) for i in range(rate)]
    with wave.open(str(wav), 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
    return wav


def synthetic_emissions(ids, blank=0):
    vocab = max([blank] + ids) + 1
    frames = [blank] * 2
    for idx in ids:
        frames.extend([idx] * 3 + [blank] * 2)
    result = []
    for token in frames:
        result.append([math.log(0.99) if i == token else math.log(0.01 / (vocab - 1)) for i in range(vocab)])
    return result


def test_true_acoustic_ctc_bilingual_hindi_and_english():
    words = split_words('HI नमस्ते')
    ids, groups = prefix_token_groups(CharTokenizer(), words, blank_id=0)
    emissions = synthetic_emissions(ids)
    spans = ctc_viterbi(emissions, ids, 0)
    assert len(spans) == len(ids)
    assert spans[0][0] == 2
    words_timed = word_intervals(words, groups, spans, 2000, len(emissions))
    assert [w['token'] for w in words_timed] == words
    assert 0 < words_timed[0]['end_ms'] <= words_timed[1]['start_ms']
    assert all(w['acoustic_score'] > .98 for w in words_timed)


def test_ctc_repeated_tokens_require_blank_and_fails_closed():
    # Two identical 'H' tokens require blank in CTC between them.
    frames = synthetic_emissions([1, 1])
    spans = ctc_viterbi(frames, [1, 1], 0)
    assert spans[0][1] < spans[1][0]
    with pytest.raises(ValueError):
        ctc_viterbi([[math.log(.1), math.log(.9)]] * 2, [1, 1], 0)
    with pytest.raises(ValueError):
        ctc_viterbi([[0.0, float('nan')]], [1], 0)


def test_m24_tokenizer_model_mismatch_and_hindi_not_truncated():
    assert split_words('हिंदी में शिक्षण') == ['हिंदी', 'में', 'शिक्षण']
    with pytest.raises(ValueError, match='unknown'):
        prefix_token_groups(CharTokenizer(), split_words('HI OTHER'), 0)
    with pytest.raises(ValueError):
        prefix_token_groups(CharTokenizer(), [''], 0)


def test_pcm_quality_flags_and_file_integrity(tmp_path):
    p = audio_file(tmp_path)
    report = wav_audio_qa(p)
    assert report['sample_rate_hz'] == 16000
    assert report['duration_ms'] == 1000
    assert report['technical_flags'] == []
    assert report['audio_sha256'] == hashlib.sha256(p.read_bytes()).hexdigest()
    silent = audio_file(tmp_path, 0)
    assert 'LOW_SIGNAL_RMS' in wav_audio_qa(silent)['technical_flags']


def test_voice_manifest_rights_and_locale_consent(tmp_path):
    model = tmp_path / 'owner-approved.onnx'
    model.write_bytes(b'model placeholder proof for sha validation')
    payload = {'locale': 'hi-IN', 'backend': 'piper', 'model_file': str(model),
               'rights_attested': True, 'license_reference': 'human local license review',
               'sha256': hashlib.sha256(model.read_bytes()).hexdigest()}
    assert validate_voice_profile(payload, 'hi-IN')['requires_sample_listening']
    with pytest.raises(ValueError, match='mismatch'):
        validate_voice_profile(payload, 'en-US')
    with pytest.raises(ValueError, match='consent'):
        validate_voice_profile({**payload, 'cloned_voice': True}, 'hi-IN')
    with pytest.raises(ValueError, match='SHA-256'):
        validate_voice_profile({**payload, 'sha256': 'wrong'}, 'hi-IN')

@pytest.fixture
def app_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main
    monkeypatch.setenv('VIRALOS_DB', str(tmp_path / 'm24.db'))
    monkeypatch.setattr(main, 'OUT', tmp_path / 'output')
    with TestClient(main.app) as client:
        yield client


def m24_project(client):
    def post(path,data):
        r=client.post(path,json=data)
        assert r.status_code==200,(path,r.status_code,r.text)
        return r.json()
    channel=post('/api/channels',{'name':'M24 localized channel','sport_id':'cricket','locale':'hi-IN',
                                  'market':'India','timezone':'Asia/Kolkata'})
    pid=post('/api/projects',{'channel_id':channel['channel_id'],'title':'Original cricket field explainer',
                             'original_angle':'Analyze local original cricket diagrams without licensed broadcast.',
                             'format':'SHORT'})['project_id']
    script=('यह मूल क्रिकेट फील्ड का विश्लेषण है। इसमें हम अपने बनाए ग्राफिक्स दिखाते हैं। '
            'यह किसी वास्तविक मैच के फुटेज का दावा नहीं है।')
    post(f'/api/projects/{pid}/script',{'text':script,'claim_links':[]})
    draft=post(f'/api/projects/{pid}/director/drafts',{'locale':'hi-IN'})
    for idx in range(len(draft['segments'])):
        data = io.BytesIO()
        with wave.open(data,'wb') as wf:
            rate=16000
            wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(rate)
            samples=[round(5000*math.sin(2*math.pi*320*i/rate)) for i in range(round(rate*1.5))]
            wf.writeframes(struct.pack('<'+'h'*len(samples),*samples))
        r=client.post(f'/api/projects/{pid}/director/drafts/{draft["draft_id"]}/voice/{idx}',
                      files={'file':('voice.wav',data.getvalue(),'audio/wav')})
        assert r.status_code==200,r.text
    plan=post(f'/api/projects/{pid}/director/drafts/{draft["draft_id"]}/assemble',{})
    return pid,plan


def test_m24_owner_review_bridge_is_project_and_voice_bound(app_client):
    from app import db
    client=app_client
    pid,assembled=m24_project(client)
    plan_id=assembled['plan_id']
    p=client.get(f'/api/projects/{pid}/studio/plan').json()['plan']
    words=[]
    for cue in p['captions']:
        tokens=cue['text'].split()
        slice_ms=(cue['end_ms']-cue['start_ms'])//len(tokens)
        for i,token in enumerate(tokens):
            start=cue['start_ms']+i*slice_ms
            words.append({'token':token,'start_ms':start,'end_ms':start+slice_ms-1,'acoustic_score':0.95})
    payload={'locale':'hi-IN','voice_audio_sha256':assembled['voice_sha256'],
             'model_directory_name':'approved-local-hindi-ctc',
             'status':'DRAFT_OWNER_REVIEW_REQUIRED','method':'OFFLINE_CTC_VITERBI_FORCED_ALIGNMENT',
             'words':words}
    endpoint=f'/api/projects/{pid}/m24/plans/{plan_id}/alignment-drafts'
    assert client.get('/api/m24/capabilities').json()['model_auto_download'] is False
    assert client.post(endpoint,json={**payload,'voice_audio_sha256':'0'*64}).status_code==409
    assert client.post(endpoint,json={**payload,'locale':'en-US'}).status_code==409
    draft=client.post(endpoint,json=payload)
    assert draft.status_code==200,draft.text
    draft_id=draft.json()['draft_id']
    assert draft.json()['state']=='PENDING_OWNER_REVIEW'
    assert client.post(endpoint,json=payload).status_code==409
    accept=f'/api/projects/{pid}/m24/alignment-drafts/{draft_id}/owner-review'
    confirmation={'owner_listened_to_full_audio':True,'owner_checked_each_word_and_timing':True,
                  'owner_checked_translation_names_numbers':True,'reviewer':'Owner'}
    assert client.post(accept,json={**confirmation,'owner_checked_each_word_and_timing':False}).status_code==422
    result=client.post(accept,json=confirmation)
    assert result.status_code==200,result.text
    assert result.json()['status']=='OWNER_REVIEWED_IMPORTED'
    assert result.json()['publish_ready'] is False
    assert client.post(accept,json=confirmation).status_code==409
    assert 'WEBVTT' in client.get(f'/api/projects/{pid}/m22/plans/{plan_id}/words.vtt').text
    with db.read() as c:
        assert db.one(c,'SELECT provenance FROM m22_word_alignments WHERE plan_id=?',(plan_id,))['provenance']=='EXTERNAL_ALIGNER_OWNER_REVIEWED'
