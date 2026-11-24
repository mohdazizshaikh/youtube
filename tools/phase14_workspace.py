"""Bilingual, synthetic-only private review and recovery; no release authority."""
import argparse, hashlib, json, sqlite3, secrets
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
try:
    from . import phase14_bilingual as b
except ImportError:
    import phase14_bilingual as b

APP=0x564f4b31; SCHEMA='VIRALOS_BILINGUAL_REVIEW_V1'; LANGS=('en','hi')
CATS=('visual','caption','voice','fact','rights','audio','packaging')
LIMIT=128*1024*1024
FILES=('metadata.json','en.mp4','en_receipt.json','en_timeline.json','hi.mp4','hi_render.json','hi_master.json','hi_timeline.json','en.png','hi.png')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p,pin=None,limit=LIMIT):
    p=Path(p)
    if p.is_symlink() or not p.is_file():raise ValueError('regular file required')
    with p.open('rb') as f:raw=f.read(limit+1)
    if not raw or len(raw)>limit or (pin is not None and sha(raw)!=b.pin(pin)):raise ValueError('size/hash mismatch')
    return raw
def dump(p,m):
    with Path(p).open('x',encoding='utf8') as f:json.dump(m,f,ensure_ascii=False,indent=2);f.write('\n')
def fresh(p):
    p=Path(p);p.mkdir(mode=0o700,exist_ok=False);(p/'INCOMPLETE').touch();return p

def chapters(t,m):
    if len(t['shots'])!=24 or len(m['chapters'])!=8:raise ValueError('chapter count')
    end=0;out=[]
    for i,s in enumerate(t['shots']):
        n=s['samples']
        if type(n) is not int or not 48000<=n<=4320000:raise ValueError('sample bound')
        f=(n+1599)//1600
        if (s['chapter'],s['beat'],s['start_frame'],s['end_frame'],s['padding_samples'])!=(f'{i//3+1:02}',i%3,end,end+f,f*1600-n):raise ValueError('timeline mismatch')
        if i%3==0:
            c=m['chapters'][i//3]
            if c['start_seconds']!=end//30 or not isinstance(c['title'],str) or not 1<=len(c['title'])<=150:raise ValueError('chapter mismatch')
            out.append(dict(title=c['title'],start_frame=end))
        end+=f
    if end!=t['frames'] or not 720<=end<=27000:raise ValueError('duration')
    return out,end

def prepare(config,expected,output):
    c=json.loads(read(config,expected,128000))
    if set(c)!=set(FILES):raise ValueError('config inventory')
    d={}
    for n in FILES:
        if set(c[n])!={'path','sha256'}:raise ValueError('pin envelope')
        d[n]=read(c[n]['path'],c[n]['sha256'],LIMIT if n.endswith('.mp4') else 2_000_000)
    m,e,et,h,hm,ht=[json.loads(d[n]) for n in ('metadata.json','en_receipt.json','en_timeline.json','hi_render.json','hi_master.json','hi_timeline.json')]
    ev,hv=sha(d['en.mp4']),sha(d['hi.mp4'])
    if m.get('schema')!='VIRALOS_PACKAGING_DRAFT_V2' or m.get('publication_authorized') is not False or m.get('human_review_required') is not True:raise ValueError('metadata gate')
    if e.get('status')!='SYNTHETIC_PRIVATE_REVIEW_CANDIDATE' or e.get('caption_basis')!='synthetic_fixture' or e.get('publication_authorized') is not False or e.get('acoustic_alignment_verified') is not False or e.get('timeline_sha256')!=sha(d['en_timeline.json']) or e['audit']['video_sha256']!=ev or m['english_video_sha256']!=ev:raise ValueError('English chain')
    if h.get('schema')!='VIRALOS_HINDI_REVIEW_V1' or h.get('basis')!='synthetic_espeak' or h.get('caption_basis')!='synthetic_fixture' or h.get('publication_authorized') is not False or h.get('acoustic_alignment_verified') is not False or h.get('intake_receipt_sha256')!=sha(d['hi_timeline.json']) or h.get('plan_sha256')!=ht.get('plan_sha256') or h.get('plan_sha256')!=m.get('hindi_plan_sha256') or hm.get('source_sha256')!=h.get('video_sha256') or hm.get('output_sha256')!=hv or hm.get('numeric_gate_pass') is not True or hm.get('publication_authorized') is not False or m['hindi']['video_sha256']!=hv:raise ValueError('Hindi chain')
    for l in LANGS:
        if sha(d[l+'.png'])!=m['thumbnail_sha256']['thumbnail_'+l+'.png']:raise ValueError('thumbnail mismatch')
    ec,ef=chapters(et,m['english']);hc,hf=chapters(ht,m['hindi'])
    if ef!=e['audit']['frames'] or hf!=h['frames']:raise ValueError('frame mismatch')
    out=fresh(output)
    for n,raw in d.items():(out/n).write_bytes(raw)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(b.audit,out/(l+'.mp4'),f) for l,f in zip(LANGS,(ef,hf))]; audits=[x.result() for x in jobs]
    if any(not a['numeric_audio_gate_pass'] or a['video_sha256']!=v for a,v in zip(audits,(ev,hv))):raise ValueError('fresh audit gate')
    info=dict(schema=SCHEMA,files={n:sha(x) for n,x in d.items()},locales={l:dict(frames=f,chapters=c,audit=a) for l,f,c,a in zip(LANGS,(ef,hf),(ec,hc),audits)},state='DEMO_BLOCKED',publication_authorized=False,acoustic_alignment_verified=False)
    dump(out/'workspace.json',info);pin=sha(read(out/'workspace.json'))
    with closing(sqlite3.connect(out/'notes.sqlite')) as db:
        db.executescript(f'PRAGMA application_id={APP}; PRAGMA user_version=1; CREATE TABLE identity(pin TEXT); CREATE TABLE notes(revision INTEGER PRIMARY KEY, locale TEXT, frame INTEGER, category TEXT, note TEXT);')
        db.execute('INSERT INTO identity VALUES (?)',(pin,));db.commit()
    (out/'INCOMPLETE').unlink();return info

