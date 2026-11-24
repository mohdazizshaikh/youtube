import array, copy, hashlib, json, sys
import pytest
try:
    from tools import phase14_integrated_qc as q
except ImportError:
    import phase14_integrated_qc as q


def pcm(values):
    a=array.array('h',values)
    if sys.byteorder!='little':a.byteswap()
    return a.tobytes()


def test_quiet_and_clip():
    r=q.signal_metrics(pcm([0]*200+[32767,-32768]+[5000]*98),100)
    assert r['near_full_scale_samples']==2 and r['sample_peak_dbfs']==0
    assert r['quiet_intervals']==[[0.,2.]] and r['longest_quiet_seconds']==2


def test_tail_silence():
    r=q.signal_metrics(pcm([10000]*100+[0]*201),100)
    assert r['quiet_intervals']==[[1.,3.01]]


def test_short_quiet_not_flagged():
    r=q.signal_metrics(pcm([0]*199),100)
    assert r['quiet_intervals']==[] and r['sample_peak_dbfs'] is None

@pytest.mark.parametrize('raw',[b'',b'\0',b'\0'*180202])
def test_bad_pcm(raw):
    with pytest.raises(ValueError):q.signal_metrics(raw,100)


def test_visual_parse():
    v=q.visual_events('[blackdetect @ 1] black_start:1.2 black_end:1.8 black_duration:0.6\n[freezedetect @ 2] lavfi.freezedetect.freeze_start: 2.5\n[freezedetect @ 2] lavfi.freezedetect.freeze_end: 6.2')
    assert v['black_intervals']==[[1.2,1.8,.6]] and len(v['freeze_events'])==2


def receipt(locale='hi-IN'):
    schema,field={'hi-IN':('VIRALOS_HINDI_OWNER_REVIEW_V1','manifest_sha256'),'en-US':('VIRALOS_OWNER_ASSEMBLY_REVIEW_V1','retime_sha256')}[locale]
    return dict(schema=schema,locale=locale,**{field:'b'*64},frames=744,artificial_pcm_fixture=True,caption_basis='omitted_no_verified_alignment',acoustic_alignment_verified=False,publication_authorized=False,human_review_required=True,decode_pass=True,video_sha256='a'*64)

@pytest.mark.parametrize('locale',['hi-IN','en-US'])
def test_chain(locale):
    assert q.check_chain(receipt(locale),locale,'b'*64,744,True)=='a'*64

@pytest.mark.parametrize('field,value',[('frames',745),('manifest_sha256','c'*64),('artificial_pcm_fixture',False),('caption_basis','synthetic_fixture'),('publication_authorized',True),('acoustic_alignment_verified',True),('human_review_required',False),('decode_pass',False),('video_sha256','not-a-hash')])
def test_chain_reject(field,value):
    r=receipt();r[field]=value
    with pytest.raises(ValueError):q.check_chain(r,'hi-IN','b'*64,744,True)


def test_pinned_json(tmp_path):
    p=tmp_path/'r.json';p.write_text('{}');h=hashlib.sha256(p.read_bytes()).hexdigest()
    assert q.pinned_json(p,h)=={}
    p.write_text('{"altered":true}')
    with pytest.raises(ValueError):q.pinned_json(p,h)


def test_readiness_never_approves():
    s=dict(schema='VIRALOS_SIGNAL_QC_V1',publication_authorized=False,audit=dict(decode_pass=True,numeric_audio_gate_pass=True),review_flags=[])
    p=dict(schema='VIRALOS_PHASE14_PREFLIGHT_V1',publication_authorized=False,review_dependencies_detected=True)
    r=q.readiness(s,p)
    assert r['numeric_audio_reported'] and not r['production_accepted'] and not r['publication_authorized'] and len(r['required_unverified'])==5
    s['publication_authorized']=True
    with pytest.raises(ValueError):q.readiness(s,p)
