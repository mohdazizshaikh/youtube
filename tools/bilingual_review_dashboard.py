"""Read-only loopback dashboard for a stopped bilingual pilot or native derivative.

Fresh audit at startup, pinned files and metadata on each request. Never submits
reviews, merges queues, or grants release. Run individual review consoles separately.
"""
from __future__ import annotations
import argparse
import html
import json
import secrets
import sqlite3
from pathlib import Path
from threading import Lock

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from app.local_http_guard import check_browser_request
from tools import bilingual_pilot as bp, native_hindi_pilot as nh, pilot_run_verify as pv
from tools.bilingual_snapshot import pair_records
from tools.narration_prepare import pinned, private_root

LANGS=("hindi","english")
MAX_VIDEO=128*1024*1024


def select_runs(pair,pair_pin,native=None,native_pin=None):
    pair=private_root(pair)
    pv.require({p.name for p in pair.iterdir()}==set(LANGS)|{"pair.json"},"PAIR_INVENTORY")
    raw=pv.read(pair/"pair.json",bp.MAX_BOARDS)
    records=pair_records(raw,pair_pin)
    parent=pv.decode(raw)
    pv.require(parent.get("visual_text_support")=="ASCII_ONLY","PAIR_MODE")
    result={lang:(pair/lang,records[lang]["manifest_sha256"],records[lang]["video_sha256"])
            for lang in LANGS}
    if native is not None or native_pin is not None:
        pv.require(native is not None and native_pin is not None,"NATIVE_ARGUMENTS")
        native=private_root(native)
        pv.require({p.name for p in native.iterdir()}=={"native.json","hindi"},"NATIVE_INVENTORY")
        row=pv.decode(pinned(pv.read(native/"native.json",nh.MAX_REQUEST),native_pin,nh.MAX_REQUEST))
        pv.require(type(row) is dict and row.get("schema")==nh.SCHEMA
                   and row.get("parent_pair_sha256")==pair_pin
                   and row.get("parent_hindi_manifest_sha256")==records["hindi"]["manifest_sha256"]
                   and row.get("english_manifest_sha256")==records["english"]["manifest_sha256"]
                   and row.get("duration_ms")==parent["duration_ms"]
                   and row.get("visual_mode") in nh.VISUAL_MODES
                   and row.get("publication_eligible") is False
                   and row.get("native_visual_accepted") is False,"NATIVE_BINDING")
        result["hindi"]=(native/"hindi",pv.pin(row["manifest_sha256"]),pv.pin(row["video_sha256"]))
    pv.require(result["hindi"][1]!=result["english"][1],"DUPLICATE_CHILD")
    return result,parent["duration_ms"]


def snapshot(runs,duration,fresh=False):
    rows={}
    for lang in LANGS:
        run,pin,video=runs[lang]
        checked=pv.verify(run,pin,fresh=fresh)
        manifest=pv.document(run/"draft"/"manifest.json")
        pv.require(manifest["duration_ms"]==duration and manifest["files_sha256"]["draft.mp4"]==video,
                   "DASHBOARD_MEDIA_BINDING")
        packet=pv.document(run/"review_packet.json")
        scenes=[]
        for row in packet["scenes"]:
            # Only display declared content. Browser uses textContent, not HTML.
            scenes.append({"scene":row["scene"],"start_ms":row["start_ms"],"end_ms":row["end_ms"],
                           "title":row["title"],"narration_text":row["narration_text"],
                           "claims":[x["text"] for x in row["claims"]],
                           "native_visual_declaration":row["specialist_facts"].get(nh.KEY),
                           "mixed_audio":row["specialist_facts"].get("production_mix_audio_kind")=="MIXED_VOICE_AND_MUSIC"})
        rows[lang]={"manifest_sha256":pin,"video_sha256":video,
                    "revision":checked["queue_revision"],"state":checked["queue_state"],
                    "synthetic_demo":checked["synthetic_demo"],"scenes":scenes}
    for field in ("synthetic_demo",):
        pv.require(rows["hindi"][field]==rows["english"][field],"PAIR_CLASSIFICATION")
    pv.require([(s["start_ms"],s["end_ms"]) for s in rows["hindi"]["scenes"]]==
               [(s["start_ms"],s["end_ms"]) for s in rows["english"]["scenes"]],"PAIR_TIMING")
    return {"schema":"VIRALOS_BILINGUAL_DASHBOARD_V1","duration_ms":duration,"languages":rows,
            "read_only":True,"fresh_media_audit":fresh,"human_review_verified":False,
            "translation_verified":False,"publication_eligible":False}