def connect(root,pin):
    p=Path(root)/'notes.sqlite'
    if p.is_symlink() or not p.is_file() or p.stat().st_size>8_000_000:raise ValueError('invalid ledger')
    db=sqlite3.connect(p.absolute().as_uri()+'?mode=rw',uri=True,timeout=5)
    try:
        if db.execute('PRAGMA application_id').fetchone()[0]!=APP or db.execute('PRAGMA user_version').fetchone()[0]!=1 or db.execute('SELECT pin FROM identity').fetchall()!=[(pin,)]:raise ValueError('ledger identity')
        return db
    except BaseException:db.close();raise

def check_note(m,l,f,c,n):
    if l not in LANGS or type(f) is not int or not 0<=f<m['locales'][l]['frames'] or c not in CATS or not isinstance(n,str) or not 1<=len(n.strip())<=1000 or any(ord(x)<32 and x not in '\n\t' for x in n):raise ValueError('invalid note')
def rows(db,m):
    r=db.execute('SELECT revision,locale,frame,category,note FROM notes ORDER BY revision LIMIT 1001').fetchall()
    if len(r)>1000:raise ValueError('note limit')
    for i,(v,l,f,c,n) in enumerate(r,1):
        if i!=v:raise ValueError('revision gap')
        check_note(m,l,f,c,n)
    return r

def load(root,pin,partial=False):
    root=Path(root)
    if root.is_symlink() or ((root/'INCOMPLETE').exists() and not partial):raise ValueError('incomplete workspace')
    m=json.loads(read(root/'workspace.json',pin,128000))
    if m.get('schema')!=SCHEMA or m.get('state')!='DEMO_BLOCKED' or m.get('publication_authorized') is not False or m.get('acoustic_alignment_verified') is not False or set(m['files'])!=set(FILES) or set(m['locales'])!=set(LANGS):raise ValueError('workspace schema')
    for n,h in m['files'].items():read(root/n,h,LIMIT if n.endswith('.mp4') else 2_000_000)
    with closing(connect(root,pin)) as db:
        if db.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError('corrupt ledger')
        rows(db,m)
    return m

