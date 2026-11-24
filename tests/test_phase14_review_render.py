import json
import pytest
try:
    from tools import phase14_review_render as r
except ImportError:
    import phase14_review_render as r

@pytest.fixture
def inputs(tmp_path):
    raw=tmp_path/'raw.mp4'; raw.write_bytes(b'raw')
    master=tmp_path/'master.mp4'; master.write_bytes(b'master')
    t=tmp_path/'timeline.json'; m=tmp_path/'master.json'
    a=dict(shots=r.assembly.timeline([15*48000]*24),video_sha256=r.quality.sha(raw),plan_sha256=r.assembly.PLAN_SHA,voice_basis='synthetic eSpeak English',publication_authorized=False)
    b=dict(source_sha256=r.quality.sha(raw),output_sha256=r.quality.sha(master),numeric_gate_pass=True,publication_authorized=False)
    t.write_text(json.dumps(a)); m.write_text(json.dumps(b))
    return raw,master,t,m,a,b

def test_valid(inputs):
    raw,master,t,m,_,_=inputs
    assert r.validate_chain(raw,master,t,m)[2]==10800

@pytest.mark.parametrize('field,value', [('video_sha256','bad'),('plan_sha256','bad'),('voice_basis','owner'),('publication_authorized',True)])
def test_raw_receipt(inputs,field,value):
    raw,master,t,m,a,_=inputs; a[field]=value; t.write_text(json.dumps(a))
    with pytest.raises(ValueError): r.validate_chain(raw,master,t,m)

@pytest.mark.parametrize('field,value',[('source_sha256','bad'),('output_sha256','bad'),('numeric_gate_pass',False),('publication_authorized',True)])
def test_master_receipt(inputs,field,value):
    raw,master,t,m,_,b=inputs; b[field]=value; m.write_text(json.dumps(b))
    with pytest.raises(ValueError): r.validate_chain(raw,master,t,m)

def test_corrupt_file(inputs):
    raw,master,t,m,_,_=inputs; master.write_bytes(b'changed')
    with pytest.raises(ValueError): r.validate_chain(raw,master,t,m)

def test_warning():
    text='Dialogue: 1,0:00:00.00,0:00:01.00,Warning,,0,0,0,,SYNTHETIC TIMING TEST - NOT ALIGNED'
    assert '0:00:01.04' in r.warning_ass(text,1,31)
    with pytest.raises(ValueError): r.warning_ass('bad',1,31)
    with pytest.raises(ValueError): r.warning_ass(text+'\n'+text,1,31)
