"""Scene-aware freeze triage and resumable, pinned technical review reports.
No publication or semantic quality certification. Fixed report stages only.
"""
import argparse, hashlib, json, math, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

LANGS=('en','hi'); EXPECTATIONS=('intentional_static_review','semantic_motion_expected')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path,pin):
    p=Path(path)
    if not isinstance(pin,str) or not re.fullmatch('[0-9a-f]{64}',pin) or p.is_symlink() or not p.is_file():raise ValueError('pinned regular file required')
    with p.open('rb') as f:raw=f.read(2_000_001)
    if not raw or len(raw)>2_000_000 or sha(raw)!=pin:raise ValueError('input hash/size mismatch')
    obj=json.loads(raw)
    if not isinstance(obj,dict):raise ValueError('object required')
    return obj

def intervals(events,frames):
    if not isinstance(events,list) or len(events)>54000:raise ValueError('event bounds')
    start=None;prev=-1;out=[];duration=frames/30
    for e in events:
        if not isinstance(e,dict) or set(e)!={'event','seconds'}:raise ValueError('event schema')
        s=e['seconds']
        if type(s) not in (int,float) or not math.isfinite(s) or not 0<=s<=duration+1e-6 or s<prev:raise ValueError('event time/order')
        prev=s;f=min(frames,round(s*30))
        if e['event']=='start' and start is None:start=f
        elif e['event']=='end' and start is not None and f>start:out.append((start,f,False));start=None
        else:raise ValueError('unpaired freeze event')
    if start is not None:
        if start>=frames:raise ValueError('empty trailing interval')
        out.append((start,frames,True))
    return out

def assess(qc,timeline,policy):
    if qc.get('schema')!='VIRALOS_SIGNAL_QC_V1' or qc.get('publication_authorized') is not False or timeline.get('publication_authorized') is not False or qc['audit'].get('decode_pass') is not True:raise ValueError('review evidence required')
    frames=timeline['frames']; rows=timeline['shots'];video=qc['audit']['video_sha256']
    if not isinstance(video,str) or not re.fullmatch('[0-9a-f]{64}',video) or type(frames) is not int or not 720<=frames<=27000 or qc['audit']['frames']!=frames or len(rows)!=24 or not isinstance(policy,list) or len(policy)!=24 or any(x not in EXPECTATIONS for x in policy):raise ValueError('timeline/policy mismatch')
    ranges=intervals(qc['visual']['freeze_events'],frames); cursor=0;results=[]
    for i,s in enumerate(rows):
        n=s['samples']
        if type(n) is not int or not 48000<=n<=4320000:raise ValueError('sample bound')
        length=(n+1599)//1600;end=cursor+length
        if (s['chapter'],s['beat'],s['start_frame'],s['end_frame'],s['padding_samples'])!=(f'{i//3+1:02}',i%3,cursor,end,length*1600-n):raise ValueError('shot discontinuity')
        overlap=sum(max(0,min(end,z)-max(cursor,a)) for a,z,_ in ranges)
        label=('EXPECTED_STATIC_REVIEW' if policy[i]==EXPECTATIONS[0] else 'UNEXPECTED_FREEZE_REVIEW') if overlap else 'NO_FREEZE_DETECTED'
        results.append(dict(shot=i,chapter=s['chapter'],start_frame=cursor,end_frame=end,expected=policy[i],freeze_frames=overlap,review_status=label));cursor=end
    if cursor!=frames:raise ValueError('final frame mismatch')
    total=sum(x['freeze_frames'] for x in results)
    if total!=sum(z-a for a,z,_ in ranges):raise ValueError('unaccounted freeze frames')
    return dict(schema='VIRALOS_SCENE_QC_V1',video_sha256=video,frames=frames,freeze_intervals=[dict(start_frame=a,end_frame=z,closed_at_eof=eof) for a,z,eof in ranges],freeze_frames=total,freeze_fraction=round(total/frames,6),shots=results,unexpected_freeze_shots=sum(x['review_status']=='UNEXPECTED_FREEZE_REVIEW' for x in results),expected_static_review_shots=sum(x['review_status']=='EXPECTED_STATIC_REVIEW' for x in results),original_review_flags=qc['review_flags'],semantic_quality_verified=False,publication_authorized=False,human_review_required=True)

def encoded(obj):return (json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')
def store(path,obj):
    data=encoded(obj)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=len(data) or path.read_bytes()!=data:raise ValueError('existing stage differs; preserve and start new run')
        return 'reused',sha(data)
    with path.open('xb') as f:f.write(data)
    return 'created',sha(data)

def run(config,expected,output,stage='all'):
    if stage not in ('scene','all'):raise ValueError('unsupported stage')
    c=read(config,expected)
    if set(c)!={'schema','locales','preflight'} or c['schema']!='VIRALOS_REVIEW_ORCHESTRATION_V1' or set(c['locales'])!=set(LANGS):raise ValueError('config schema')
    def inp(x):
        if not isinstance(x,dict) or set(x)!={'path','sha256'}:raise ValueError('pin envelope')
        return read(x['path'],x['sha256'])
    pre=inp(c['preflight'])
    if pre.get('schema')!='VIRALOS_PHASE14_PREFLIGHT_V1' or pre.get('publication_authorized') is not False:raise ValueError('preflight schema')
    root=Path(output)
    if root.is_symlink():raise ValueError('symlink output')
    root.mkdir(exist_ok=True)
    # Explicit single-run lock. Interrupted lock requires manual inspection, not auto removal.
    lock=root/'RUNNING'
    with lock.open('xb') as f:f.write(expected.encode('ascii'))
    try:
        store(root/'run.json',dict(schema='VIRALOS_REVIEW_RUN_V1',config_sha256=expected,publication_authorized=False))
        def one(l):
            item=c['locales'][l]
            if set(item)!={'qc','timeline','policy','video_sha256'}:raise ValueError('locale schema')
            qc,t=inp(item['qc']),inp(item['timeline'])
            if qc['audit']['video_sha256']!=item['video_sha256']:raise ValueError('video identity mismatch')
            scene=assess(qc,t,item['policy']);scene.update(config_sha256=expected,locale=l,qc_sha256=item['qc']['sha256'],timeline_sha256=item['timeline']['sha256'])
            status,pin=store(root/(l+'_scene.json'),scene);result=dict(scene=status,scene_sha256=pin)
            if stage=='all':
                report=dict(schema='VIRALOS_SCENE_READINESS_V1',locale=l,video_sha256=scene['video_sha256'],config_sha256=expected,scene_sha256=pin,preflight_sha256=c['preflight']['sha256'],technical_decode_reported=qc['audit']['decode_pass'] is True,numeric_audio_reported=qc['audit']['numeric_audio_gate_pass'] is True,dependencies_reported=pre['review_dependencies_detected'] is True,expected_static_review_shots=scene['expected_static_review_shots'],unexpected_freeze_shots=scene['unexpected_freeze_shots'],required_unverified=['licensed_voice','acoustic_alignment','semantic_and_native_editorial_review','owner_windows_browser_restore','authorized_private_upload'],production_accepted=False,publication_authorized=False)
                s,h=store(root/(l+'_readiness.json'),report);result.update(readiness=s,readiness_sha256=h)
            return l,result
        with ThreadPoolExecutor(max_workers=2) as pool:results=dict(pool.map(one,LANGS))
        return dict(config_sha256=expected,stages=results,publication_authorized=False)
    finally:lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--expected',required=True);p.add_argument('--output',required=True);p.add_argument('--stage',choices=('scene','all'),default='all')
    print(json.dumps(run(**vars(p.parse_args())),indent=2))
