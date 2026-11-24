"""Pinned review-stage and audio packet identity contracts."""
import copy,json
from pathlib import Path
import pytest
try:
    from tools import phase14_media_run as m
except ImportError:
    import phase14_media_run as m
P='a'*64; S='b'*64

def receipt():
    return dict(schema='VIRALOS_SEMANTIC_FILM_REVIEW_V1',locale='en',publication_authorized=False,acoustic_alignment_verified=False,caption_basis='omitted_no_verified_alignment',audio_payload_match=True,source_video_sha256=S,frames=720,shots=[dict(chapter=f'{i//3+1:02}',beat=i%3,start_frame=i*30,end_frame=(i+1)*30,samples=48000,padding_samples=0) for i in range(24)],audit=dict(frames=720,video_sha256=P,decode_pass=True,numeric_audio_gate_pass=True))

def test_receipt():assert m.validate_receipt(receipt(),'en',P,S)==720
@pytest.mark.parametrize('mut',[lambda r:r.update(publication_authorized=True),lambda r:r.update(acoustic_alignment_verified=True),lambda r:r.update(source_video_sha256=P),lambda r:r['shots'][2].update(start_frame=1),lambda r:r['audit'].update(frames=721),lambda r:r['shots'][2].update(samples=True),lambda r:r.update(caption_basis='synthetic_fixture')])
def test_reject(mut):
    r=receipt();mut(r)
    with pytest.raises(ValueError):m.validate_receipt(r,'en',P,S)

def test_exact(tmp_path):
    p=tmp_path/'stage';assert m.exact(p,b'abc')=='created';assert m.exact(p,b'abc')=='reused'
    with pytest.raises(ValueError):m.exact(p,b'bad')
    assert p.read_bytes()==b'abc'

def test_pin(tmp_path):
    p=tmp_path/'x';p.write_bytes(b'abc')
    with pytest.raises(ValueError):m.raw(p,P)
    assert m.raw(p,m.s.sha(b'abc'))==b'abc'

def test_handoff():
    r=receipt();meta=dict(english_video_sha256=S,thumbnail_sha256={'thumbnail_en.png':P},english=dict(title='Draft',description='Review',chapters=[dict(title=str(i),start_seconds=i*3) for i in range(8)]));qc=dict(audit=dict(video_sha256=P));scene=dict(freeze_fraction=.5,unexpected_freeze_shots=1,original_review_flags=['STATIC'])
    h=m.build_handoff('en',r,meta,P,scene,qc,{},P);assert h['video_sha256']==P and h['chapters'][1]['start_frame']==90 and not h['publication_authorized']
    meta['english']['chapters'][1]['start_seconds']=4
    with pytest.raises(ValueError):m.build_handoff('en',r,meta,P,scene,qc,{},P)

def test_packet_signatures(monkeypatch):
    import types
    data=dict(streams=[dict(codec_name='aac',sample_rate='48000',channels=1,time_base='1/48000')],packets=[dict(pts=-1024,dts=-1024,duration=1024,size='50',data_hash='SHA256:'+P,side_data_list=[dict(skip_samples=1024)])])
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:types.SimpleNamespace(stdout=json.dumps(data).encode()))
    first=m.packet_signature('a');data['packets'][0]['pts']=0;assert m.packet_signature('b')!=first
    del data['packets'][0]['duration']
    with pytest.raises(ValueError):m.packet_signature('c')

def test_recovery(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();(old/'run.json').write_bytes(m.s.encoded(dict(schema='VIRALOS_MEDIA_RUN_ID_V1',config_sha256=P,publication_authorized=False)));(old/'RUNNING').write_text(P)
    for l in m.LANGS:
        (old/l).mkdir();(old/l/'video.mp4').write_bytes(b'bad')
    def fake(config,expected,output,stage):
        output.mkdir()
        for l in m.LANGS:
            (output/l).mkdir()
            for n in ('video.mp4','receipt.json','thumbnail.png','packets.json'):(output/l/n).write_bytes(b'good')
        return dict(publication_authorized=False)
    monkeypatch.setattr(m,'run',fake);res=m.recover('config',P,old,tmp_path/'new');assert res['recovery']['en/video.mp4']['prior_state']=='mismatch' and res['recovery']['hi/receipt.json']['prior_state']=='missing' and (old/'RUNNING').read_text()==P and (old/'en/video.mp4').read_bytes()==b'bad'
    with pytest.raises(ValueError):m.recover('config',P,old,old/'nested')
