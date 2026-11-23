import pytest
from fastapi.testclient import TestClient
from app.localization_review import numbers, locale_audit
import app.main as m

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('VIRALOS_DB',str(tmp_path/'locale.db'))
    monkeypatch.setattr(m,'OUT',tmp_path/'outputs')
    with TestClient(m.app) as c:yield c

def project(c):
    ch=c.post('/api/channels',json={'name':'Test English sports','sport_id':'cricket','locale':'en-US','market':'USA','timezone':'America/New_York'}).json()
    p=c.post('/api/projects',json={'channel_id':ch['channel_id'],'title':'Evidence-based original cricket explainer','original_angle':'Original line diagrams for explaining fielding patterns and captain tactics.'}).json()
    s=c.post(f'/api/projects/{p["project_id"]}/script',json={'text':'In 2026, 11 fielders played this game. The figure 35.5 is a hypothetical example of the pattern.'})
    assert s.status_code==200,s.text
    return p['project_id']

def payload():
    return {'locale':'hi-IN','localized_script':'२०२६ में, ११ फील्डरों ने इस खेल में हिस्सा लिया। ३५.५ उदाहरण है।',
            'on_screen_text':['मैदान में ११ खिलाड़ी'],
            'pronunciation':[{'written_term':'fielder','spoken_form':'फील्डर'}],
            'method':'OWNER_WRITTEN'}

def test_number_normalization_and_human_cultural_review():
    assert numbers('Year 2026; 11, 35.5')==numbers('२०२६ ११ ३५.५')
    assert 'NUMERIC_CONTENT_CHANGED_REQUIRES_DOCUMENTED_REVIEW' in locale_audit('2026, 11',payload())['flags']

def test_localization_owner_review_stale_dependency(client):
    pid=project(client)
    caps=client.get('/api/m25/capabilities').json()
    assert caps['auto_translate'] is False and caps['auto_dub_or_retime'] is False
    base=payload()
    resp=client.post(f'/api/projects/{pid}/m25/localizations',json=base)
    assert resp.status_code==200,resp.text
    vid=resp.json()['variant_id']
    assert resp.json()['status']=='PENDING_OWNER_REVIEW'
    assert client.post(f'/api/projects/{pid}/m25/localizations',json=base).status_code==409
    review={'reviewer':'Owner','owner_reviewed_entire_localized_script':True,'owner_checked_names_numbers_units':True,
            'owner_reviewed_visual_layout_typography':True,'owner_checked_pronunciation_and_audio_plan':True,
            'owner_reviewed_source_claims_and_disclosures':True}
    endpoint=f'/api/projects/{pid}/m25/localizations/{vid}/owner-review'
    assert client.post(endpoint,json={**review,'owner_checked_names_numbers_units':False}).status_code==422
    accepted=client.post(endpoint,json=review)
    assert accepted.status_code==200,accepted.text
    assert not accepted.json()['publish_ready']
    assert client.post(endpoint,json=review).status_code==409
    assert client.get(f'/api/projects/{pid}/m25/localizations/{vid}').json()['status']=='OWNER_REVIEWED'
    revision=client.post(f'/api/projects/{pid}/script',json={'text':'The script changed significantly; all localized variants must be reviewed again.'})
    assert revision.status_code==200
    assert client.get(f'/api/projects/{pid}/m25/localizations/{vid}').json()['status']=='STALE'


def test_number_drifts_controls_and_romanized_hinglish(client):
    pid=project(client)
    item=payload()
    item['localized_script']='२०२७ में ११ खिलाड़ी थे। यह एक स्थानीय उदाहरण है और संदर्भ अलग है।'
    assert client.post(f'/api/projects/{pid}/m25/localizations',json=item).status_code==422
    item['numeric_conversion_explanation']='All numbers changed in this example; human must explicitly verify every correction.'
    r=client.post(f'/api/projects/{pid}/m25/localizations',json=item)
    assert r.status_code==200,r.text
    assert 'NUMERIC_CONTENT_CHANGED_REQUIRES_DOCUMENTED_REVIEW' in r.json()['audit']['flags']
    p2=project(client)
    item2=payload();item2['localized_script']='Original 2026 mein 11 fielders khele the 35.5 units.'
    item2['on_screen_text']=['Hinglish screen caption'];item2['romanized_hinglish']=True
    assert client.post(f'/api/projects/{p2}/m25/localizations',json=item2).status_code==200


def test_direction_control_and_unknown_text_rejected(client):
    pid=project(client)
    item=payload();item['on_screen_text']=['heading\u202e text']
    assert client.post(f'/api/projects/{pid}/m25/localizations',json=item).status_code==422
