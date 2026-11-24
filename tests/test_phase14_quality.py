import copy
import wave
import pytest
try:
    from tools import phase14_quality as q
except ImportError:
    import phase14_quality as q

@pytest.fixture
def fixture(tmp_path):
    s=tmp_path/'script.txt'; s.write_text('नमस्ते दुनिया hello world', encoding='utf-8')
    w=tmp_path/'voice.wav'
    with wave.open(str(w),'wb') as f:
        f.setparams((1,2,16000,0,'NONE','not compressed')); f.writeframes(b'\0'*64000)
    m={'locale':'hi-IN','basis':'synthetic_fixture','wav_sha256':q.sha(w),'script_sha256':q.sha(s),'words':[{'text':t,'start_ms':i*400,'end_ms':i*400+350} for i,t in enumerate(s.read_text(encoding='utf-8').split())]}
    return s,w,m

def test_captions(fixture,tmp_path):
    s,w,m=fixture; out=tmp_path/'caption'; r=q.captions(s,w,m,out)
    assert r['word_count']==4 and not r['publication_authorized'] and not r['timing_accuracy_verified']
    assert (out/'highlight.ass').read_text(encoding='utf-8').count('Dialogue:')==4
    assert not (out/'INCOMPLETE').exists()
    with pytest.raises(FileExistsError): q.captions(s,w,m,out)

@pytest.mark.parametrize('mutate',[
    lambda m:m.update(wav_sha256='wrong'),
    lambda m:m.update(script_sha256='wrong'),
    lambda m:m.update(basis='guessed'),
    lambda m:m.update(locale='unknown'),
    lambda m:m['words'][0].update(text='wrong'),
    lambda m:m['words'][1].update(start_ms=100),
    lambda m:m['words'][-1].update(end_ms=3000),
    lambda m:m['words'][0].update(start_ms=True),
    lambda m:m['words'].pop(),
])
def test_invalid(fixture,mutate):
    s,w,m=fixture; mutate(m)
    with pytest.raises(ValueError): q.validate_words(s,w,m)

def test_master_gate():
    assert q.accepted({'input_i':-16.24,'input_tp':-1.37})
    assert not q.accepted({'input_i':-17.07,'input_tp':-1.82})
    assert not q.accepted({'input_i':-16,'input_tp':-.9})

def test_master_bad_hash(fixture,tmp_path):
    _,w,_=fixture
    with pytest.raises(ValueError): q.master(w,tmp_path/'out','bad')
    assert not (tmp_path/'out').exists()
