"""Opt-in, loopback-only review console; no publication or arbitrary path API."""
from __future__ import annotations
import json
import secrets
from pathlib import Path
from threading import Lock
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from . import domain_review_queue as queue
from .domain_draft_review import review_packet, template, _canonical
from .domain_draft_video import digest
from .local_http_guard import check_browser_request

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / 'static'
MAX_BODY = 128_000
MAX_VIDEO = 128 * 1024 * 1024


def load_catalog(path: Path):
    with Path(path).open('rb') as f:
        raw = f.read(MAX_BODY + 1)
    if len(raw) > MAX_BODY:
        raise ValueError('catalog too large')
    data = json.loads(raw)
    if not isinstance(data, list) or not 1 <= len(data) <= 100:
        raise ValueError('catalog requires 1–100 entries')
    entries = {}
    for item in data:
        if not isinstance(item, dict) or set(item) != {'manifest_sha256','draft','assets'}:
            raise ValueError('exact catalog fields required')
        pin = queue._pin(item['manifest_sha256'])
        if pin in entries or not all(isinstance(item[k], str) and Path(item[k]).is_absolute() for k in ('draft','assets')):
            raise ValueError('unique pins and absolute owner paths required')
        entries[pin] = (Path(item['draft']), Path(item['assets']))
    return entries


def create_app(db: Path, entries: dict):
    db = Path(db)
    if db.is_symlink() or db.resolve().is_relative_to(ROOT):
        raise ValueError('private queue database must be outside source tree')
    db = db.resolve()
    queue.status(db)  # refuse missing, foreign or unsupported DB at startup
    if not 1 <= len(entries) <= 100:
        raise ValueError('catalog requires 1–100 entries')
    catalog = {}
    for pin, pair in entries.items():
        queue._pin(pin)
        draft, assets = map(Path, pair)
        if any(p.is_symlink() or not p.is_dir() for p in (draft, assets)):
            raise ValueError('existing non-symlink directories required')
        draft, assets = draft.resolve(), assets.resolve()
        if any(p.is_relative_to(ROOT) or db.is_relative_to(p) for p in (draft, assets)) or draft == assets:
            raise ValueError('private media and queue must be separate and outside source tree')
        catalog[pin] = (draft, assets)
    token = secrets.token_hex(32)
    gate = Lock()
    app = FastAPI(title='ViralOS local editorial console', docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def guard(request, call_next):
        problem = check_browser_request(host_header=request.headers.get('host',''), scheme=request.url.scheme,
            origin=request.headers.get('origin'), fetch_site=request.headers.get('sec-fetch-site'))
        if problem:
            response = JSONResponse({'detail':'Local browser request rejected'}, status_code=403)
        elif request.url.path.startswith('/api/') and not secrets.compare_digest(request.headers.get('x-review-session','').encode('utf8'), token.encode('ascii')):
            response = JSONResponse({'detail':'Local console session required; reload page'}, status_code=403)
        else:
            response = await call_next(request)
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
            'X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
            'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"})
        return response

    def paths(pin):
        if pin not in catalog:
            raise HTTPException(404, 'Draft not in configured catalog')
        return catalog[pin]

    def registered(pin):
        paths(pin)
        for row in queue.status(db)['drafts']:
            if row['manifest_sha256'] == pin:
                return row
        raise HTTPException(409,'Register draft first')

    def operation(fn):
        # Bound simultaneous expensive decode operations on the CPU target.
        if not gate.acquire(blocking=False):
            raise HTTPException(429,'Another media operation is running; retry manually')
        try:
            return fn()
        except (ValueError, OSError, KeyError, TypeError, RuntimeError):
            raise HTTPException(409,'Media, review or revision validation failed; reload and inspect local inputs') from None
        finally:
            gate.release()

    @app.get('/', response_class=HTMLResponse)
    def home():
        return HTMLResponse((STATIC/'domain_review.html').read_text(encoding='utf8').replace('__SESSION_TOKEN__',token))

    @app.get('/review.js')
    def script():
        return Response((STATIC/'domain_review.js').read_bytes(),media_type='text/javascript')

    @app.get('/review.css')
    def style():
        return Response((STATIC/'domain_review.css').read_bytes(),media_type='text/css')

    @app.get('/api/drafts')
    def listing():
        def work():
            current = queue.status(db)
            rows = {x['manifest_sha256']:x for x in current['drafts']}
            return {'drafts':[rows.get(pin,{'manifest_sha256':pin,'state':'UNREGISTERED','revision':None}) for pin in catalog],
                    'history':[x for x in current['history'] if x['manifest_sha256'] in catalog], 'publication_eligible':False}
        return operation(work)

    @app.post('/api/drafts/{pin}/register')
    def register(pin: str):
        draft, assets = paths(pin)
        return operation(lambda: {'draft':queue.register(db,draft,assets,pin),'publication_eligible':False})

    @app.get('/api/drafts/{pin}/packet')
    def packet(pin: str):
        draft, assets = paths(pin)
        def work():
            row = registered(pin)
            packet = review_packet(draft,assets,pin)
            if _canonical(packet) != row['packet_sha256'] or packet['video_sha256'] != row['video_sha256']:
                raise ValueError('changed packet')
            return {'packet':packet,'review':template(packet),'revision':row['revision'],'publication_eligible':False}
        return operation(work)

    @app.get('/api/drafts/{pin}/video')
    def video(pin: str):
        draft, _ = paths(pin)
        def work():
            row = registered(pin)
            file = draft/'draft.mp4'
            if file.is_symlink() or not file.is_file():
                raise ValueError('invalid video')
            # Serve the exact verified bytes, not a subsequent open of a mutable path.
            with file.open('rb') as f:
                raw = f.read(MAX_VIDEO+1)
            if not raw or len(raw)>MAX_VIDEO or digest(raw)!=row['video_sha256']:
                raise ValueError('video pin mismatch')
            return Response(raw,media_type='video/mp4')
        return operation(work)

    @app.post('/api/drafts/{pin}/submit')
    async def submit(pin: str, request: Request):
        draft, assets = paths(pin)
        if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
            raise HTTPException(415,'JSON required')
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>MAX_BODY:
                raise HTTPException(413,'Review exceeds size limit')
            raw.extend(chunk)
        try:
            body = json.loads(raw)
            if not isinstance(body,dict) or set(body)!={'revision','review'} or type(body['revision']) is not int or body['revision']<0 or not isinstance(body['review'],dict):
                raise ValueError('invalid envelope')
        except (ValueError,UnicodeError,RecursionError):
            raise HTTPException(400,'Invalid review envelope') from None
        return await run_in_threadpool(operation,lambda: queue.submit(db,draft,assets,pin,body['revision'],body['review']))

    return app
