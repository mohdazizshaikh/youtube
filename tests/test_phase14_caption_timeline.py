import copy
import json
import wave
from pathlib import Path
import pytest
try:
    from tools import phase14_caption_timeline as c, phase14_caption_fixture as f
except ImportError:
    import phase14_caption_timeline as c
    import phase14_caption_fixture as f

PLAN = Path(c.__file__).with_name('phase14_film_plan.json')

@pytest.fixture(scope='module')
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp('full_caption')
    rec = c.assembly.timeline([15*c.RATE-100]*24)
    t = root/'timeline.json'
    t.write_text(json.dumps({'shots':rec}),encoding='utf-8')
    n = root/'narration.wav'
    with wave.open(str(n),'wb') as w:
        w.setparams((1,2,c.RATE,0,'NONE','not compressed'))
        for r in rec:
            w.writeframes(b'\x01\x00'*r['samples']+b'\x00\x00'*r['padding_samples'])
    m = f.make(PLAN,t,n,root/'fixture')
    return PLAN,t,n,m,m.parent/'assets'


def test_full_timeline(bundle,tmp_path):
    r=c.compile_timeline(*bundle,tmp_path/'output')
    assert r['words']==932 and r['shots']==24 and r['frames']==10800
    assert r['pcm_assembly_match'] and not r['publication_authorized'] and not r['acoustic_alignment_verified']
    s=(tmp_path/'output/global_highlight.ass').read_text(encoding='utf-8')
    assert 'SYNTHETIC TIMING TEST - NOT ALIGNED' in s
    words=json.loads((tmp_path/'output/global_words.json').read_text(encoding='utf-8'))
    assert all(a['end_cs']<=b['start_cs'] for a,b in zip(words,words[1:]))
    assert all(len(' '.join(w['text'] for w in g))<=42 and len({w['shot'] for w in g})==1 for g in c.groups(words))
    with pytest.raises(FileExistsError): c.compile_timeline(*bundle,tmp_path/'output')

@pytest.mark.parametrize('field,value', [('locale','xx'),('basis','unverified'),('schema',2),('narration_sha256','bad'),('timeline_sha256','bad'),('plan_sha256','bad'),('shots',[])])
def test_bad_manifest(bundle,tmp_path,field,value):
    p,t,n,m,a=bundle
    d=c.load(m); d[field]=value; bad=tmp_path/'manifest.json';bad.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(ValueError): c.validate_inputs(p,t,n,bad,a)


def test_missing_rights(bundle,tmp_path):
    p,t,n,m,a=bundle
    d=c.load(m); d['basis']='owner_reviewed_ctc';bad=tmp_path/'manifest.json';bad.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(ValueError,match='rights'): c.validate_inputs(p,t,n,bad,a)


def test_reorder(bundle,tmp_path):
    p,t,n,m,a=bundle
    d=c.load(m);d['shots'][0],d['shots'][1]=d['shots'][1],d['shots'][0];bad=tmp_path/'manifest.json';bad.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(ValueError,match='order'): c.validate_inputs(p,t,n,bad,a)


def test_wrong_pcm_even_with_updated_hash(bundle,tmp_path):
    p,t,n,m,a=bundle
    bad=tmp_path/'wrong.wav';data=bytearray(n.read_bytes());data[50]^=1;bad.write_bytes(data)
    d=c.load(m);d['narration_sha256']=c.quality.sha(bad);j=tmp_path/'manifest.json';j.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(ValueError,match='assembled PCM'): c.validate_inputs(p,t,bad,j,a)


def test_bad_asset_hash(bundle,tmp_path):
    p,t,n,m,a=bundle
    d=c.load(m);d['shots'][0]['wav_sha256']='bad';j=tmp_path/'manifest.json';j.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(ValueError,match='asset hash'): c.validate_inputs(p,t,n,j,a)


def test_wrong_padding_even_with_updated_hash(bundle,tmp_path):
    p,t,n,m,a=bundle
    bad=tmp_path/'wrong.wav';data=bytearray(n.read_bytes());data[44+2*(15*c.RATE-100)]=1;bad.write_bytes(data)
    d=c.load(m);d['narration_sha256']=c.quality.sha(bad);j=tmp_path/'manifest.json';j.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(ValueError,match='padding'): c.validate_inputs(p,t,bad,j,a)

@pytest.mark.parametrize('token',['{bad}','a\\b','a<b','a\u202eb','a\x00b','x'*43])
def test_unsafe_tokens(token): assert not c.safe_token(token)


def test_hindi_and_group_breaks():
    assert c.safe_token('नमस्ते') and c.safe_token('दुनिया')
    words=[dict(shot=0,text='नमस्ते',start_cs=0,end_cs=40),dict(shot=0,text='दुनिया',start_cs=41,end_cs=60),dict(shot=1,text='ज्ञान',start_cs=61,end_cs=90)]
    assert len(list(c.groups(words)))==2
    a=c.compile_ass(words,'hi-IN','synthetic_fixture')
    assert 'Noto Sans Devanagari' in a and 'नमस्ते' in a and 'SYNTHETIC TIMING TEST' in a


def test_path_rejection(tmp_path):
    with pytest.raises(ValueError): c.safe_file(tmp_path.resolve(),'../00.wav')
