import json
import re
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app import domain_review_queue as q, domain_draft_review as r, domain_review_web as w


@pytest.fixture
def console(tmp_path, monkeypatch):
    draft=tmp_path/'draft';draft.mkdir();assets=tmp_path/'assets';assets.mkdir()
    raw=b'local test fixture video';(draft/'draft.mp4').write_bytes(raw)
    packet={'manifest_sha256':'a'*64,'video_sha256':w.digest(raw),'domain':'sports','format':'SHORT','synthetic_demo':True,
            'scenes':[{'scene':1,'scene_sha256':'c'*64},{'scene':2,'scene_sha256':'d'*64}]}
    for mod in (q,r,w): monkeypatch.setattr(mod,'review_packet',lambda *args:packet)
    db=tmp_path/'review.sqlite';q.initialize(db)
    app=w.create_app(db,{packet['manifest_sha256']:(draft,assets)})
    with TestClient(app) as c:
        html=c.get('/')
        token=re.search(r'name="review-session" content="([0-9a-f]{64})"',html.text).group(1)
        yield c,{'X-Review-Session':token},packet,db,draft


def test_ui_and_headers(console):
    c,h,p,db,draft=console
    response=c.get('/')
    assert response.status_code==200 and 'Editorial review' in response.text
    assert response.headers['cache-control']=='no-store'
    assert response.headers['x-frame-options']=='DENY' and "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert c.get('/review.js').status_code==200 and c.get('/review.css').status_code==200
    assert c.get('/docs').status_code==404
    assert c.get('/api/drafts',headers=h).json()['drafts'][0]['state']=='UNREGISTERED'


@pytest.mark.parametrize('headers',[{}, {'X-Review-Session':'wrong'}, {'X-Review-Session':'x'*64}])
def test_session_required(console,headers):
    c,*_=console
    assert c.get('/api/drafts',headers=headers).status_code==403


@pytest.mark.parametrize('extra',[{'Host':'attacker.example'},{'Origin':'https://attacker.example'},{'Sec-Fetch-Site':'cross-site'},{'Origin':'http://testserver:1234'}])
def test_origin_guard(console,extra):
    c,h,p,db,draft=console
    assert c.post(f"/api/drafts/{p['manifest_sha256']}/register",headers=h|extra).status_code==403
    assert q.status(db)['draft_count']==0


def test_register_packet_submit_history(console):
    c,h,p,db,draft=console;url=f"/api/drafts/{p['manifest_sha256']}"
    assert c.get(url+'/packet',headers=h).status_code==409
    assert c.post(url+'/register',headers=h).status_code==200
    loaded=c.get(url+'/packet',headers=h).json();assert loaded['revision']==0
    assert not loaded['publication_eligible'] and loaded['review']==r.template(p)
    assert c.get(url+'/video',headers=h).content==(draft/'draft.mp4').read_bytes()
    review=loaded['review'];review['reviewer']='PRIVATE NAME'
    for scene in review['scenes']:
        scene['checks']=dict.fromkeys(r.CHECKS,'PASS');scene['notes']='PRIVATE NOTE'
    data={'revision':0,'review':review}
    res=c.post(url+'/submit',headers=h,json=data);assert res.status_code==200 and res.json()['state']=='DEMO_BLOCKED' and not res.json()['publication_eligible']
    assert c.post(url+'/submit',headers=h,json=data).status_code==409
    status=c.get('/api/drafts',headers=h).json()
    assert status['drafts'][0]['revision']==1 and len(status['history'])==1
    assert 'PRIVATE NAME' not in json.dumps(status) and b'PRIVATE NOTE' not in db.read_bytes()


def test_scope_and_tamper(console):
    c,h,p,db,draft=console;url=f"/api/drafts/{p['manifest_sha256']}"
    assert c.get('/api/drafts/'+'b'*64+'/video',headers=h).status_code==404
    assert c.post(url+'/register',headers=h).status_code==200
    (draft/'draft.mp4').write_bytes(b'wrong video')
    assert c.get(url+'/video',headers=h).status_code==409
    p['video_sha256']='f'*64
    assert c.get(url+'/packet',headers=h).status_code==409
    assert c.get('/api/drafts',headers=h).json()['drafts'][0]['revision']==0


def test_request_bounds_and_no_error_echo(console):
    c,h,p,db,draft=console;url=f"/api/drafts/{p['manifest_sha256']}/submit"
    assert c.post(url,headers=h,content='x').status_code==415
    assert c.post(url,headers=h|{'content-type':'application/json'},content=b'x'*(w.MAX_BODY+1)).status_code==413
    assert c.post(url,headers=h,json={'revision':True,'review':{}}).status_code==400
    assert c.post(url,headers=h,json={'revision':0,'review':{},'draft':'/private/path'}).status_code==400
    response=c.post(url,headers=h,json={'revision':0,'review':{'private':'SECRET NOTE'}})
    assert response.status_code==409 and 'SECRET NOTE' not in response.text


def test_catalog_validation(tmp_path):
    file=tmp_path/'catalog.json';item={'manifest_sha256':'a'*64,'draft':str(tmp_path/'d'),'assets':str(tmp_path/'a')}
    file.write_text(json.dumps([item]));assert len(w.load_catalog(file))==1
    for bad in ([item,item],[item|{'draft':'relative'}],[item|{'unknown':'x'}],[]):
        file.write_text(json.dumps(bad));
        with pytest.raises(ValueError):w.load_catalog(file)


def test_queue_isolation_and_startup(tmp_path):
    d=tmp_path/'d';d.mkdir();a=tmp_path/'a';a.mkdir();db=d/'queue.sqlite';q.initialize(db)
    with pytest.raises(ValueError,match='separate'):w.create_app(db,{'a'*64:(d,a)})
    with pytest.raises(ValueError):w.create_app(tmp_path/'absent.sqlite',{'a'*64:(d,a)})


def test_real_browser_api_media_audit(tmp_path):
    from app.domain_draft_video import DraftPlan,compose,digest
    from test_domain_draft_video import sample
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):pytest.skip('local FFmpeg required')
    assets=tmp_path/'assets';assets.mkdir();draft=tmp_path/'draft';compose(DraftPlan.model_validate(sample(assets)),assets,draft)
    pin=digest((draft/'manifest.json').read_bytes());db=tmp_path/'q.sqlite';q.initialize(db)
    with TestClient(w.create_app(db,{pin:(draft,assets)})) as c:
        h={'X-Review-Session':re.search(r'name="review-session" content="([0-9a-f]{64})"',c.get('/').text).group(1)}
        url=f'/api/drafts/{pin}';assert c.post(url+'/register',headers=h).status_code==200
        data=c.get(url+'/packet',headers=h).json();assert c.get(url+'/video',headers=h).content==(draft/'draft.mp4').read_bytes()
        (draft/'captions.vtt').write_text('changed',encoding='utf8')
        assert c.post(url+'/submit',headers=h,json={'revision':0,'review':data['review']}).status_code==409
        assert q.status(db)['drafts'][0]['revision']==0
