import copy, hashlib, json, re, sqlite3
import pytest
try:
    from tools import phase14_editorial as e, phase14_visual_polish as v, phase14_alignment_benchmark as b
except ImportError:
    import phase14_editorial as e, phase14_visual_polish as v, phase14_alignment_benchmark as b
from fastapi.testclient import TestClient


def dump(p,obj):p.write_text(json.dumps(obj),encoding='utf8');return hashlib.sha256(p.read_bytes()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

@pytest.fixture
def workspace(tmp_path,monkeypatch):
    shots=e.a.timeline([48000*16]*24); video=tmp_path/'v.mp4';video.write_bytes(b'fixture');t=tmp_path/'timeline.json';ts=dump(t,{'shots':shots,'plan_sha256':e.a.PLAN_SHA});r=tmp_path/'receipt.json';data={'status':'SYNTHETIC_PRIVATE_REVIEW_CANDIDATE','caption_basis':'synthetic_fixture','publication_authorized':False,'acoustic_alignment_verified':False,'queue_enqueued':False,'timeline_sha256':ts,'audit':{'video_sha256':sha(video)},'audio_packet_sha256':'a'*64};rs=dump(r,data)
    monkeypatch.setattr(e.a,'audit',lambda *args:{'decode_pass':True});monkeypatch.setattr(e.r,'audio_hash',lambda *args:'a'*64)
    root=tmp_path/'workspace';e.prepare(video,sha(video),r,rs,t,ts,root);return root,video,t,r,data


def test_layout():assert v.layout_ok() and v.BOARD[1]+v.BOARD[3]<=v.LANE[1] and v.LANE[1]+v.LANE[3]<=v.CAPTION[1]

def test_notes_persist_and_stale(workspace):
    root,*_=workspace;m,raw,pin=e.load(root);assert raw==b'fixture';body=dict(revision=0,frame=13,category='caption',note='Review this');assert e.append(root,pin,m['frames'],body)['revision']==1
    with pytest.raises(ValueError):e.append(root,pin,m['frames'],body)
    assert e.notes(root,pin)['notes'][0]['frame']==13 and e.notes(root,pin)['publication_authorized'] is False

@pytest.mark.parametrize('field,value',[('revision',True),('frame',-1),('frame',999999),('category','approve'),('note',''),('note','a'*1001)])
def test_bad_note(workspace,field,value):
    root,*_=workspace;m,_,pin=e.load(root);body=dict(revision=0,frame=1,category='visual',note='Fix');body[field]=value
    with pytest.raises(ValueError):e.append(root,pin,m['frames'],body)

@pytest.mark.parametrize('field,value',[('publication_authorized',True),('caption_basis','owner_reviewed_ctc'),('queue_enqueued',True),('acoustic_alignment_verified',True)])
def test_bad_receipt(workspace,field,value):
    root,video,t,r,data=workspace;data[field]=value;rs=dump(r,data)
    with pytest.raises(ValueError):e.prepare(video,sha(video),r,rs,t,sha(t),root.parent/'new')


def test_mutation(workspace):
    root,*_=workspace;(root/'review.mp4').write_bytes(b'changed')
    with pytest.raises(ValueError):e.load(root)


def test_http(workspace):
    root,*_=workspace;c=TestClient(e.create_app(root),base_url='http://127.0.0.1:8766');assert c.get('/api/meta').status_code==403
    page=c.get('/');token=re.search(r"const token='([a-f0-9]+)'",page.text)[1];h={'X-Review-Session':token};assert c.get('/api/video',headers=h).content==b'fixture'
    assert c.get('/api/meta',headers={**h,'Origin':'https://evil.example'}).status_code==403
    assert c.post('/api/notes',headers=h,json=dict(revision=0,frame=42,category='fact',note='check source')).json()['state']=='DEMO_BLOCKED'
    assert c.post('/api/notes',headers=h,json=dict(revision=0,frame=42,category='fact',note='stale')).status_code==409
    assert c.post('/api/approve',headers=h).status_code==404

@pytest.fixture
def align(tmp_path):
    import wave
    s=tmp_path/'script.txt';s.write_text(' '.join(['word']*20));w=tmp_path/'voice.wav'
    with wave.open(str(w),'wb') as f:f.setparams((1,2,8000,0,'NONE','not compressed'));f.writeframes(b'\x01\x00'*8000*6)
    ref=dict(locale='en-US',basis='synthetic_fixture',wav_sha256=sha(w),script_sha256=sha(s),words=[dict(text='word',start_ms=i*250,end_ms=i*250+150) for i in range(20)])
    r=tmp_path/'ref.json';dump(r,ref);return s,w,r,ref,tmp_path/'candidate.json'

@pytest.mark.parametrize('offset,passes',[(30,True),(100,False)])
def test_benchmark(align,offset,passes):
    s,w,r,ref,c=align;can=copy.deepcopy(ref)
    for x in can['words']:x['start_ms']+=offset;x['end_ms']+=offset
    cs=dump(c,can);out=b.evaluate(s,w,r,c,sha(r),cs,synthetic=True);assert out['numeric_threshold_pass'] is passes and out['median_absolute_error_ms']==offset and out['acoustic_alignment_verified'] is False
    with pytest.raises(ValueError):b.evaluate(s,w,r,c,sha(r),cs)


def test_benchmark_hash(align):
    s,w,r,ref,c=align;dump(c,ref)
    with pytest.raises(ValueError):b.evaluate(s,w,r,c,sha(r),'b'*64,True)
