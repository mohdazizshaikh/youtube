import json, math, struct, wave
from pathlib import Path
import pytest
try:
    from tools import phase14_owner_assembly as a, phase14_voice_runtime as v, phase14_owner_retime as r
except ImportError:
    import phase14_owner_assembly as a, phase14_voice_runtime as v, phase14_owner_retime as r

@pytest.fixture
def prepared(tmp_path):
    plan=Path(__file__).parent.parent/'tools'/'phase14_film_plan.json'
    if not plan.exists():plan=Path(__file__).with_name('phase14_film_plan.json')
    kit=tmp_path/'kit';a.b.english_request(plan,kit);m=json.loads((kit/'manifest.template.json').read_text());m.update(rights_attested=True,listening_attested=True,rights_reference='ARTIFICIAL TEST FIXTURE ONLY');chapters=[];n=144003
    pcm=b''.join(struct.pack('<h',int(4000*math.sin(2*math.pi*440*j/48000))) for j in range(n))
    for i,row in enumerate(m['chapters']):
        path=kit/'assets'/row['file']
        with wave.open(str(path),'wb') as f:f.setparams((1,2,48000,0,'NONE','not compressed'));f.writeframes(pcm)
        row['wav_sha256']=a.q.sha(path);words=len((kit/'scripts'/f'{i:02}.txt').read_text().split());chapters.append(dict(chapter=i+1,wav_sha256=row['wav_sha256'],sample_boundaries=[0,48001,96002,n],word_boundaries=[0,words//3,words*2//3,words]))
    mp=kit/'owner.json';a.b.dump(mp,m);bp=kit/'boundaries.json';a.b.dump(bp,dict(schema='VIRALOS_OWNER_SHOT_BOUNDARIES_V1',owner_manifest_sha256=a.q.sha(mp),basis='owner_reviewed_manual',boundary_review_attested=True,chapters=chapters));out=tmp_path/'retimed';r.split(plan,mp,kit/'assets',bp,a.q.sha(bp),out)
    return plan,out,a.q.sha(out/'receipt.json')

def test_exact_pcm(prepared):
    p,r,audio,texts=a.validate(*prepared);assert r['frames']==744 and len(texts)==24 and sum(len(x.split()) for x in texts)==932
    assert not r['publication_authorized']

@pytest.mark.parametrize('field,value',[('beat',2),('start_frame',1),('padding_samples',0),('word_start',1),('source_start_sample',1),('script_sha256','0'*64)])
def test_bad_row(prepared,field,value):
    p,out,_=prepared;f=out/'receipt.json';r=json.loads(f.read_text());r['shots'][0][field]=value;f.write_text(json.dumps(r));
    with pytest.raises(ValueError):a.validate(p,out,a.q.sha(f))

def test_tamper(prepared):
    p,out,pin=prepared;(out/'assets'/'00.txt').write_text('tampered');
    with pytest.raises(ValueError):a.validate(p,out,pin)

def test_tampered_assembled(prepared):
    p,out,pin=prepared;f=out/'narration.wav';x=bytearray(f.read_bytes());x[-1]=1;f.write_bytes(x);m=out/'receipt.json';r=json.loads(m.read_text());r['narration_sha256']=a.q.sha(f);m.write_text(json.dumps(r));
    with pytest.raises(ValueError,match='assembled PCM'):a.validate(p,out,a.q.sha(m))

@pytest.fixture
def runtime(tmp_path):
    m=dict(schema='VIRALOS_LOCAL_PIPER_V1',locale='hi-IN',rights_attested=True,rights_reference='TEST FILES, NOT MODEL')
    for name,content in [('executable',b'not executable'),('model',b'not ONNX'),('config',b'{"audio":{"sample_rate":22050}}')]:
        p=tmp_path/name;p.write_bytes(content);m[name]=dict(path=str(p),sha256=a.q.sha(p))
    p=tmp_path/'runtime.json';a.b.dump(p,m);return p,a.q.sha(p),m

def test_runtime_inspect(runtime):
    p,pin,m=runtime;assert v.inspect(p,pin)[2]==22050

@pytest.mark.parametrize('field,value',[('rights_attested',False),('locale','zz'),('rights_reference',''),('schema','wrong')])
def test_runtime_bad_manifest(runtime,field,value):
    p,pin,m=runtime;m[field]=value;p.write_text(json.dumps(m));
    with pytest.raises(ValueError):v.inspect(p,a.q.sha(p))

def test_model_tamper(runtime):
    p,pin,m=runtime;Path(m['model']['path']).write_bytes(b'changed')
    with pytest.raises(ValueError):v.inspect(p,pin)

def test_no_exec_on_script_mismatch(runtime,tmp_path,monkeypatch):
    p,pin,m=runtime;s=tmp_path/'script.txt';s.write_text('test');monkeypatch.setattr(v.subprocess,'run',lambda *a,**kw:pytest.fail('unexpected execution'))
    with pytest.raises(ValueError):v.synthesize(p,pin,s,'0'*64,tmp_path/'out')
