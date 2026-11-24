"""Compile declared reviewed word timing on an exact bilingual PCM timeline; never certifies alignment."""
import argparse, json, math
from pathlib import Path
try:
    from . import phase14_localize as loc, phase14_bilingual as b, phase14_owner_assembly as en
except ImportError:
    import phase14_localize as loc, phase14_bilingual as b, phase14_owner_assembly as en


def hindi_inputs(plan, manifest, assets, expected):
    raw=loc.read(manifest,100000)
    if loc.digest(raw)!=b.pin(expected): raise ValueError('manifest pin mismatch')
    p,pin,basis,pairs,mpin=loc.intake(plan,manifest,assets)
    if basis not in ('owner_reviewed_recording','owner_reviewed_local_tts') or mpin!=expected: raise ValueError('owner speech declaration required')
    texts=[t for c in p['chapters'] for t in c['segments']]
    rows=[dict(r,script_sha256=loc.digest(t.encode('utf8'))) for (_,r),t in zip(pairs,texts)]
    return p,rows,texts,pairs


def compile_rows(rows,texts,manifest,identity,locale,font):
    if not isinstance(manifest,dict) or set(manifest)!={'schema','locale','source_sha256','basis','timing_review_attested','shots'} or manifest['schema']!='VIRALOS_REVIEWED_WORDS_V1' or manifest['locale']!=locale or manifest['source_sha256']!=b.pin(identity) or manifest['basis'] not in ('owner_reviewed_manual','owner_reviewed_ctc') or manifest['timing_review_attested'] is not True: raise ValueError('reviewed timing identity required')
    shots=manifest['shots']
    if not isinstance(shots,list) or len(shots)!=len(rows) or len(rows)!=24 or len(texts)!=24: raise ValueError('24 shots required')
    output=[];last=0;cursor=0
    for i,(r,txt,s) in enumerate(zip(rows,texts,shots)):
        tokens=txt.split()
        if type(r['samples']) is not int or not 48000<=r['samples']<=4320000 or r['start_frame']!=cursor or r['end_frame']!=cursor+(r['samples']+1599)//1600:raise ValueError('source timeline mismatch')
        cursor=r['end_frame']
        if not isinstance(s,dict) or set(s)!={'shot','wav_sha256','script_sha256','words'} or type(s['shot']) is not int or s['shot']!=i or s['wav_sha256']!=b.pin(r['wav_sha256']) or s['script_sha256']!=loc.digest(txt.encode('utf8')):raise ValueError('shot pin mismatch')
        words=s['words']
        if not isinstance(words,list) or len(words)!=len(tokens):raise ValueError('exact word coverage required')
        local_end=0;checked=[]
        for t,w in zip(tokens,words):
            if not isinstance(w,dict) or set(w)!={'text','start_sample','end_sample'} or w['text']!=t or any(c in '{}\\<>' or ord(c)<32 for c in t):raise ValueError('word mismatch or unsafe token')
            a,z=w['start_sample'],w['end_sample']
            if type(a) is not int or type(z) is not int or not local_end<=a<z<=r['samples'] or z-a<1920:raise ValueError('invalid word boundaries')
            local_end=z;offset=r['start_frame']*1600
            # Round inward to avoid showing a cue before or after its declared boundary.
            start=(offset+a+479)//480;end=(offset+z)//480
            if start<last or end<=start:raise ValueError('centisecond collision')
            if font.getlength(t)>1580:raise ValueError('caption token too wide')
            checked.append(dict(shot=i,text=t,start=start,end=end));last=end
        group=[]
        def flush():
            for j,w in enumerate(group):output.append(dict(w,group=[x['text'] for x in group],active=j))
        for w in checked:
            if group and (len(group)>=4 or w['start']-group[-1]['end']>40 or font.getlength(' '.join([x['text'] for x in group]+[w['text']]))>1580):flush();group=[]
            group.append(w)
        if group:flush()
    return output


def compile_file(locale,plan,source,expected,timing,timing_sha,output,fontpath,assets=None,fixture=False):
    raw=loc.read(timing,2_000_000)
    if loc.digest(raw)!=b.pin(timing_sha):raise ValueError('timing manifest pin mismatch')
    if locale=='en-US':
        _,r,_,texts=en.validate(plan,source,expected);rows=r['shots']
    elif locale=='hi-IN':
        if assets is None:raise ValueError('Hindi source assets required')
        _,rows,texts,_=hindi_inputs(plan,source,assets,expected)
    else:raise ValueError('unsupported locale')
    font=loc.font(fontpath,55);words=compile_rows(rows,texts,json.loads(raw),expected,locale,font)
    ass=b.ass(words,rows[-1]['end_frame'],font.getname()[0]).replace('SYNTHETIC HINDI / WORD TIMING NOT ALIGNED / NO RELEASE','ARTIFICIAL TIMING FIXTURE / NO RELEASE' if fixture else 'DECLARED REVIEWED TIMING / INDEPENDENT QC PENDING / NO RELEASE')
    out=Path(output);out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch()
    (out/'review.ass').write_text(ass,encoding='utf8');b.dump(out/'words.json',words)
    result=dict(schema='VIRALOS_REVIEWED_CAPTION_COMPILE_V1',locale=locale,source_sha256=expected,timing_sha256=timing_sha,frames=rows[-1]['end_frame'],words=len(words),artificial_timing_fixture=fixture,ass_sha256=loc.digest((out/'review.ass').read_bytes()),words_sha256=loc.digest((out/'words.json').read_bytes()),acoustic_alignment_verified=False,human_review_required=True,publication_authorized=False)
    b.dump(out/'receipt.json',result);(out/'INCOMPLETE').unlink();return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('locale','plan','source','expected','timing','timing-sha','output','fontpath'):p.add_argument('--'+n,required=True)
    p.add_argument('--assets');p.add_argument('--fixture',action='store_true');print(json.dumps(compile_file(**vars(p.parse_args())),indent=2))
