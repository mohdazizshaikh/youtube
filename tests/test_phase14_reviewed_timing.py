import copy, json, hashlib, wave
from pathlib import Path
import pytest
try:
    from tools import phase14_reviewed_timing as t, phase14_preflight as p
except ImportError:
    import phase14_reviewed_timing as t, phase14_preflight as p

class Font:
    def getlength(self,s): return len(s)*20

def fixture():
    rows=[]; texts=[]; shots=[]
    for i in range(24):
        txt='एक अक्षर';sha=hashlib.sha256(txt.encode()).hexdigest();rows.append(dict(samples=48001,start_frame=i*31,end_frame=(i+1)*31,wav_sha256='a'*64));texts.append(txt);shots.append(dict(shot=i,wav_sha256='a'*64,script_sha256=sha,words=[dict(text='एक',start_sample=0,end_sample=19200),dict(text='अक्षर',start_sample=24000,end_sample=48000)]))
    m=dict(schema='VIRALOS_REVIEWED_WORDS_V1',locale='hi-IN',source_sha256='b'*64,basis='owner_reviewed_manual',timing_review_attested=True,shots=shots)
    return rows,texts,m

def test_exact_frame_offset():
    r,s,m=fixture();out=t.compile_rows(r,s,m,'b'*64,'hi-IN',Font());assert len(out)==48;assert out[2]['start']==104;assert out[1]['end']==100;assert out[0]['group']==['एक','अक्षर'];assert out[-1]['end']<=744*100/30

@pytest.mark.parametrize('kind',['wrong_pin','wrong_locale','unreviewed','synthetic','missing_shot','wrong_shot','wrong_audio','wrong_script','missing_word','wrong_word','overlap','past_pcm','boolean','short','bad_frame'])
def test_reject(kind):
    r,s,m=fixture();a=m['shots'][0];w=a['words'][0]
    if kind=='wrong_pin':m['source_sha256']='c'*64
    elif kind=='wrong_locale':m['locale']='en-US'
    elif kind=='unreviewed':m['timing_review_attested']=False
    elif kind=='synthetic':m['basis']='synthetic_fixture'
    elif kind=='missing_shot':m['shots'].pop()
    elif kind=='wrong_shot':a['shot']=1
    elif kind=='wrong_audio':a['wav_sha256']='c'*64
    elif kind=='wrong_script':a['script_sha256']='c'*64
    elif kind=='missing_word':a['words'].pop()
    elif kind=='wrong_word':w['text']='other'
    elif kind=='overlap':a['words'][1]['start_sample']=100
    elif kind=='past_pcm':a['words'][1]['end_sample']=48002
    elif kind=='boolean':w['start_sample']=False
    elif kind=='short':w['end_sample']=100
    elif kind=='bad_frame':r[1]['start_frame']=30
    with pytest.raises(ValueError):t.compile_rows(r,s,m,'b'*64,'hi-IN',Font())

def test_english_contract():
    r,s,m=fixture();m['locale']='en-US';s[:]=['two words']*24
    for a in m['shots']:
        a['script_sha256']=hashlib.sha256(b'two words').hexdigest();a['words'][0]['text']='two';a['words'][1]['text']='words'
    assert len(t.compile_rows(r,s,m,'b'*64,'en-US',Font()))==48

def test_group_width():
    r,s,m=fixture()
    class Narrow:
        def getlength(self,s): return len(s)*300
    out=t.compile_rows(r,s,m,'b'*64,'hi-IN',Narrow());assert out[0]['group']==['एक']

def test_preflight_never_claims_acceptance(monkeypatch):
    monkeypatch.setattr(p.shutil,'which',lambda n:None)
    out=p.check();assert out['review_dependencies_detected'] is False;assert out['publication_authorized'] is False;assert out['natural_voice_runtime_verified'] is False
