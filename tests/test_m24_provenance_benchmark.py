"""Offline model provenance and reference-based alignment metrics: no real model loads."""
from __future__ import annotations
import copy, hashlib, json, math
from pathlib import Path
import pytest
from app.m24_provenance import inspect_ctc_model
from app.m24_benchmark import evaluate_alignment_corpus


def digest(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def create_model(tmp_path:Path,locale='hi-IN'):
    root=tmp_path/'acoustic-model';root.mkdir()
    files={'config.json':b'{"model_type":"wav2vec2"}',
           'model.safetensors':b'LOCAL_FAKE_TEST_WEIGHT_NOT_A_REAL_MODEL'}
    for name,data in files.items():(root/name).write_bytes(data)
    manifest=tmp_path/'owner_model_manifest.json'
    data={'schema':'VIRALOS_LOCAL_CTC_MODEL_V1','model_id':'synthetic-unit-only',
          'locale':locale,'license_reference':'Owner-provided local review document ID 123',
          'owner_rights_review_attested':True,'commercial_use_allowed_per_owner':True,
          'files_sha256':{name:digest(blob) for name,blob in files.items()}}
    manifest.write_text(json.dumps(data),encoding='utf8')
    return root,manifest,data


def test_offline_ctc_manifest_matches_every_byte_without_models_or_network(tmp_path):
    root,m,data=create_model(tmp_path)
    result=inspect_ctc_model(root,m,'hi-IN')
    assert result['status'].startswith('LOCAL_CTC_MODEL_HASHES_VERIFIED')
    assert result['files_verified']==2 and result['inference_performed'] is False
    assert result['license_independently_verified'] is False
    assert result['remote_download_performed'] is False
    (root/'model.safetensors').write_bytes(b'CHANGED_WEIGHTS')
    with pytest.raises(ValueError,match='SHA-256 mismatch'):
        inspect_ctc_model(root,m,'hi-IN')


def test_local_model_license_locale_extra_unlisted_and_symlink_fail_closed(tmp_path):
    root,m,data=create_model(tmp_path)
    with pytest.raises(ValueError,match='locale'):
        inspect_ctc_model(root,m,'en-US')
    (root/'ignored.bin').write_bytes(b'unlisted')
    with pytest.raises(ValueError,match='Unlisted'):
        inspect_ctc_model(root,m,'hi-IN')
    (root/'ignored.bin').unlink()
    data['commercial_use_allowed_per_owner']=False
    m.write_text(json.dumps(data),encoding='utf8')
    with pytest.raises(ValueError,match='rights'):
        inspect_ctc_model(root,m,'hi-IN')
    data['commercial_use_allowed_per_owner']=True
    data['files_sha256']['../token.json']='0'*64
    m.write_text(json.dumps(data),encoding='utf8')
    with pytest.raises(ValueError,match='Unsafe'):
        inspect_ctc_model(root,m,'hi-IN')
    data['files_sha256'].pop('../token.json')
    m.write_text(json.dumps(data),encoding='utf8')
    try:
        (root/'link.json').symlink_to(tmp_path/'owner_model_manifest.json')
    except (NotImplementedError,OSError):
        pytest.skip('Symlinks not supported by local OS/user')
    with pytest.raises(ValueError,match='Symlink'):
        inspect_ctc_model(root,m,'hi-IN')


def corpus(samples=10,words=20):
    entries=[]
    for sample_no in range(samples):
        reference=[{'token':f'word{w:03d}', 'start_ms':w*200,'end_ms':w*200+165}
                   for w in range(words)]
        predicted=[{**x,'start_ms':x['start_ms']+12,'end_ms':x['end_ms']+12,
                    'acoustic_score':0.91} for x in reference]
        entries.append({'sample_id':f'sample{sample_no:03d}',
                        'audio_sha256':digest(f'fixture-{sample_no}'.encode()),
                        'duration_ms':words*200+500,
                        'human_reference':reference,'ctc_candidate':predicted})
    return {'schema':'VIRALOS_CTC_BENCHMARK_V1','locale':'hi-IN',
            'model_manifest_sha256':'f'*64,'samples':entries}


def test_benchmark_measures_real_reference_comparison_not_speech_quality():
    result=evaluate_alignment_corpus(corpus())
    assert result['status']=='TIMING_THRESHOLDS_MET_OWNER_REVIEW_REQUIRED'
    assert result['sample_count']==10 and result['reference_word_count']==200
    assert result['median_boundary_error_ms']==12
    assert result['p95_boundary_error_ms']==12
    assert not result['human_reference_authenticated']
    assert not result['audio_hashes_recomputed_from_wavs']
    assert not result['publication_or_model_release_approved']
    assert 'word000' not in str(result)


def test_benchmark_reports_small_set_bad_timing_and_transcript_mismatch():
    small=evaluate_alignment_corpus(corpus(samples=2))
    assert small['status']=='CORPUS_TOO_SMALL_FOR_THRESHOLD_REVIEW'
    bad=corpus()
    for s in bad['samples']:
        for x in s['ctc_candidate']:
            x['start_ms']+=300
            x['end_ms']+=300
        s['duration_ms']+=400
    assert evaluate_alignment_corpus(bad)['status']=='TIMING_THRESHOLDS_NOT_MET'
    bad=corpus();bad['samples'][2]['ctc_candidate'][0]['token']='unspoken'
    result=evaluate_alignment_corpus(bad)
    assert result['status']=='TRANSCRIPT_MISMATCH_BLOCKED'
    assert result['transcript_mismatch_count']==1


def test_benchmark_rejects_invalid_or_duplicate_audio_tokens_and_nan():
    data=corpus()
    data['samples'][1]['audio_sha256']=data['samples'][0]['audio_sha256']
    with pytest.raises(ValueError,match='duplicated'):
        evaluate_alignment_corpus(data)
    data=corpus();data['samples'][0]['ctc_candidate'][0]['acoustic_score']=math.nan
    with pytest.raises(ValueError,match='acoustic'):
        evaluate_alignment_corpus(data)
    data=corpus();data['samples'][0]['human_reference'][1]['start_ms']=0
    with pytest.raises(ValueError,match='nonoverlapping'):
        evaluate_alignment_corpus(data)
