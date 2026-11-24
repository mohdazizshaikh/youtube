"""Compare declared acoustic word boundaries to independently reviewed reference timestamps.
No model inference, reviewer authentication, or publication authorization.
"""
import argparse, json, math, statistics
from pathlib import Path
try:
    from . import phase14_quality as q
except ImportError:
    import phase14_quality as q


def evaluate(script,wav,reference,candidate,reference_sha,candidate_sha,synthetic=False):
    script,wav,reference,candidate=map(Path,(script,wav,reference,candidate))
    if reference.resolve()==candidate.resolve() or reference_sha==candidate_sha: raise ValueError('distinct reference and candidate evidence required')
    def load(p,pin):
        if p.is_symlink() or not p.is_file() or p.stat().st_size>2_000_000 or q.sha(p)!=pin:raise ValueError('manifest hash or size mismatch')
        return json.loads(p.read_text(encoding='utf8'))
    ref,can=load(reference,reference_sha),load(candidate,candidate_sha)
    if ref.get('locale')!=can.get('locale'): raise ValueError('locale mismatch')
    if synthetic:
        if ref.get('basis')!='synthetic_fixture' or can.get('basis')!='synthetic_fixture':raise ValueError('fixture mode requires synthetic declarations')
    else:
        if ref.get('basis')!='owner_reviewed_manual' or can.get('basis')!='owner_reviewed_ctc':raise ValueError('manual reference and CTC candidate declarations required')
        for m in (ref,can):
            if m.get('rights_attested') is not True or m.get('listening_attested') is not True or not isinstance(m.get('rights_reference'),str) or not m['rights_reference'].strip():raise ValueError('rights and listening declarations required')
        if ref.get('independent_reference_attested') is not True or not isinstance(can.get('model_sha256'),str) or len(can['model_sha256'])!=64 or any(c not in '0123456789abcdef' for c in can['model_sha256']):raise ValueError('reference independence and model identity declarations required')
    x,y=q.validate_words(script,wav,ref),q.validate_words(script,wav,can)
    if len(x)<20:raise ValueError('minimum 20 reference words required')
    errors=[abs(a[k]-b[k]) for a,b in zip(x,y) for k in ('start_ms','end_ms')]
    ordered=sorted(errors); median=statistics.median(errors);p95=ordered[math.ceil(.95*len(ordered))-1]
    if q.sha(reference)!=reference_sha or q.sha(candidate)!=candidate_sha or q.sha(wav)!=ref['wav_sha256'] or q.sha(script)!=ref['script_sha256']:raise ValueError('source changed during benchmark')
    return dict(schema='VIRALOS_ALIGNMENT_BENCHMARK_V1',locale=ref['locale'],words=len(x),boundaries=len(errors),reference_sha256=reference_sha,candidate_sha256=candidate_sha,wav_sha256=ref['wav_sha256'],median_absolute_error_ms=median,p95_absolute_error_ms=p95,max_absolute_error_ms=max(errors),numeric_threshold_pass=median<=80 and p95<=200,synthetic_fixture=synthetic,acoustic_alignment_verified=False,reviewer_identity_verified=False,publication_authorized=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('script','wav','reference','candidate','reference_sha','candidate_sha'):p.add_argument('--'+n.replace('_','-'),required=True)
    p.add_argument('--synthetic',action='store_true');print(json.dumps(evaluate(**vars(p.parse_args())),indent=2))
