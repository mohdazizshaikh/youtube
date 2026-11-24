import copy, io, json, wave
from pathlib import Path
import pytest
try:
    from tools import phase14_localize as l, phase14_packaging as p
except ImportError:
    import phase14_localize as l, phase14_packaging as p
PLAN=Path(l.__file__).with_name('phase14_hi_plan.json')
def make_wav(n=48001,rate=48000,silent=False):
    buf=io.BytesIO()
    with wave.open(buf,'wb') as w:
        w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes((b'\0\0' if silent else b'\x01\x00')*n)
    return buf.getvalue()
@pytest.fixture
def assets(tmp_path):
    plan,pin=l.load_plan(PLAN); base=tmp_path/'assets';base.mkdir(); data=make_wav();shots=[]
    for i,t in enumerate(s for c in plan['chapters'] for s in c['segments']):
        name=f'{i:02}.wav';(base/name).write_bytes(data);shots.append(dict(file=name,script_sha256=l.digest(t.encode('utf8')),wav_sha256=l.digest(data)))
    m=dict(schema=1,locale='hi-IN',basis='synthetic_espeak',plan_sha256=pin,shots=shots)
    path=tmp_path/'manifest.json';path.write_text(json.dumps(m));return path,base,m

def test_exact_pcm_retime(assets):
    path,base,m=assets;_,_,basis,shots,_=l.intake(PLAN,path,base)
    assert basis=='synthetic_espeak' and len(shots)==24 and shots[0][1]['padding_samples']==1599 and shots[-1][1]['end_frame']==744
@pytest.mark.parametrize('mutator', [lambda m:m.update(locale='en-US'),lambda m:m.update(plan_sha256='x'),lambda m:m.update(basis='owner_reviewed_recording'),lambda m:m['shots'].pop(),lambda m:m['shots'][0].update(file='../00.wav'),lambda m:m['shots'][0].update(script_sha256='x'),lambda m:m['shots'][0].update(wav_sha256='x')])
def test_manifest_reject(assets,mutator):
    path,base,m=assets;mutator(m);path.write_text(json.dumps(m))
    with pytest.raises(ValueError):l.intake(PLAN,path,base)
@pytest.mark.parametrize('data',[make_wav(rate=16000),make_wav(n=100),make_wav(silent=True),make_wav()[:-2]])
def test_bad_pcm(data):
    with pytest.raises(ValueError):l.pcm(data)

def test_owner_declarations_not_certification(assets):
    path,base,m=assets;m.update(basis='owner_reviewed_local_tts',rights_attested=True,listening_attested=True,rights_reference='local record');path.write_text(json.dumps(m));assert l.intake(PLAN,path,base)[2]=='owner_reviewed_local_tts'
def test_tampered_wav(assets):
    path,base,m=assets;(base/'00.wav').write_bytes(make_wav(n=48002))
    with pytest.raises(ValueError):l.intake(PLAN,path,base)
def test_kit_fail_closed(tmp_path):
    out=tmp_path/'request';r=l.request(PLAN,out);assert r['ready_for_intake'] is False and len(list((out/'scripts').glob('*.txt')))==24
    with pytest.raises(ValueError):l.intake(PLAN,out/'manifest.template.json',out/'assets')
    with pytest.raises(FileExistsError):l.request(PLAN,out)
def test_hash_visual():
    assert len(p.bits())==256 and sum(p.bits())==125

def test_packaging_bad_pin(tmp_path):
    v=tmp_path/'v.mp4';v.write_bytes(b'fake');r=tmp_path/'receipt';r.write_text('{}');t=tmp_path/'timeline';t.write_text('{}');out=tmp_path/'out'
    with pytest.raises(ValueError):p.build(PLAN,v,r,t,out,'missing','missing')
    assert not out.exists()
def test_plan_order(tmp_path):
    p,_=l.load_plan(PLAN);p['chapters'][0]['id']='02';path=tmp_path/'plan';path.write_text(json.dumps(p));
    with pytest.raises(ValueError):l.load_plan(path)