def notes(root,pin,m):
    with closing(connect(root,pin)) as db:r=rows(db,m)
    return dict(revision=len(r),notes=[dict(zip(('revision','locale','frame','category','note'),x)) for x in r],state='DEMO_BLOCKED',publication_authorized=False)
def append(root,pin,m,body):
    if not isinstance(body,dict) or set(body)!={'revision','locale','frame','category','note'} or type(body['revision']) is not int:raise ValueError('invalid envelope')
    l,f,c,n=(body[k] for k in ('locale','frame','category','note'));check_note(m,l,f,c,n)
    with closing(connect(root,pin)) as db:
        db.execute('BEGIN IMMEDIATE');r=len(rows(db,m))
        if r!=body['revision'] or r>=1000:raise ValueError('stale revision')
        db.execute('INSERT INTO notes VALUES (?,?,?,?,?)',(r+1,l,f,c,n.strip()));db.commit()
    return notes(root,pin,m)

def backup(root,pin,output):
    m=load(root,pin);out=fresh(output)
    for n,h in {**m['files'],'workspace.json':pin}.items():(out/n).write_bytes(read(Path(root)/n,h))
    with closing(connect(root,pin)) as src,closing(sqlite3.connect(out/'notes.sqlite')) as dest:src.backup(dest)
    with closing(connect(out,pin)) as db:r=len(rows(db,m))
    info=dict(schema='VIRALOS_BILINGUAL_BACKUP_V1',workspace_sha256=pin,revision=r,files={n:sha(read(out/n)) for n in (*FILES,'workspace.json','notes.sqlite')},publication_authorized=False)
    dump(out/'backup.json',info);(out/'INCOMPLETE').unlink();return info

def restore(source,expected,output):
    source=Path(source)
    if source.is_symlink() or (source/'INCOMPLETE').exists():raise ValueError('incomplete backup')
    m=json.loads(read(source/'backup.json',expected,128000));pin=m['workspace_sha256']
    if m.get('schema')!='VIRALOS_BILINGUAL_BACKUP_V1' or m.get('publication_authorized') is not False or set(m['files'])!=set((*FILES,'workspace.json','notes.sqlite')) or m['files']['workspace.json']!=pin:raise ValueError('backup schema')
    out=fresh(output)
    for n,h in m['files'].items():(out/n).write_bytes(read(source/n,h))
    info=load(out,pin,partial=True)
    if notes(out,pin,info)['revision']!=m['revision']:raise ValueError('backup revision mismatch')
    (out/'INCOMPLETE').unlink();return dict(workspace_sha256=pin,revision=m['revision'],publication_authorized=False)

def create_app(root,pin,port=8767):
    from fastapi import FastAPI,Request
    from fastapi.responses import HTMLResponse,JSONResponse,Response
    from starlette.concurrency import run_in_threadpool
    m=load(root,pin);root=Path(root);token=secrets.token_hex(32);nonce=secrets.token_hex(16);host=f'127.0.0.1:{port}'
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    @app.middleware('http')
    async def guard(req,call_next):
        h=req.headers
        if h.get('host')!=host or h.get('origin') not in (None,'http://'+host) or h.get('sec-fetch-site') not in (None,'none','same-origin') or (req.url.path.startswith('/api/') and not secrets.compare_digest(h.get('x-review-session','').encode(),token.encode())):r=JSONResponse({'detail':'Local session required'},403)
        else:r=await call_next(req)
        r.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':f"default-src 'none'; script-src 'nonce-{nonce}'; connect-src 'self'; media-src blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"});return r
    @app.get('/')
    def home():return HTMLResponse(PAGE.replace('TOKEN',token).replace('NONCE',nonce).replace('CATEGORIES',''.join(f'<option>{c}</option>' for c in CATS)))
    @app.get('/api/meta')
    def meta():return m
    @app.get('/api/video/{lang}')
    def video(lang:str):
        if lang not in LANGS:return JSONResponse({'detail':'Unknown language'},404)
        n=lang+'.mp4'
        try:return Response(read(root/n,m['files'][n]),media_type='video/mp4')
        except (ValueError,OSError):return JSONResponse({'detail':'Media changed'},409)
    @app.get('/api/notes')
    def get_notes():return notes(root,pin,m)
    @app.post('/api/notes')
    async def submit(req:Request):
        if req.headers.get('content-type','').split(';')[0]!='application/json':return JSONResponse({'detail':'JSON required'},415)
        raw=bytearray()
        async for chunk in req.stream():
            if len(raw)+len(chunk)>8192:return JSONResponse({'detail':'Too large'},413)
            raw.extend(chunk)
        try:return await run_in_threadpool(append,root,pin,m,json.loads(raw))
        except (ValueError,TypeError,UnicodeError,RecursionError):return JSONResponse({'detail':'Invalid or stale note'},409)
    return app

