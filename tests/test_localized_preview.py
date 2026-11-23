"""CPU M2.5 localized video proof: human text + owner WAV, never fake TTS."""
import io
import json
import math
import shutil
import struct
import wave

import pytest
from fastapi.testclient import TestClient
import app.main as main
from app import db


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('VIRALOS_DB',str(tmp_path/'localized.db'))
    monkeypatch.setattr(main,'OUT',tmp_path/'outputs')
    with TestClient(main.app) as client:
        yield client


def wav_voice(seconds=2.8):
    buf=io.BytesIO()
    with wave.open(buf,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
        samples=[int(7000*math.sin(2*math.pi*220*i/16000)) for i in range(round(seconds*16000))]
        w.writeframes(struct.pack('<'+'h'*len(samples),*samples))
    return buf.getvalue()


def make_variant(client):
    ch=client.post('/api/channels',json={'name':'Owner original study','sport_id':'nfl',
        'locale':'en-US','market':'US','timezone':'America/New_York'}).json()['channel_id']
    pid=client.post('/api/projects',json={'channel_id':ch,'title':'An original field formation study',
        'original_angle':'Explain an invented diagram without implying authentic broadcast game footage.'}).json()['project_id']
    r=client.post(f'/api/projects/{pid}/script',json={'text':'This is a source script used as an example. The visual is not authentic match footage.'})
    assert r.status_code==200,r.text
    text='This is an owner translated narration about original diagrams. This movement is not real match footage.'
    screens=['An original field illustration','Movement is only hypothetical']
    payload={'locale':'en-IN','localized_script':text,'on_screen_text':screens,'method':'OWNER_WRITTEN'}
    v=client.post(f'/api/projects/{pid}/m25/localizations',json=payload)
    assert v.status_code==200,v.text
    vid=v.json()['variant_id']
    first='This is an owner translated narration about original diagrams.'
    second='This movement is not real match footage.'
    plan={'locale':'en-IN','locale_reviewed':True,'captions_provenance':'OWNER_TIMED',
          'shots':[{'role':'HOOK','duration_ms':1400,'headline':screens[0],
                    'visual':{'kind':'ORIGINAL_DIAGRAM','motion':'STATIC'},'overlays':[],'claim_ids':[]},
                   {'role':'PAYOFF','duration_ms':1400,'headline':screens[1],
                    'visual':{'kind':'ORIGINAL_DIAGRAM','motion':'STATIC'},'overlays':[],'claim_ids':[]}],
          'captions':[{'start_ms':0,'end_ms':1390,'text':first},
                      {'start_ms':1400,'end_ms':2790,'text':second}]}
    return pid,vid,plan


def approval(client,pid,vid):
    return client.post(f'/api/projects/{pid}/m25/localizations/{vid}/owner-review',json={
        'reviewer':'Mock owner','owner_reviewed_entire_localized_script':True,
        'owner_checked_names_numbers_units':True,'owner_reviewed_visual_layout_typography':True,
        'owner_checked_pronunciation_and_audio_plan':True,
        'owner_reviewed_source_claims_and_disclosures':True})


def send(client,pid,vid,plan,bytes_=None,rights=True):
    return client.post(f'/api/projects/{pid}/m25/localizations/{vid}/studio-preview',
        data={'plan_json':json.dumps(plan),'owner_voice_rights_attested':str(rights).lower(),
              'voice_origin':'Owner recorded in local offline studio'},
        files={'file':('owner.wav',wav_voice() if bytes_ is None else bytes_,'audio/wav')})


def test_localized_cpu_render_requires_current_owner_review_and_real_wav(client):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('Local media tools required')
    pid,vid,plan=make_variant(client)
    caps=client.get('/api/m25/localized-preview/capabilities').json()
    assert caps['automatic_dubbing_or_tts'] is False
    assert send(client,pid,vid,plan).status_code==409
    assert approval(client,pid,vid).status_code==200
    assert send(client,pid,vid,plan,rights=False).status_code==422
    assert send(client,pid,vid,plan,bytes_=b'not a wave').status_code==422
    bad=json.loads(json.dumps(plan));bad['shots'][0]['headline']='Unreviewed new claim'
    assert send(client,pid,vid,bad).status_code==409
    bad=json.loads(json.dumps(plan));bad['captions'][0]['text']='Invented unsupported captions'
    assert send(client,pid,vid,bad).status_code==409
    r=send(client,pid,vid,plan)
    assert r.status_code==200,r.text
    body=r.json()
    assert body['status']=='TECHNICAL_PREVIEW_OWNER_REVIEW_REQUIRED'
    assert not body['youtube_upload_eligible'] and not body['narration_generated_by_model']
    assert body['automated_quality']=='TECHNICAL_QC_PASSED_HUMAN_REVIEW_REQUIRED'
    url=body['download_url']
    mp4=client.get(url)
    assert mp4.status_code==200 and len(mp4.content)>15000
    with db.read() as c:
        assert db.one(c,'SELECT preview_id FROM m25_localized_previews WHERE preview_id=?',(body['preview_id'],))
    # A changed output cannot be presented as the same preview.
    with db.read() as c:
        record=db.one(c,'SELECT preview_file_relpath FROM m25_localized_previews WHERE preview_id=?',(body['preview_id'],))
    out=main.OUT/record['preview_file_relpath']
    with out.open('ab') as f:f.write(b'TAMPER')
    assert client.get(url).status_code==409


def test_localized_preview_becomes_stale_after_source_script_change(client):
    pid,vid,plan=make_variant(client)
    assert approval(client,pid,vid).status_code==200
    changed=client.post(f'/api/projects/{pid}/script',json={'text':'The newer original source script invalidates previously reviewed localizations.'})
    assert changed.status_code==200,changed.text
    assert send(client,pid,vid,plan).status_code==409


def test_hindi_latin_fallback_font_is_rejected(monkeypatch):
    import app.studio_render as render
    from app.localized_preview import require_devanagari_font
    from fastapi import HTTPException
    monkeypatch.setattr(render,'font_file',lambda locale:'/fake/DejaVuSans.ttf')
    with pytest.raises(HTTPException) as ex:
        require_devanagari_font('hi-IN')
    assert ex.value.status_code==409
    require_devanagari_font('en-IN')