def create_app(pair,pair_pin,native=None,native_pin=None):
    return create_selected_app(lambda:select_runs(pair,pair_pin,native,native_pin))


def create_selected_app(selector, *, mixed=False):
    """Internal trusted selector; never accept browser-supplied paths or pins."""
    runs,duration=selector()
    snapshot(runs,duration,fresh=True)
    token=secrets.token_hex(32)
    gate=Lock()
    app=FastAPI(title="ViralOS bilingual review",docs_url=None,redoc_url=None,openapi_url=None)

    @app.middleware("http")
    async def guard(request:Request,call_next):
        problem=check_browser_request(host_header=request.headers.get("host",""),
                 scheme=request.url.scheme,origin=request.headers.get("origin"),
                 fetch_site=request.headers.get("sec-fetch-site"))
        if problem:
            response=JSONResponse({"detail":"Local browser request rejected"},status_code=403)
        elif request.url.path.startswith("/api/") and not secrets.compare_digest(
                request.headers.get("x-review-session","").encode("utf8"),token.encode("ascii")):
            response=JSONResponse({"detail":"Local session required"},status_code=403)
        else:
            response=await call_next(request)
        response.headers.update({"Cache-Control":"no-store","X-Content-Type-Options":"nosniff",
            "X-Frame-Options":"DENY","Referrer-Policy":"no-referrer",
            "Content-Security-Policy":"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"})
        return response

    def operation(fn):
        if not gate.acquire(blocking=False):
            raise HTTPException(429,"Another local operation is running")
        try:
            current=selector()
            pv.require(current==(runs,duration),"DASHBOARD_CHANGED")
            return fn()
        except (ValueError,OSError,KeyError,TypeError,RuntimeError,sqlite3.Error):
            raise HTTPException(409,"Local integrity validation failed") from None
        finally:
            gate.release()

    @app.get("/",response_class=HTMLResponse)
    def home():
        page=PAGE.replace("__TOKEN__",token)
        if mixed:
            page=page.replace("Bilingual editorial review","Mixed-production editorial review").replace(
                "Private, read-only comparison.","Private, read-only comparison of mixed audio candidates.")
        return HTMLResponse(page)

    @app.get("/dashboard.js")
    def script():
        return Response(JS,media_type="text/javascript")

    @app.get("/dashboard.css")
    def css():
        return Response(CSS,media_type="text/css")

    @app.get("/api/status")
    def status():
        return operation(lambda:snapshot(runs,duration))

    @app.get("/api/video/{lang}")
    def video(lang:str):
        if lang not in LANGS:
            raise HTTPException(404,"Unknown language")
        def work():
            snapshot(runs,duration)
            run,_,video_pin=runs[lang]
            raw=pv.read(run/"draft"/"draft.mp4",MAX_VIDEO)
            pv.require(bp.sha(raw)==video_pin,"VIDEO_PIN")
            return Response(raw,media_type="video/mp4")
        return operation(work)

    return app


PAGE="""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="review-session" content="__TOKEN__"><link rel="stylesheet" href="/dashboard.css">
<title>ViralOS bilingual editorial review</title></head><body>
<header><h1>Bilingual editorial review</h1><p>Private, read-only comparison. No publication authorization.</p>
<button id="refresh" type="button">Refresh verified metadata</button><p id="status" role="status"></p></header>
<main><section id="hindi"><h2>Hindi</h2><p class="state"></p><button type="button" data-lang="hindi">Load Hindi video</button><video controls preload="none"></video><div class="scenes"></div></section>
<section id="english"><h2>English</h2><p class="state"></p><button type="button" data-lang="english">Load English video</button><video controls preload="none"></video><div class="scenes"></div></section></main>
<footer>Review each language in its existing independent console. Close this dashboard before editing or backup.</footer>
<script src="/dashboard.js" defer></script></body></html>"""

