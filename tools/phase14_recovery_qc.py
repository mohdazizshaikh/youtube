"""Variable shot review and non-destructive recovery of interrupted report runs."""
import argparse, json, re
from pathlib import Path
try:
    from . import phase14_scene_review as s
except ImportError:
    import phase14_scene_review as s


def variable(qc,timeline,policy):
    if qc.get('schema')!='VIRALOS_SIGNAL_QC_V1' or qc.get('publication_authorized') is not False or timeline.get('publication_authorized') is not False or qc['audit'].get('decode_pass') is not True:raise ValueError('review evidence required')
    frames=timeline['frames'];rows=timeline['shots'];pin=qc['audit']['video_sha256']
    if not isinstance(pin,str) or not re.fullmatch('[0-9a-f]{64}',pin) or type(frames) is not int or not 30<=frames<=27000 or qc['audit']['frames']!=frames or not isinstance(rows,list) or not 1<=len(rows)<=240 or not isinstance(policy,list) or len(policy)!=len(rows) or any(x not in s.EXPECTATIONS for x in policy):raise ValueError('timeline/policy mismatch')
    if timeline.get('video_sha256')!=pin:raise ValueError('explicit video identity required')
    ranges=s.intervals(qc['visual']['freeze_events'],frames);cursor=0;results=[]
    for i,row in enumerate(rows):
        a,z=row['start_frame'],row['end_frame']
        if type(a) is not int or type(z) is not int or a!=cursor or not a<z<=frames:raise ValueError('shot continuity')
        overlap=sum(max(0,min(z,y)-max(a,x)) for x,y,_ in ranges)
        status=('EXPECTED_STATIC_REVIEW' if policy[i]==s.EXPECTATIONS[0] else 'UNEXPECTED_FREEZE_REVIEW') if overlap else 'NO_FREEZE_DETECTED'
        results.append(dict(shot=i,start_frame=a,end_frame=z,freeze_frames=overlap,expected=policy[i],review_status=status));cursor=z
    total=sum(x['freeze_frames'] for x in results)
    if cursor!=frames or total!=sum(z-a for a,z,_ in ranges):raise ValueError('frame accounting')
    return dict(schema='VIRALOS_VARIABLE_SCENE_QC_V1',video_sha256=pin,frames=frames,shots=results,freeze_frames=total,freeze_fraction=round(total/frames,6),freeze_intervals=[dict(start_frame=a,end_frame=z,closed_at_eof=eof) for a,z,eof in ranges],unexpected_freeze_shots=sum(x['review_status']=='UNEXPECTED_FREEZE_REVIEW' for x in results),expected_static_review_shots=sum(x['review_status']=='EXPECTED_STATIC_REVIEW' for x in results),original_review_flags=qc['review_flags'],semantic_quality_verified=False,human_review_required=True,publication_authorized=False)


def recover(config,expected,source,output):
    """Recompute in a new location. Compare only known report files, preserve source lock/bytes."""
    source=Path(source);out=Path(output)
    if source.is_symlink() or not source.is_dir() or out.exists() or out.is_symlink() or out.resolve().is_relative_to(source.resolve()):raise ValueError('new separate output required')
    if source.resolve().is_relative_to(out.resolve()):raise ValueError('separate directory required')
    # Require matching run identity even when stale lock exists; never unlock old location.
    run=source/'run.json';identity=dict(schema='VIRALOS_REVIEW_RUN_V1',config_sha256=expected,publication_authorized=False)
    if run.is_symlink() or not run.is_file() or run.stat().st_size!=len(s.encoded(identity)) or run.read_bytes()!=s.encoded(identity):raise ValueError('source run identity mismatch')
    lock=source/'RUNNING'
    if lock.is_symlink():raise ValueError('unsafe source lock')
    lock_present=lock.exists()
    if lock_present and (not lock.is_file() or lock.stat().st_size!=64 or lock.read_bytes()!=expected.encode('ascii')):raise ValueError('source lock mismatch')
    out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch()
    new=out/'recomputed';r=s.run(config,expected,new,'all');status={}
    for name in ('en_scene.json','hi_scene.json','en_readiness.json','hi_readiness.json'):
        old=source/name;fresh=new/name
        if old.is_symlink():raise ValueError('unsafe source stage')
        if not old.exists():state='MISSING_RECOMPUTED'
        elif not old.is_file():raise ValueError('unsafe source stage')
        elif old.stat().st_size==fresh.stat().st_size and old.read_bytes()==fresh.read_bytes():state='EXACT_MATCH_RECOMPUTED'
        else:state='MISMATCH_RECOMPUTED_REVIEW_REQUIRED'
        status[name]=dict(state=state,new_sha256=s.sha(fresh.read_bytes()))
    report=dict(schema='VIRALOS_REPORT_RECOVERY_V1',config_sha256=expected,source_lock_present=lock_present,old_run_modified=False,stages=status,recomputed=r,production_accepted=False,publication_authorized=False,human_review_required=True)
    (out/'recovery.json').write_bytes(s.encoded(report));(out/'INCOMPLETE').unlink();return report


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('recover')
    for n in ('config','expected','source','output'):a.add_argument('--'+n,required=True)
    a=sub.add_parser('assess')
    for n in ('qc','qc-sha','timeline','timeline-sha','policy','policy-sha','output'):a.add_argument('--'+n,required=True)
    args=vars(p.parse_args());mode=args.pop('mode')
    if mode=='recover':r=recover(**args)
    else:
        policy=s.read(args['policy'],args['policy_sha']);q=s.read(args['qc'],args['qc_sha']);t=s.read(args['timeline'],args['timeline_sha'])
        if set(policy)!={'video_sha256','shots'} or policy['video_sha256']!=q['audit']['video_sha256']:raise ValueError('policy identity')
        r=variable(q,t,policy['shots']);r.update(qc_sha256=args['qc_sha'],timeline_sha256=args['timeline_sha'],policy_sha256=args['policy_sha'])
        with Path(args['output']).open('xb') as f:f.write(s.encoded(r))
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
