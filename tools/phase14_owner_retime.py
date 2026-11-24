"""Split pinned owner chapter WAVs at explicitly reviewed sample boundaries.
No inference, rights certification, natural voice acceptance or publishing.
"""
import argparse, io, json, wave
from pathlib import Path
try:
    from . import phase14_bilingual as b, phase14_localize as loc
except ImportError:
    import phase14_bilingual as b, phase14_localize as loc

def split(plan,manifest,assets,boundaries,expected,output):
    plan,manifest,assets,boundaries=map(Path,(plan,manifest,assets,boundaries))
    raw=loc.read(manifest,100000); mp=loc.digest(raw)
    bp=loc.read(boundaries,100000)
    if loc.digest(bp)!=b.pin(expected):raise ValueError('boundary manifest hash')
    cuts=json.loads(bp)
    if cuts.get('schema')!='VIRALOS_OWNER_SHOT_BOUNDARIES_V1' or cuts.get('owner_manifest_sha256')!=mp or cuts.get('basis')!='owner_reviewed_manual' or cuts.get('boundary_review_attested') is not True:raise ValueError('reviewed boundary declarations required')
    if not isinstance(cuts.get('chapters'),list) or len(cuts['chapters'])!=8:raise ValueError('eight chapter boundaries required')
    base=b.english_intake(plan,manifest,assets)
    if loc.digest(loc.read(manifest,100000))!=mp:raise ValueError('manifest changed')
    p=json.loads(loc.read(plan,100000));staged=[];cursor=0
    for i,(c,row,rec) in enumerate(zip(p['scenes'],cuts['chapters'],base['chapters'])):
        raw=loc.read(assets/f'{i:02}.wav',9000000)
        if loc.digest(raw)!=rec['wav_sha256'] or row.get('wav_sha256')!=rec['wav_sha256'] or row.get('chapter')!=i+1:raise ValueError('chapter identity')
        pcm,n=loc.pcm(raw); samples=row.get('sample_boundaries');words=row.get('word_boundaries'); tokens=c['narration'].split()
        if not isinstance(samples,list) or not isinstance(words,list) or len(samples)!=4 or len(words)!=4 or any(type(x) is not int for x in samples+words) or samples[0]!=0 or samples[-1]!=n or words[0]!=0 or words[-1]!=len(tokens):raise ValueError('exact endpoints required')
        for j in range(3):
            a,z=samples[j:j+2];u,v=words[j:j+2];s=z-a
            if not 48000<=s<=4320000 or not 0<=u<v<=len(tokens):raise ValueError('invalid cut')
            chunk=pcm[a*2:z*2]
            if not any(chunk):raise ValueError('silent cut')
            f=(s+1599)//1600;text=' '.join(tokens[u:v]); bio=io.BytesIO()
            with wave.open(bio,'wb') as w:w.setparams((1,2,48000,0,'NONE','not compressed'));w.writeframes(chunk)
            staged.append((bio.getvalue(),chunk,text,dict(chapter=f'{i+1:02}',beat=j,start_frame=cursor,end_frame=cursor+f,samples=s,padding_samples=f*1600-s,source_wav_sha256=rec['wav_sha256'],source_start_sample=a,source_end_sample=z,word_start=u,word_end=v)))
            cursor+=f
    if not 720<=cursor<=27000:raise ValueError('duration bound')
    out=Path(output);out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch();(out/'assets').mkdir();rows=[]
    with wave.open(str(out/'narration.wav'),'wb') as w:
        w.setparams((1,2,48000,0,'NONE','not compressed'))
        for i,(wav,pcm,text,r) in enumerate(staged):
            name=f'{i:02}';(out/'assets'/f'{name}.wav').write_bytes(wav);(out/'assets'/f'{name}.txt').write_bytes(text.encode('utf8'));w.writeframes(pcm+b'\0'*(r['padding_samples']*2));rows.append(dict(r,wav_sha256=loc.digest(wav),script_sha256=loc.digest(text.encode('utf8'))))
    info=dict(schema='VIRALOS_OWNER_RETIME_V1',locale='en-US',plan_sha256=loc.PIN,owner_manifest_sha256=mp,boundaries_sha256=expected,frames=cursor,shots=rows,narration_sha256=b.q.sha(out/'narration.wav'),basis='owner_declared_manual_boundaries',acoustic_alignment_verified=False,natural_voice_verified=False,publication_authorized=False)
    b.dump(out/'receipt.json',info);(out/'INCOMPLETE').unlink();return info

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','manifest','assets','boundaries','expected','output'):p.add_argument('--'+n,required=True)
    print(json.dumps(split(**vars(p.parse_args())),indent=2))
if __name__=='__main__':main()
