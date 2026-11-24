"""Hash-bound editorial task list for existing bilingual semantic films; never grants acceptance."""
import argparse, json
from pathlib import Path
try:
    from . import phase14_media_run as m, phase14_scene_review as s
except ImportError:
    import phase14_media_run as m, phase14_scene_review as s

FOCUS=(
    'Check exact input bytes and changed-character emphasis.',
    'Check fixed output length and distinguish input from digest.',
    'Check code legibility and complete reproducible digest.',
    'Check corresponding bit comparison, 125/256 example and limitations.',
    'Check trusted reference and complete download verification steps.',
    'Distinguish one-way hash from reversible encryption with the correct key.',
    'Separate byte integrity from origin/authenticity and signatures.',
    'Check actionable final checklist, pacing and recap.')

def tasks(config,expected,output):
    c=json.loads(m.raw(config,expected,128000))
    if set(c)!={'schema','locales'} or c['schema']!='VIRALOS_EDITORIAL_TASK_CONFIG_V1' or set(c['locales'])!={'en','hi'}:raise ValueError('config schema')
    result=[];sources={}
    for l in ('en','hi'):
        inp=c['locales'][l]
        if set(inp)!={'scene','handoff'}:raise ValueError('inventory')
        scene=m.obj(inp['scene']);hand=m.obj(inp['handoff']);pin=m.pin(scene['video_sha256']);frames=scene['frames'];rows=scene['shots']
        if scene.get('schema')!='VIRALOS_VARIABLE_SCENE_QC_V1' or scene.get('semantic_quality_verified') is not False or scene.get('publication_authorized') is not False or hand.get('schema')!='VIRALOS_SEMANTIC_HANDOFF_V1' or hand.get('locale')!=l or hand.get('video_sha256')!=pin or hand.get('frames')!=frames or hand.get('production_accepted') is not False or hand.get('publication_authorized') is not False:raise ValueError('review identity')
        if type(frames) is not int or not 720<=frames<=27000 or len(rows)!=24 or len(hand['chapters'])!=8:raise ValueError('timeline')
        cursor=0;total=0;flagged=0
        for i,r in enumerate(rows):
            a,z,n=r['start_frame'],r['end_frame'],r['freeze_frames']
            if any(type(v) is not int for v in (a,z,n)) or r['shot']!=i or a!=cursor or not a<z<=frames or not 0<=n<=z-a or r['expected']!='semantic_motion_expected':raise ValueError('shot evidence')
            status='UNEXPECTED_FREEZE_REVIEW' if n else 'NO_FREEZE_DETECTED'
            if r['review_status']!=status:raise ValueError('flag mismatch')
            if i%3==0 and hand['chapters'][i//3]['start_frame']!=a:raise ValueError('chapter identity')
            total+=n;flagged+=bool(n);cursor=z
            result.append(dict(id=f'{l}-{i+1:02}',locale=l,video_sha256=pin,chapter=i//3+1,shot=i,start_frame=a,end_frame=z,freeze_frames=n,freeze_fraction=round(n/(z-a),6),detector_status=status,priority='P0_MOTION_REVIEW' if n else 'P1_EDITORIAL_REVIEW',focus=FOCUS[i//3],status='OPEN',human_review_required=True))
        if cursor!=frames or total!=scene['freeze_frames'] or flagged!=scene['unexpected_freeze_shots'] or flagged!=hand['unexpected_freeze_shots'] or round(total/frames,6)!=scene['freeze_fraction'] or hand['freeze_fraction']!=scene['freeze_fraction'] or hand['review_flags']!=scene['original_review_flags']:raise ValueError('aggregate mismatch')
        sources[l]=dict(video_sha256=pin,scene_sha256=inp['scene']['sha256'],handoff_sha256=inp['handoff']['sha256'],review_flags=scene['original_review_flags'])
    result.sort(key=lambda x:(-x['freeze_fraction'],-x['freeze_frames'],x['id']))
    report=dict(schema='VIRALOS_EDITORIAL_TASKS_V1',config_sha256=expected,sources=sources,tasks=result,motion_review_count=sum(x['freeze_frames']>0 for x in result),task_count=len(result),human_review_required=True,production_accepted=False,publication_authorized=False)
    m.write_new(output,s.encoded(report));return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('config','expected','output'):p.add_argument('--'+k,required=True)
    r=tasks(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('task_count','motion_review_count','production_accepted','publication_authorized')},indent=2))
