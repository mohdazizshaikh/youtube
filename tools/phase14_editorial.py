"""Versioned, private Phase 14 review workspace; permanently synthetic-blocked."""
import argparse, hashlib, json, re, secrets, sqlite3
from contextlib import closing
from pathlib import Path
try:
    from . import phase14_assembly as a, phase14_quality as q, phase14_review_render as r
except ImportError:
    import phase14_assembly as a, phase14_quality as q, phase14_review_render as r

SCHEMA='VIRALOS_PHASE14_REVIEW_V1'
APP_ID=0x564f4831
MAX_VIDEO=128*1024*1024
CATEGORIES={'visual','caption','voice','fact','rights','audio','packaging'}


def pinned(path, pin, limit):
    path=Path(path)
    if not isinstance(pin,str) or not re.fullmatch('[0-9a-f]{64}',pin) or path.is_symlink() or not path.is_file(): raise ValueError('regular pinned file required')
    with path.open('rb') as f: raw=f.read(limit+1)
    if not raw or len(raw)>limit or hashlib.sha256(raw).hexdigest()!=pin: raise ValueError('file size or hash mismatch')
    return raw


def prepare(video, video_sha, receipt, receipt_sha, timeline, timeline_sha, output):
    vr=pinned(receipt,receipt_sha,100_000); tr=pinned(timeline,timeline_sha,100_000); v,t=json.loads(vr),json.loads(tr)
    n=a.check_timeline(t['shots'])
    if v.get('status')!='SYNTHETIC_PRIVATE_REVIEW_CANDIDATE' or v.get('caption_basis')!='synthetic_fixture' or v.get('publication_authorized') is not False or v.get('acoustic_alignment_verified') is not False or v.get('queue_enqueued') is not False or v.get('timeline_sha256')!=timeline_sha or v.get('audit',{}).get('video_sha256')!=video_sha or t.get('plan_sha256')!=a.PLAN_SHA: raise ValueError('unsupported candidate or receipt chain')
    raw=pinned(video,video_sha,MAX_VIDEO); out=Path(output).resolve(); out.mkdir(exist_ok=False); (out/'INCOMPLETE').touch()
    (out/'review.mp4').write_bytes(raw); (out/'source_receipt.json').write_bytes(vr); (out/'timeline.json').write_bytes(tr)
    audit=a.audit(out/'review.mp4',video_sha,t['shots'],True)
    if r.audio_hash(out/'review.mp4')!=v.get('audio_packet_sha256'): raise ValueError('audio payload mismatch')
    info=dict(schema=SCHEMA,video_sha256=video_sha,receipt_sha256=receipt_sha,timeline_sha256=timeline_sha,frames=n,fps=30,chapters=[dict(id=f'{i//3+1:02}',start_frame=t['shots'][i]['start_frame'],end_frame=t['shots'][i+2]['end_frame']) for i in range(0,24,3)],audit=audit,publication_authorized=False,acoustic_alignment_verified=False,legacy_queue_enqueued=False)
    (out/'workspace.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf8')
    with closing(sqlite3.connect(out/'revisions.sqlite')) as db:
        db.executescript(f'PRAGMA application_id={APP_ID}; PRAGMA user_version=1; CREATE TABLE identity (pin TEXT NOT NULL); CREATE TABLE notes (revision INTEGER PRIMARY KEY, frame INTEGER NOT NULL, category TEXT NOT NULL, note TEXT NOT NULL);')
        db.execute('INSERT INTO identity VALUES (?)',(q.sha(out/'workspace.json'),)); db.commit()
    (out/'INCOMPLETE').unlink(); return info


def load(root):
    root=Path(root).resolve()
    if (root/'INCOMPLETE').exists(): raise ValueError('incomplete workspace')
    meta=root/'workspace.json'; m=json.loads(meta.read_text(encoding='utf8'))
    if m.get('schema')!=SCHEMA or m.get('publication_authorized') is not False or m.get('acoustic_alignment_verified') is not False: raise ValueError('unsupported workspace')
    with closing(connect(root,q.sha(meta))) as db: pass
    pinned(root/'source_receipt.json',m['receipt_sha256'],100_000); pinned(root/'timeline.json',m['timeline_sha256'],100_000)
    return m,pinned(root/'review.mp4',m['video_sha256'],MAX_VIDEO),q.sha(meta)


def connect(root,pin):
    file=Path(root)/'revisions.sqlite'
    if file.is_symlink() or not file.is_file(): raise ValueError('private revision DB required')
    db=sqlite3.connect(file.resolve().as_uri()+'?mode=rw',uri=True,timeout=5)
    try:
        if db.execute('PRAGMA application_id').fetchone()[0]!=APP_ID or db.execute('PRAGMA user_version').fetchone()[0]!=1 or db.execute('SELECT pin FROM identity').fetchall()!=[(pin,)]: raise ValueError('workspace DB identity mismatch')
        return db
    except BaseException: db.close();raise


def notes(root,pin):
    with closing(connect(root,pin)) as db:
        rows=db.execute('SELECT revision,frame,category,note FROM notes ORDER BY revision').fetchall()
    return dict(revision=rows[-1][0] if rows else 0,notes=[dict(zip(('revision','frame','category','note'),row)) for row in rows],state='DEMO_BLOCKED',publication_authorized=False)


