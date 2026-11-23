"""Read-only CTC alignment error scoring against owner-annotated word boundaries.

Ground truth and model provenance are not authenticated by this scoring tool.
No narration, transcript, model file or external service is accessed. Results
are diagnostic; they cannot certify natural voice quality or legal rights.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from statistics import median
from .m24_audio import SUPPORTED_LOCALES

_SHA = re.compile(r'^[0-9a-f]{64}$')
_SAMPLE_ID = re.compile(r'^[A-Za-z0-9._-]{2,100}$')
MAX_SAMPLES = 100
MAX_WORDS_PER_SAMPLE = 150
MAX_TOTAL_WORDS = 12_000
MIN_SAMPLES = 10
MIN_WORDS = 200


def _valid_words(words, duration_ms, acoustic):
    if not isinstance(words, list) or not 2 <= len(words) <= MAX_WORDS_PER_SAMPLE:
        raise ValueError('Each sample requires 2..150 words')
    last = 0
    for item in words:
        keys = {'token', 'start_ms', 'end_ms', 'acoustic_score'} if acoustic else {'token','start_ms','end_ms'}
        if not isinstance(item,dict) or set(item) != keys:
            raise ValueError('Invalid word annotation structure')
        token = item['token']
        if not isinstance(token, str) or not token.strip() or len(token)>90 or any(ord(x)<32 for x in token):
            raise ValueError('Invalid annotation token')
        start,end = item['start_ms'],item['end_ms']
        if (type(start) is not int or type(end) is not int or start < last or end <= start or end > duration_ms):
            raise ValueError('Word timestamps must be ordered, nonoverlapping and within audio')
        last = end
        if acoustic:
            score = item['acoustic_score']
            if type(score) not in (float,int) or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError('Invalid acoustic score')


def _percentile95(errors):
    values=sorted(errors)
    return values[math.ceil(0.95*len(values))-1]


def evaluate_alignment_corpus(payload: dict) -> dict:
    if not isinstance(payload,dict) or set(payload) != {'schema','locale','model_manifest_sha256','samples'}:
        raise ValueError('Invalid CTC benchmark corpus schema')
    if payload['schema'] != 'VIRALOS_CTC_BENCHMARK_V1' or payload['locale'] not in SUPPORTED_LOCALES:
        raise ValueError('Unsupported benchmark schema or locale')
    if not isinstance(payload['model_manifest_sha256'],str) or not _SHA.fullmatch(payload['model_manifest_sha256']):
        raise ValueError('Missing model provenance manifest hash')
    samples=payload['samples']
    if not isinstance(samples,list) or not 1 <= len(samples) <= MAX_SAMPLES:
        raise ValueError('Bounded 1..100 samples required')
    seen_id=set();seen_audio=set();total_words=0;errors=[];scores=[];unmatched=[]
    for sample in samples:
        if not isinstance(sample,dict) or set(sample) != {
            'sample_id','audio_sha256','duration_ms','human_reference','ctc_candidate'
        }:
            raise ValueError('Malformed sample')
        sid=sample['sample_id'];aid=sample['audio_sha256']
        if not isinstance(sid,str) or not _SAMPLE_ID.fullmatch(sid) or sid in seen_id:
            raise ValueError('Missing/duplicated/invalid sample ID')
        if not isinstance(aid,str) or not _SHA.fullmatch(aid) or aid in seen_audio:
            raise ValueError('Missing/duplicated/invalid audio hash')
        seen_id.add(sid);seen_audio.add(aid)
        duration=sample['duration_ms']
        if type(duration) is not int or not 500 <= duration <= 120000:
            raise ValueError('Audio duration outside bounded test range')
        reference=sample['human_reference'];candidate=sample['ctc_candidate']
        _valid_words(reference,duration,False)
        _valid_words(candidate,duration,True)
        total_words+=len(reference)
        if total_words>MAX_TOTAL_WORDS:
            raise ValueError('Benchmark corpus too large')
        if len(reference)!=len(candidate) or any(x['token']!=y['token'] for x,y in zip(reference,candidate)):
            unmatched.append(sid)
            continue
        for gold,pred in zip(reference,candidate):
            errors.extend((abs(gold['start_ms']-pred['start_ms']), abs(gold['end_ms']-pred['end_ms'])))
            scores.append(pred['acoustic_score'])
    eligible = len(samples)>=MIN_SAMPLES and total_words>=MIN_WORDS
    p95=_percentile95(errors) if errors else None
    med=median(errors) if errors else None
    if unmatched: state='TRANSCRIPT_MISMATCH_BLOCKED'
    elif not eligible: state='CORPUS_TOO_SMALL_FOR_THRESHOLD_REVIEW'
    elif med is not None and med<=100 and p95<=250: state='TIMING_THRESHOLDS_MET_OWNER_REVIEW_REQUIRED'
    else: state='TIMING_THRESHOLDS_NOT_MET'
    return {
        'schema':'VIRALOS_CTC_TIMING_EVALUATION_V1','status':state,'locale':payload['locale'],
        'model_manifest_sha256':payload['model_manifest_sha256'],
        'sample_count':len(samples),'reference_word_count':total_words,
        'matched_word_count':len(scores),'transcript_mismatch_count':len(unmatched),
        'mismatched_sample_ids':unmatched,'median_boundary_error_ms':med,
        'p95_boundary_error_ms':p95,'mean_acoustic_score':round(sum(scores)/len(scores),5) if scores else None,
        'thresholds':{'min_sample_count':MIN_SAMPLES,'min_reference_words':MIN_WORDS,
                      'median_boundary_error_ms_max':100,'p95_boundary_error_ms_max':250},
        'human_reference_authenticated':False,'audio_hashes_recomputed_from_wavs':False,
        'inference_executed_by_benchmark':False,'local_ctc_weights_verified_by_benchmark':False,
        'native_speaker_approval_obtained':False,'publication_or_model_release_approved':False,
        'offline_only':True,
    }
