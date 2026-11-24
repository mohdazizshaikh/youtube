import hashlib,json,sqlite3,wave
from pathlib import Path
import pytest
try:
    from tools import phase14_workspace as w,phase14_owner_retime as r
except ImportError:
    import phase14_workspace as w,phase14_owner_retime as r

@pytest.fixture
def demo(tmp_path):
    p=tmp_path/'workspace';p.mkdir();files={}
    for n in w.FILES:
        (p/n).write_bytes(n.encode());files[n]=w.sha(n.encode())
    m=dict(schema=w.SCHEMA,files=files,locales={l:{'frames':100,'chapters':[]} for l in w.LANGS},state='DEMO_BLOCKED',publication_authorized=False,acoustic_alignment_verified=False)
    w.dump(p/'workspace.json',m);pin=w.sha((p/'workspace.json').read_bytes())
    with sqlite3.connect(p/'notes.sqlite') as db:
        db.executescript(f'PRAGMA application_id={w.APP}; PRAGMA user_version=1; CREATE TABLE identity(pin TEXT); CREATE TABLE notes(revision INTEGER PRIMARY KEY,locale TEXT,frame INTEGER,category TEXT,note TEXT);');db.execute('INSERT INTO identity VALUES(?)',(pin,))
    return p,pin,m

def body(**kw):return dict(dict(revision=0,locale='hi',frame=30,category='caption',note='fixture'),**kw)

def test_note_restore(demo,tmp_path):
    p,pin,m=demo;assert w.append(p,pin,m,body())['revision']==1
    b=tmp_path/'backup';w.backup(p,pin,b);out=tmp_path/'restored';w.restore(b,w.sha((b/'backup.json').read_bytes()),out)
    assert w.notes(out,pin,w.load(out,pin))==w.notes(p,pin,m)
    with pytest.raises(FileExistsError):w.restore(b,w.sha((b/'backup.json').read_bytes()),out)

@pytest.mark.parametrize('kw',[{'revision':1},{'locale':'xx'},{'frame':100},{'frame':True},{'category':'approve'},{'note':''},{'note':'\x00'},{'revision':True}])
def test_invalid_note(demo,kw):
    with pytest.raises(ValueError):w.append(*demo,body(**kw))

def test_tampered_media(demo):
    p,pin,m=demo;(p/'hi.mp4').write_bytes(b'bad')
    with pytest.raises(ValueError):w.load(p,pin)

def test_tampered_backup(demo,tmp_path):
    p,pin,m=demo;b=tmp_path/'backup';w.backup(p,pin,b);h=w.sha((b/'backup.json').read_bytes());(b/'notes.sqlite').write_bytes(b'bad')
    with pytest.raises(ValueError):w.restore(b,h,tmp_path/'bad')
    assert (tmp_path/'bad'/'INCOMPLETE').exists()

def test_api(demo):
    from fastapi.testclient import TestClient
    import re
    p,pin,m=demo;c=TestClient(w.create_app(p,pin),base_url='http://127.0.0.1:8767');token=re.search("X-Review-Session':'([a-f0-9]+)'",c.get('/').text)[1];h={'X-Review-Session':token}
    assert c.get('/api/video/en').status_code==403
    assert c.get('/api/video/en',headers=h).content==b'en.mp4'
    assert c.get('/api/video/hi',headers=dict(h,Origin='http://evil.example')).status_code==403
    assert c.post('/api/notes',headers=h,json=body()).status_code==200
    assert c.post('/api/notes',headers=h,json=body()).status_code==409
    assert c.post('/api/approve',headers=h).status_code==404

@pytest.fixture
def owner(tmp_path):
    plan=Path(__file__).parent.parent/'tools'/'phase14_film_plan.json'
    if not plan.exists():plan=Path(__file__).with_name('phase14_film_plan.json')
    kit=tmp_path/'kit';r.b.english_request(plan,kit);m=json.loads((kit/'manifest.template.json').read_text());m.update(rights_attested=True,listening_attested=True,rights_reference='TEST FIXTURE ONLY');chapters=[]
    for i,row in enumerate(m['chapters']):
        p=kit/'assets'/row['file'];n=144003
        with wave.open(str(p),'wb') as f:f.setparams((1,2,48000,0,'NONE','not compressed'));f.writeframes(b'\x01\x00'*n)
        row['wav_sha256']=w.sha(p.read_bytes());words=len((kit/'scripts'/f'{i:02}.txt').read_text().split());chapters.append(dict(chapter=i+1,wav_sha256=row['wav_sha256'],sample_boundaries=[0,48001,96002,n],word_boundaries=[0,words//3,words*2//3,words]))
    mp=kit/'owner.json';w.dump(mp,m);bp=kit/'boundaries.json';d=dict(schema='VIRALOS_OWNER_SHOT_BOUNDARIES_V1',owner_manifest_sha256=w.sha(mp.read_bytes()),basis='owner_reviewed_manual',boundary_review_attested=True,chapters=chapters);w.dump(bp,d)
    return plan,mp,kit/'assets',bp,d

def test_retime(owner,tmp_path):
    p,m,a,b,d=owner;out=tmp_path/'retimed';x=r.split(p,m,a,b,w.sha(b.read_bytes()),out);assert x['frames']==744 and len(x['shots'])==24 and not x['acoustic_alignment_verified'];assert sum(s['samples'] for s in x['shots'])==8*144003
    with wave.open(str(out/'narration.wav'),'rb') as f:assert f.getnframes()==744*1600

@pytest.mark.parametrize('field,value',[('sample_boundaries',[0,48000,48000,144003]),('word_boundaries',[0,2,1,10]),('wav_sha256','0'*64)])
def test_cut_rejected(owner,tmp_path,field,value):
    p,m,a,b,d=owner;d['chapters'][0][field]=value;b.unlink();w.dump(b,d)
    with pytest.raises(ValueError):r.split(p,m,a,b,w.sha(b.read_bytes()),tmp_path/'out')