def append(root,pin,frames,body):
    if not isinstance(body,dict) or set(body)!={'revision','frame','category','note'}: raise ValueError('invalid revision envelope')
    rev,frame,cat,note=(body[k] for k in ('revision','frame','category','note'))
    if type(rev) is not int or rev<0 or type(frame) is not int or not 0<=frame<frames or not isinstance(cat,str) or cat not in CATEGORIES or not isinstance(note,str) or not 1<=len(note.strip())<=1000 or any(ord(c)<32 and c not in '\n\t' for c in note): raise ValueError('invalid time-coded note')
    with closing(connect(root,pin)) as db:
        db.execute('BEGIN IMMEDIATE'); old=db.execute('SELECT COALESCE(MAX(revision),0) FROM notes').fetchone()[0]
        if old!=rev or old>=1000: raise ValueError('stale revision or note limit')
        db.execute('INSERT INTO notes VALUES (?,?,?,?)',(rev+1,frame,cat,note.strip())); db.commit()
    return notes(root,pin)


PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><title>ViralOS private review</title><style nonce="NONCE">body{font:16px system-ui;background:#101b2b;color:#edf3fa;max-width:1000px;margin:25px auto;padding:0 18px}video{width:100%;max-height:65vh}button,select,textarea{font:inherit;margin:6px;padding:8px}textarea{width:95%;box-sizing:border-box}li{white-space:pre-wrap}strong{color:#ffc368}</style><h1>ViralOS · Private editorial review</h1><p><strong>SYNTHETIC / NOT ALIGNED / RELEASE BLOCKED</strong></p><video id="video" controls preload="metadata"></video><p id="chapters"></p><label>Issue category <select id="category">CATEGORIES</select></label><label>Time-coded note<textarea id="note" maxlength="1000" placeholder="Describe a revision at the current playback position"></textarea></label><button id="save">Save note at current frame</button><p id="status" role="status"></p><ol id="history"></ol><script nonce="NONCE">const token='TOKEN', headers={'X-Review-Session':token}, video=document.getElementById('video'), status=document.getElementById('status');let revision=0,frames=0;async function get(p){const r=await fetch(p,{headers});if(!r.ok)throw Error('Request failed');return r.json()}function show(x){revision=x.revision;document.getElementById('history').replaceChildren(...x.notes.map(n=>{let li=document.createElement('li');li.textContent=`${(n.frame/30).toFixed(2)}s · ${n.category} · ${n.note}`;return li}));status.textContent=`Revision ${revision} · DEMO BLOCKED`}async function start(){let m=await get('/api/meta');frames=m.frames;for(const c of m.chapters){let b=document.createElement('button');b.textContent='Chapter '+c.id;b.onclick=()=>video.currentTime=c.start_frame/30;document.getElementById('chapters').append(b)}let r=await fetch('/api/video',{headers});if(!r.ok)throw Error('Video verification failed');video.src=URL.createObjectURL(await r.blob());show(await get('/api/notes'))}document.getElementById('save').onclick=async()=>{try{const r=await fetch('/api/notes',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({revision,frame:Math.min(frames-1,Math.floor(video.currentTime*30)),category:document.getElementById('category').value,note:document.getElementById('note').value})});if(!r.ok){show(await get('/api/notes'));throw Error('Save rejected; check note or retry after reload')}show(await r.json());document.getElementById('note').value=''}catch(e){status.textContent=e.message}};start().catch(e=>status.textContent=e.message)</script></html>'''


def create_app(root,port=8766):
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse, Response
    from starlette.concurrency import run_in_threadpool
    root=Path(root).resolve(); m,raw,pin=load(root); token=secrets.token_hex(32);nonce=secrets.token_hex(16);host=f'127.0.0.1:{port}'
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    @app.middleware('http')
    async def guard(request,call_next):
        h=request.headers
        if h.get('host')!=host or h.get('origin') not in (None,'http://'+host) or h.get('sec-fetch-site') not in (None,'none','same-origin') or (request.url.path.startswith('/api/') and not secrets.compare_digest(h.get('x-review-session','').encode(),token.encode())): response=JSONResponse({'detail':'Local session required'},403)
        else: response=await call_next(request)
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; media-src blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"});return response
    @app.get('/')
    def home():return HTMLResponse(PAGE.replace('NONCE',nonce).replace('TOKEN',token).replace('CATEGORIES',''.join(f'<option>{c}</option>' for c in sorted(CATEGORIES))))
    @app.get('/api/meta')
    def meta():return m
    @app.get('/api/video')
    def video():return Response(raw,media_type='video/mp4')
    @app.get('/api/notes')
    def listing():return notes(root,pin)
    @app.post('/api/notes')
    async def submit(request: Request):
        if request.headers.get('content-type','').split(';')[0]!='application/json':return JSONResponse({'detail':'JSON required'},415)
        data=bytearray()
        async for chunk in request.stream():
            if len(data)+len(chunk)>8192:return JSONResponse({'detail':'Too large'},413)
            data.extend(chunk)
        try:return await run_in_threadpool(append,root,pin,m['frames'],json.loads(data))
        except (ValueError,TypeError,UnicodeError,RecursionError):return JSONResponse({'detail':'Invalid or stale note'},409)
    return app


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True);b=s.add_parser('prepare')
    for name in ('video','video_sha','receipt','receipt_sha','timeline','timeline_sha','output'):b.add_argument('--'+name.replace('_','-'),type=str if name.endswith('_sha') else Path,required=True)
    w=s.add_parser('serve');w.add_argument('--workspace',type=Path,required=True);w.add_argument('--port',type=int,default=8766);args=vars(p.parse_args());cmd=args.pop('cmd')
    if cmd=='prepare': print(json.dumps(prepare(**args),indent=2))
    else:
        import uvicorn
        if not 1024<=args['port']<=65535:raise ValueError('invalid port')
        uvicorn.run(create_app(args['workspace'],args['port']),host='127.0.0.1',port=args['port'],proxy_headers=False,access_log=False)