PAGE='''<!doctype html><html><meta charset="utf-8"><title>Private bilingual review</title><h1>ViralOS bilingual review</h1><p>SYNTHETIC / NOT ALIGNED / RELEASE BLOCKED</p><select id="lang"><option value="en">English</option><option value="hi">हिन्दी</option></select><p><video id="v" controls width="800"></video></p><div id="chapters"></div><select id="cat">CATEGORIES</select><textarea id="note" maxlength="1000"></textarea><button id="save" disabled>Save note at current frame</button><p id="status"></p><ol id="history"></ol><script nonce="NONCE">const h={'X-Review-Session':'TOKEN'},$=s=>document.getElementById(s);let m,rev=0,active=null,busy=false,url=null;async function get(p){let r=await fetch(p,{headers:h});if(!r.ok)throw Error('Request rejected');return r.json()}function show(x){rev=x.revision;$('history').replaceChildren(...x.notes.map(n=>{let li=document.createElement('li');li.textContent=n.locale+' · '+(n.frame/30).toFixed(2)+'s · '+n.category+' · '+n.note;return li}));$('status').textContent='Revision '+rev+' · DEMO BLOCKED'}async function film(){if(busy)return;busy=true;active=null;$('lang').disabled=$('save').disabled=true;try{let l=$('lang').value,r=await fetch('/api/video/'+l,{headers:h});if(!r.ok)throw Error('Video rejected');let next=URL.createObjectURL(await r.blob());$('v').src=next;if(url)URL.revokeObjectURL(url);url=next;active=l;$('chapters').replaceChildren(...m.locales[l].chapters.map(c=>{let b=document.createElement('button');b.textContent=c.title;b.onclick=()=>$('v').currentTime=c.start_frame/30;return b}));show(await get('/api/notes'))}catch(e){$('status').textContent=e.message}finally{busy=false;$('lang').disabled=false;$('save').disabled=!active}}$('lang').onchange=film;$('save').onclick=async()=>{if(busy||!active)return;busy=true;$('lang').disabled=$('save').disabled=true;try{let r=await fetch('/api/notes',{method:'POST',headers:{...h,'Content-Type':'application/json'},body:JSON.stringify({revision:rev,locale:active,frame:Math.min(m.locales[active].frames-1,Math.floor($('v').currentTime*30)),category:$('cat').value,note:$('note').value})});if(!r.ok){show(await get('/api/notes'));throw Error('Note rejected')}show(await r.json());$('note').value=''}catch(e){$('status').textContent=e.message}finally{busy=false;$('lang').disabled=$('save').disabled=false}};(async()=>{m=await get('/api/meta');await film()})().catch(e=>$('status').textContent=e.message)</script></html>'''

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    for cmd,fields in [('prepare','config expected output'),('backup','root pin output'),('restore','source expected output'),('serve','root pin')]:
        s=sub.add_parser(cmd)
        for n in fields.split():s.add_argument('--'+n,required=True)
        if cmd=='serve':s.add_argument('--port',type=int,default=8767)
    a=vars(p.parse_args());cmd=a.pop('cmd')
    if cmd=='serve':
        import uvicorn
        if not 1024<=a['port']<=65535:raise ValueError('invalid port')
        uvicorn.run(create_app(**a),host='127.0.0.1',port=a['port'],proxy_headers=False,access_log=False)
    else:print(json.dumps({'prepare':prepare,'backup':backup,'restore':restore}[cmd](**a),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
