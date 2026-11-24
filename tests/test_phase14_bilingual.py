import io,json,wave
from pathlib import Path
import pytest
try:
    from tools import phase14_bilingual as b, phase14_localize as l
except ImportError:
    import phase14_bilingual as b, phase14_localize as l
HI=Path(l.__file__).with_name('phase14_hi_plan.json')
EN=Path(l.__file__).with_name('phase14_film_plan.json')
class Font:
    def getlength(self,s):return len(s)*22

def wav(data):
    buf=io.BytesIO()
    with wave.open(buf,'wb') as w:w.setparams((1,2,48000,0,'NONE','not compressed'));w.writeframes(data)
    return buf.getvalue()

@pytest.fixture
def prep(tmp_path):
    p,pp=l.load_plan(HI);n=48001;frames=31;audio=(b'\x01\x00'*n+b'\0\0'*(frames*1600-n))*24;data=wav(audio)
    (tmp_path/'narration.wav').write_bytes(data);rows=[dict(chapter=f'{i//3+1:02}',beat=i%3,start_frame=i*frames,end_frame=(i+1)*frames,samples=n,padding_samples=frames*1600-n,wav_sha256='a'*64) for i in range(24)]
    r=dict(schema='VIRALOS_HINDI_INTAKE_V1',locale='hi-IN',basis='synthetic_espeak',publication_authorized=False,plan_sha256=pp,shots=rows,board_sha256=['b'*64]*24,frames=744,duration_seconds=744/30,narration_sha256=l.digest(data))
    return tmp_path,r

def save(folder,r):
    data=json.dumps(r).encode();(folder/'receipt.json').write_bytes(data);return l.digest(data)

def test_prepared(prep):
    folder,r=prep;_,got,_=b.prepared(HI,folder,save(folder,r));assert got['frames']==744

@pytest.mark.parametrize('mutation',[lambda r:r.update(basis='owner_reviewed_recording'),lambda r:r.update(publication_authorized=True),lambda r:r.update(plan_sha256='a'*64),lambda r:r['shots'][0].update(padding_samples=0),lambda r:r['shots'][1].update(start_frame=0),lambda r:r.update(frames=743),lambda r:r.update(duration_seconds=float('nan')),lambda r:r.update(narration_sha256='a'*64),lambda r:r['shots'].pop()])
def test_reject_prepared(prep,mutation):
    folder,r=prep;mutation(r)
    with pytest.raises(ValueError):b.prepared(HI,folder,save(folder,r))

def test_wrong_receipt_pin(prep):
    folder,r=prep;save(folder,r)
    with pytest.raises(ValueError):b.prepared(HI,folder,'b'*64)

def test_padding(prep):
    folder,r=prep;data=bytearray((folder/'narration.wav').read_bytes());data[44+48001*2]=3;(folder/'narration.wav').write_bytes(data);r['narration_sha256']=l.digest(data)
    with pytest.raises(ValueError):b.prepared(HI,folder,save(folder,r))

def test_cues():
    text='एक अक्षर बदलते ही क्या होता है';rows=b.cues(text,480000,Font());assert [r['text'] for r in rows]==text.split();assert rows[0]['start']==0 and rows[-1]['end']==1000;assert all(a['end']==c['start'] for a,c in zip(rows,rows[1:]));assert 'WORD TIMING NOT ALIGNED' in b.ass(rows,300,'FreeSans')

@pytest.mark.parametrize('text,samples',[('a {bad}',48000),('a b c',10),('x'*90,48000),('',48000)])
def test_bad_cues(text,samples):
    with pytest.raises(ValueError):b.cues(text,samples,Font())

def test_request_and_intake(tmp_path):
    d=tmp_path/'request';b.english_request(EN,d);m=json.loads((d/'manifest.template.json').read_text());assert len(m['chapters'])==8
    with pytest.raises(ValueError):b.english_intake(EN,d/'manifest.template.json',d/'assets')
    data=wav(b'\x01\0'*48000);m.update(rights_attested=True,listening_attested=True,rights_reference='fixture only')
    for row in m['chapters']:(d/'assets'/row['file']).write_bytes(data);row['wav_sha256']=l.digest(data)
    manifest=d/'manifest.json';manifest.write_text(json.dumps(m));r=b.english_intake(EN,manifest,d/'assets');assert len(r['chapters'])==8 and r['publication_authorized'] is False and r['natural_voice_verified'] is False
    m['chapters'][0]['file']='../00.wav';manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError):b.english_intake(EN,manifest,d/'assets')

def test_no_overwrite(tmp_path):
    d=tmp_path/'exists';d.mkdir()
    with pytest.raises(FileExistsError):b.english_request(EN,d)