CSS="""body{font:16px system-ui,sans-serif;margin:24px;color:#eaf0f7;background:#142236}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}section{background:#20354b;padding:18px;border-radius:12px;min-width:0}video{display:block;width:100%;max-height:460px;background:#0a1420;margin:12px 0}button{padding:10px 14px;border:1px solid #7ea3b7;border-radius:6px;background:#eef4f8;color:#142236}article{border-top:1px solid #62798e;padding:10px 0;overflow-wrap:anywhere}footer{margin-top:24px;color:#b9c8d6}.state{font-weight:bold}"""

JS="""'use strict';
const token=document.querySelector('meta[name="review-session"]').content;
const status=document.getElementById('status');
const urls={};
const api=async(path)=>{const r=await fetch(path,{headers:{'X-Review-Session':token},cache:'no-store'});if(!r.ok)throw Error('Local integrity or session check failed');return r;};
function node(tag,text){const e=document.createElement(tag);e.textContent=text;return e;}
function clearVideo(lang){const v=document.querySelector('#'+lang+' video');v.removeAttribute('src');v.load();if(urls[lang]){URL.revokeObjectURL(urls[lang]);delete urls[lang];}}
let busy=false;
async function action(fn){if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);try{await fn();}catch(e){for(const l of ['hindi','english']){clearVideo(l);document.querySelector('#'+l+' .scenes').replaceChildren();document.querySelector('#'+l+' .state').textContent='Unavailable';}status.textContent='Local integrity or session check failed. Close and inspect inputs.';}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);}}
async function refresh(){await action(async()=>{const d=await(await api('/api/status')).json();for(const lang of ['hindi','english']){clearVideo(lang);const row=d.languages[lang],section=document.getElementById(lang);section.querySelector('.state').textContent=row.state+' · revision '+row.revision+(row.synthetic_demo?' · synthetic demo':'');const scenes=section.querySelector('.scenes');scenes.replaceChildren();for(const s of row.scenes){const a=document.createElement('article');a.append(node('h3','Scene '+s.scene+' · '+(s.start_ms/1000).toFixed(2)+'–'+(s.end_ms/1000).toFixed(2)+' s'),node('p',s.title),node('p',s.narration_text));for(const c of s.claims)a.append(node('p',c));if(s.native_visual_declaration)a.append(node('p',s.native_visual_declaration));if(s.mixed_audio)a.append(node('p','Mixed narration and music — listening review required'));scenes.append(a);}}status.textContent='Duration '+(d.duration_ms/1000).toFixed(2)+' s · metadata verified; startup media audit only.';});}
document.getElementById('refresh').addEventListener('click',refresh);
for(const b of document.querySelectorAll('button[data-lang]'))b.addEventListener('click',()=>action(async()=>{const l=b.dataset.lang;clearVideo(l);urls[l]=URL.createObjectURL(await(await api('/api/video/'+l)).blob());document.querySelector('#'+l+' video').src=urls[l];}));
window.addEventListener('pagehide',()=>{for(const l of Object.keys(urls))URL.revokeObjectURL(urls[l]);});
refresh();
"""


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pair",type=Path,required=True)
    p.add_argument("--pair-sha256",required=True)
    p.add_argument("--native",type=Path)
    p.add_argument("--native-sha256")
    p.add_argument("--port",type=int,default=8766)
    args=p.parse_args()
    if not 1024<=args.port<=65535:
        p.error("port must be between 1024 and 65535")
    app=create_app(args.pair,args.pair_sha256,args.native,args.native_sha256)
    uvicorn.run(app,host="127.0.0.1",port=args.port,access_log=False,proxy_headers=False)


if __name__=="__main__":
    main()
