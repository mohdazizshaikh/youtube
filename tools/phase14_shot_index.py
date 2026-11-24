"""Static, local-only shot review index. No approval, upload or remote requests."""
import argparse, html, json, re
from pathlib import Path
try:
    from . import phase14_media_run as m, phase14_scene_review as s
except ImportError:
    import phase14_media_run as m, phase14_scene_review as s


def index(root, report, expected, tasks, tasks_sha, output):
    root=Path(root)
    if root.is_symlink() or (root/'RUNNING').exists():raise ValueError('active or unsafe review root')
    result=json.loads(m.raw(report,expected,128000));backlog=json.loads(m.raw(tasks,tasks_sha,128000))
    rows=result['shots'];todo=backlog['tasks']
    ids={f'{l}-{i:02}' for l in ('en','hi') for i in range(1,25)}
    if result.get('schema')!='VIRALOS_SHOT_BATCH_RESULT_V1' or result.get('publication_authorized') is not False or result.get('production_accepted') is not False or result.get('human_review_required') is not True or result['shot_count']!=48 or result['operation_count']!=192 or len(rows)!=48 or {x['id'] for x in rows}!=ids:raise ValueError('complete batch required')
    if backlog.get('schema')!='VIRALOS_EDITORIAL_TASKS_V1' or backlog.get('publication_authorized') is not False or backlog.get('production_accepted') is not False or backlog.get('human_review_required') is not True or len(todo)!=48 or {x['id'] for x in todo}!=ids:raise ValueError('backlog identity')
    by={x['id']:x for x in rows};tb={x['id']:x for x in todo};cards=[];total=0
    for t in sorted(todo,key=lambda x:(-x['freeze_fraction'],-x['freeze_frames'],x['id'])):
        i=t['id'];d=root/i
        if d.is_symlink() or (d/'INCOMPLETE').exists():raise ValueError('incomplete shot')
        raw=m.raw(d/'receipt.json',by[i]['receipt_sha256'],100000);r=json.loads(raw)
        if r.get('schema')!='VIRALOS_SHOT_REVIEW_V1' or r.get('tasks_sha256')!=tasks_sha or r.get('task')!=tb[i] or r.get('source_video_sha256')!=t['video_sha256'] or r.get('publication_authorized') is not False or r.get('production_accepted') is not False or r.get('decoded_pixels_match') is not True or r.get('silent') is not True or t['status']!='OPEN':raise ValueError('shot receipt identity')
        n=t['end_frame']-t['start_frame']
        if type(n) is not int or n<=0 or n!=r['frames'] or n!=by[i]['frames'] or r['midpoint_source_frame']!=t['start_frame']+n//2:raise ValueError('frame mismatch')
        m.raw(d/'shot.mp4',r['clip_sha256']);m.raw(d/'midpoint.png',r['midpoint_sha256'],10_000_000)
        total+=n;title=html.escape(f"{i.upper()} · Chapter {t['chapter']} · {t['priority']}")
        focus=html.escape(t['focus']);flag=html.escape(t['detector_status']);span=f"Source frames {t['start_frame']}–{t['end_frame']-1} · {n/30:.2f}s · detector coverage {t['freeze_frames']}/{n}"
        cards.append(f'<article><h2>{title}</h2><p>{html.escape(span)}<br>{flag} · OPEN</p><a href="{i}/shot.mp4"><img src="{i}/midpoint.png" loading="lazy" alt="Midpoint of {i}"></a><p>{focus}</p><p><a href="{i}/shot.mp4">Open silent review clip</a> · <a href="{i}/receipt.json">Technical evidence</a></p></article>')
    if total!=result['decoded_frames']:raise ValueError('frame aggregate')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\' file:; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>ViralOS shot review</title><style>body{font:16px system-ui;background:#101d2b;color:#e9eef4;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}article{background:#1a2c3e;padding:16px;border-radius:8px}img{width:100%;height:auto}a{color:#83dfd6}h2{font-size:18px}p{line-height:1.5}</style><h1>ViralOS — 48-shot review index</h1><p>All tasks remain OPEN. Silent clips only; source film audio and artistic acceptance are separate. No publication authority. Open in a trusted local folder.</p><main>'+''.join(cards)+'</main></html>\n'
    out=Path(output)
    if out.parent.resolve()!=root.resolve() or out.name!='index.html':raise ValueError('index must be inside review root')
    m.write_new(out,page.encode('utf8'))
    return dict(schema='VIRALOS_SHOT_INDEX_V1',batch_sha256=expected,tasks_sha256=tasks_sha,index_sha256=s.sha(page.encode('utf8')),shots=48,frames=total,publication_authorized=False,production_accepted=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('root','report','expected','tasks','tasks-sha','output'):p.add_argument('--'+k,required=True)
    print(json.dumps(index(**vars(p.parse_args())),indent=2))
