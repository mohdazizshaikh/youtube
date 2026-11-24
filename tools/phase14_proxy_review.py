"""Offline proxy review index and append-only revision requests, never approvals."""
import argparse, html, json, re, unicodedata
from pathlib import Path
try:
    from . import phase14_media_run as m, phase14_scene_review as s
except ImportError:
    import phase14_media_run as m, phase14_scene_review as s

CATEGORIES=('motion','accuracy','language','readability','audio','rights','other')

def template(r,receipt_sha):
    t=r['task'];return dict(schema='VIRALOS_PROXY_REVISION_NOTE_V1',task_id=t['id'],proxy_sha256=r['proxy_sha256'],proxy_receipt_sha256=receipt_sha,source_video_sha256=t['video_sha256'],source_frame=None,category=None,note='',expected_revision=0)


def load(root,report,expected):
    root=Path(root);data=json.loads(m.raw(report,expected,256000));rows=data['shots']
    ids={f'{l}-{i:02}' for l in ('en','hi') for i in range(1,25)}
    if data.get('schema')!='VIRALOS_PROXY_BATCH_V1' or data.get('production_accepted') is not False or data.get('publication_authorized') is not False or data.get('human_review_required') is not True or data['shot_count']!=48 or data['operation_count']!=144 or len(rows)!=48 or {r['task']['id'] for r in rows}!=ids:raise ValueError('complete proxy batch required')
    result={}
    for r in rows:
        t=r['task'];i=t['id'];folder=root/i;receipt=s.encoded(r)
        if folder.is_symlink() or (folder/'INCOMPLETE').exists() or r.get('schema')!='VIRALOS_SHOT_PROXY_V1' or r.get('decode_pass') is not True or r.get('silent') is not True or r.get('production_accepted') is not False or r.get('publication_authorized') is not False or t.get('status')!='OPEN' or t.get('human_review_required') is not True:raise ValueError('proxy review identity')
        if type(t['start_frame']) is not int or type(t['end_frame']) is not int or t['start_frame']<0 or t['end_frame']-t['start_frame']!=r['frames'] or r['frames']<=0:raise ValueError('frame range')
        if m.raw(folder/'receipt.json',limit=100000)!=receipt:raise ValueError('proxy receipt mismatch')
        m.raw(folder/'proxy.mp4',r['proxy_sha256']);result[i]=(r,s.sha(receipt))
    return result


def build(root,report,expected):
    root=Path(root);rows=load(root,report,expected);cards=[];ops=[]
    for i,(r,pin) in sorted(rows.items(),key=lambda x:(-x[1][0]['task']['freeze_fraction'],x[0])):
        t=r['task'];req=template(r,pin);p=root/i/'revision.template.json';m.exact(p,s.encoded(req))
        for name in ('proxy_encoded','proxy_decode_verified','proxy_receipt_bound','revision_template_bound'):
            ops.append(dict(operation_id=f'{i}:{name}',status='VERIFIED',proxy_receipt_sha256=pin,revision_template_sha256=s.sha(s.encoded(req))))
        esc=html.escape;cards.append(f'<article><h2>{esc(i.upper())} · {esc(t["priority"])}</h2><p>OPEN · source frames {t["start_frame"]}–{t["end_frame"]-1} · {t["freeze_frames"]}/{r["frames"]} detector coverage</p><video controls preload="none" src="{i}/proxy.mp4" aria-label="Silent review proxy {i}"></video><p>{esc(t["focus"])}</p><p><a href="{i}/proxy.mp4">MP4</a> · <a href="{i}/receipt.json">Evidence</a> · <a href="{i}/revision.template.json" download>Revision note template</a></p></article>')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; media-src \'self\' file:; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>ViralOS private proxy review</title><style>body{background:#122032;color:#edf3fa;font:16px system-ui;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}article{background:#1c3045;padding:16px;border-radius:8px}video{width:100%;background:#000}a{color:#8adbd1}h2{font-size:18px}p{line-height:1.45}</style><h1>ViralOS bilingual proxy review</h1><p>48 silent, lower-resolution proxies. All review tasks OPEN. Native speech, motion and publication not accepted. Download a note template, fill source_frame, category, note and current expected_revision, then import privately with the CLI. No browser playback verification.</p><main>'+''.join(cards)+'</main></html>\n'
    m.exact(root/'index.html',page.encode('utf8'))
    ledger=dict(schema='VIRALOS_PROXY_OPERATION_LEDGER_V1',proxy_batch_sha256=expected,completed_operations=len(ops),human_editorial_tasks_closed=0,operations=ops,publication_authorized=False)
    m.exact(root/'operation_ledger.json',s.encoded(ledger));return ledger


def validate_note(note,r,pin,revision):
    expected=template(r,pin)
    if not isinstance(note,dict) or set(note)!=set(expected):raise ValueError('note schema')
    for k in ('schema','task_id','proxy_sha256','proxy_receipt_sha256','source_video_sha256'):
        if note[k]!=expected[k]:raise ValueError('note identity')
    if type(note['expected_revision']) is not int or note['expected_revision']!=revision:raise ValueError('stale revision')
    t=r['task'];f=note['source_frame'];msg=note['note']
    if type(f) is not int or not t['start_frame']<=f<t['end_frame'] or note['category'] not in CATEGORIES or not isinstance(msg,str) or not 1<=len(msg.strip())<=1000 or len(msg)>1000 or any(unicodedata.category(c)=='Cc' and c not in '\n\t' for c in msg):raise ValueError('note content')
    return dict(note,revision=revision+1,status='OPEN',publication_authorized=False)


def append(root,report,expected,ledger,submission,submission_sha):
    rows=load(root,report,expected);note=json.loads(m.raw(submission,submission_sha,16000));target=Path(ledger);target.mkdir(exist_ok=True)
    if target.is_symlink():raise ValueError('unsafe ledger')
    with (target/'RUNNING').open('xb') as lock:lock.write(expected.encode('ascii'))
    try:
        m.exact(target/'identity.json',s.encoded(dict(proxy_batch_sha256=expected,publication_authorized=False)))
        files=sorted(target.glob('note-*.json'));previous='0'*64
        if len(files)>=1000:raise ValueError('note limit')
        for j,p in enumerate(files,1):
            if p.name!=f'note-{j:04}.json':raise ValueError('revision gap')
            raw=m.raw(p,limit=20000);item=json.loads(raw)
            old=item['submission'];r,pin=rows[old['task_id']];validated=validate_note(old,r,pin,j-1)
            if item!=dict(submission=old,record=validated,previous_sha256=previous):raise ValueError('ledger chain mismatch')
            previous=s.sha(raw)
        r,pin=rows[note['task_id']];record=validate_note(note,r,pin,len(files));data=s.encoded(dict(submission=note,record=record,previous_sha256=previous))
        m.write_new(target/f'note-{len(files)+1:04}.json',data);return dict(revision=record['revision'],note_sha256=s.sha(data),status='OPEN',publication_authorized=False)
    finally:(target/'RUNNING').unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    for name in ('build','append'):
        a=sub.add_parser(name)
        for k in ('root','report','expected'):a.add_argument('--'+k,required=True)
        if name=='append':
            for k in ('ledger','submission','submission-sha'):a.add_argument('--'+k,required=True)
    a=vars(p.parse_args());cmd=a.pop('cmd');print(json.dumps((build if cmd=='build' else append)(**a),indent=2))
