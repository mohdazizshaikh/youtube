"""Separate bilingual chart scene fade-through-dark candidate with frame/PTS audit.

Only the source chart content region fades. The source date and review warning
stay unchanged before encoding. Never blend two distinct data visualizations.
"""
from __future__ import annotations
import argparse
import io
import json
import shutil
import sqlite3
import subprocess
import wave
from fractions import Fraction
from pathlib import Path
from PIL import Image
from fontTools.ttLib import TTLibError
from tools import bilingual_chart_pilot as cp,chart_review_dashboard as dash
from tools import native_flow_motion as motion,pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file
from tools.motion_review import write_file
from tools.bilingual_pilot import json_bytes

REQUEST="VIRALOS_CHART_TRANSITION_REQUEST_V1"
SCHEMA="VIRALOS_CHART_TRANSITION_PAIR_V1"
EFFECT="DIP_TO_DARK_V1"
MAX_REQUEST=16000
MAX_STAGES=24
LANGS=cp.LANGS


def validate(raw,request_pin,chart_pin):
    pv.pin(chart_pin)
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","chart_pair_sha256","effect","fade_frames"}
               and obj["schema"]==REQUEST and obj["chart_pair_sha256"]==chart_pin
               and obj["effect"]==EFFECT and pv.exact_int(obj["fade_frames"],3,8),"TRANSITION_REQUEST")
    return obj


def schedule(frames,index,count,fade):
    pv.require(pv.exact_int(count,2,8) and pv.exact_int(index,0,count-1)
               and pv.exact_int(fade,3,8) and pv.exact_int(frames,13,750),"SCENE_BUDGET")
    # Alpha values are integer numerators over fade. First/last scenes have
    # only one boundary fade. At least half a second of unchanged chart.
    incoming=list(range(fade,0,-1)) if index else []
    outgoing=list(range(1,fade+1)) if index<count-1 else []
    hold=frames-len(incoming)-len(outgoing)
    pv.require(hold>=13,"STATIC_HOLD_REQUIRED")
    return [(1,a) for a in incoming]+[(hold,0)]+[(1,a) for a in outgoing]


def image(raw,fmt,alpha,fade):
    pv.require(fmt in ("SHORT","LONG") and pv.exact_int(fade,3,8)
               and pv.exact_int(alpha,0,fade),"FADE")
    dims=(720,1280) if fmt=="SHORT" else (1280,720)
    with Image.open(io.BytesIO(raw)) as im:
        pv.require(im.format=="PNG" and im.size==dims,"CHART_IMAGE")
        base=im.convert("RGB")
    if not alpha:return raw
    # Source-date text begins at h-104; preserve that entire bottom area.
    region=(0,0,dims[0],dims[1]-104)
    crop=base.crop(region)
    base.paste(Image.blend(crop,Image.new("RGB",crop.size,"#101e31"),alpha/fade),region[:2])
    buf=io.BytesIO()
    base.save(buf,format="PNG")
    return buf.getvalue()


def frame_check(raw,rendered):
    count=sum(n for row in rendered for n,_ in row)
    pv.require(len(raw)==count*motion.BYTES,"TRANSITION_FRAME_COUNT")
    pos=0
    worst=0.
    for row in rendered:
        refs={}
        for _,png in row:
            key=sha(png)
            if key not in refs:
                with Image.open(io.BytesIO(png)) as im:
                    refs[key]=im.convert("RGB").resize((motion.SIZE,motion.SIZE),Image.Resampling.BILINEAR)
        for n,png in row:
            key=sha(png)
            for _ in range(n):
                actual=Image.frombytes("RGB",(motion.SIZE,motion.SIZE),raw[pos:pos+motion.BYTES])
                pos+=motion.BYTES
                expected=motion.mae(actual,refs[key])
                alternatives=[motion.mae(actual,ref) for k,ref in refs.items() if k!=key]
                # Repeated fade levels in interior scenes are legitimate.
                # Distinguish other levels; reject low-contrast ambiguous fades.
                pv.require(expected<=12 and alternatives and expected+.10<min(alternatives),
                           "TRANSITION_FRAME_MISMATCH")
                worst=max(worst,expected)
    return {"frames_compared":count,"max_frame_mae":round(worst,4),
            "comparison_resolution":[motion.SIZE,motion.SIZE],"full_resolution_pixels_verified":False}


def check_pts(obj,count):
    pv.require(pv.exact_int(count,1,1500) and type(obj) is dict,"PTS_COUNT")
    streams=obj.get("streams")
    frames=obj.get("frames")
    pv.require(type(streams) is list and len(streams)==1 and type(frames) is list
               and len(frames)==count,"PTS_COUNT")
    base=streams[0].get("time_base")
    pv.require(type(base) is str and len(base)<=32 and "/" in base,"PTS_TIME_BASE")
    try:tb=Fraction(base)
    except (ValueError,ZeroDivisionError) as exc:raise ValueError("PTS_TIME_BASE") from exc
    pv.require(tb>0,"PTS_TIME_BASE")
    for i,row in enumerate(frames):
        stamp=row.get("pts")
        pv.require(type(stamp) is int and stamp>=0 and stamp*tb==Fraction(i,25),"PTS_GRID")
    return {"presentation_timestamps_verified":True,"pts_frames":count,"frame_period_ms":40}


def media_audit(video,parent,manifest,rendered):
    audit=motion.media_audit(video,parent,manifest,rendered,frame_checker=frame_check)
    probe=shutil.which("ffprobe")
    pv.require(probe,"LOCAL_FFPROBE_REQUIRED")
    raw=motion.execute([probe,"-v","error","-protocol_whitelist","file,pipe","-select_streams","v:0",
                        "-show_frames","-show_streams","-show_entries","frame=pts:stream=time_base",
                        "-of","json",str(video)],30)
    pv.require(len(raw)<=pv.MAX_JSON,"PTS_REPORT_SIZE")
    return {**audit,**check_pts(pv.decode(raw),manifest["frames"])}


def prepare(inputs,chart_pair,chart_pin,request,request_pin):
    spec=validate(request,request_pin,chart_pin)
    checked=cp.verify(inputs,chart_pair,chart_pin)
    chart_pair=ps.local_dir(chart_pair)
    obj=dash.records(pv.read(chart_pair/"chart_pair.json",cp.MAX_REQUEST),chart_pin)
    pv.require(checked["fresh_media_audit"] is True and checked["duration_ms"]==obj["duration_ms"],
               "PARENT_AUDIT")
    count=len(obj["scenes"])
    fade=spec["fade_frames"]
    pv.require(count+2*(count-1)*fade<=MAX_STAGES,"TRANSITION_STAGE_BUDGET")
    tracks={}
    for lang in LANGS:
        parent=ps.local_dir(chart_pair/lang)
        manifest=pv.document(parent/"draft"/"manifest.json")
        pv.require(pv.file_hash(parent/"draft"/"manifest.json",pv.MAX_JSON)==obj["runs"][lang]["manifest_sha256"]
                   and manifest["fps"]==25 and pv.exact_int(manifest["frames"],30,1500)
                   and manifest["duration_ms"]==obj["duration_ms"]
                   and len(manifest["scenes"])==count,"TRANSITION_BUDGET")
        rendered=[]
        timing=[]
        for i,scene in enumerate(manifest["scenes"]):
            pv.require(scene["scene"]==i+1,"SCENE_ORDER")
            raw=pv.read(parent/"draft"/scene["board_file"],cp.chart.MAX_PNG)
            pv.require(sha(raw)==scene["board_sha256"],"BOARD_PIN")
            entries=schedule(scene["frames"],i,count,fade)
            timing.append(entries)
            rendered.append([(n,image(raw,manifest["format"],a,fade)) for n,a in entries])
        pv.require(sum(n for row in rendered for n,_ in row)==manifest["frames"],"FRAME_TOTAL")
        tracks[lang]=(parent,manifest,rendered,timing)
    pv.require(tracks["hindi"][3]==tracks["english"][3],"BILINGUAL_TIMING")
    return tracks,checked,spec


def track_receipt(parent,manifest,rendered,timing,child,audit):
    return {"parent_manifest_sha256":pv.file_hash(parent/"draft"/"manifest.json",pv.MAX_JSON),
            "parent_video_sha256":manifest["files_sha256"]["draft.mp4"],
            "transition_video_sha256":pv.file_hash(child/"motion.mp4",motion.MAX_VIDEO),
            "caption_sha256":pv.file_hash(child/"captions.vtt",128000),
            "duration_ms":manifest["duration_ms"],"audit":audit,
            "stages":[[{"frames":n,"fade_numerator":a,"png_sha256":sha(png)}
                       for (n,png),(_,a) in zip(row,steps)] for row,steps in zip(rendered,timing)]}


def receipt(chart_pin,request_pin,spec,children):
    pv.require(children["hindi"]["duration_ms"]==children["english"]["duration_ms"],"DURATION")
    return {"schema":SCHEMA,"chart_pair_sha256":chart_pin,"request_sha256":request_pin,
            "effect":EFFECT,"fade_frames":spec["fade_frames"],"fps":25,
            "duration_ms":children["hindi"]["duration_ms"],"tracks":children,
            "source_date_and_warning_preserved_before_encoding":True,
            "numerical_interpolation":False,"word_alignment_verified":False,
            "editorial_queue_created":False,"human_visual_review_required":True,
            "publication_eligible":False}


def build(inputs,chart_pair,chart_pin,request,request_pin,output):
    tracks,before,spec=prepare(inputs,chart_pair,chart_pin,request,request_pin)
    output=ps.new_dir(output,ps.local_dir(chart_pair))
    for source in (inputs[0],inputs[2]):ps.new_dir(output,ps.local_dir(source))
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    children={}
    for lang,(parent,manifest,rendered,timing) in tracks.items():
        child=output/lang
        child.mkdir(mode=0o700)
        motion.render_video(child,parent,manifest,rendered)
        write_file(child/"captions.vtt",pv.read(parent/"draft"/"captions.vtt",128000))
        audit=media_audit(child/"motion.mp4",parent,manifest,rendered)
        children[lang]=track_receipt(parent,manifest,rendered,timing,child,audit)
    pv.require(cp.verify(inputs,chart_pair,chart_pin)==before,"PARENT_CHANGED")
    raw=json_bytes(receipt(chart_pin,request_pin,spec,children))
    write_file(output/"transition_pair.json",raw)
    marker.unlink()
    return {"transition_pair_sha256":sha(raw),"publication_eligible":False}


def verify(inputs,chart_pair,chart_pin,request,request_pin,output,transition_pin):
    output=ps.local_dir(output)
    pv.require({p.name for p in output.iterdir()}==set(LANGS)|{"transition_pair.json"},"TRANSITION_INVENTORY")
    raw=pinned(pv.read(output/"transition_pair.json",pv.MAX_JSON),transition_pin,pv.MAX_JSON)
    tracks,before,spec=prepare(inputs,chart_pair,chart_pin,request,request_pin)
    children={}
    for lang,(parent,manifest,rendered,timing) in tracks.items():
        child=ps.local_dir(output/lang)
        pv.require({p.name for p in child.iterdir()}=={"motion.mp4","captions.vtt"},"TRACK_INVENTORY")
        pv.require(pv.read(child/"captions.vtt",128000)==pv.read(parent/"draft"/"captions.vtt",128000),
                   "TRANSITION_CAPTIONS")
        audit=media_audit(child/"motion.mp4",parent,manifest,rendered)
        children[lang]=track_receipt(parent,manifest,rendered,timing,child,audit)
    pv.require(raw==json_bytes(receipt(chart_pin,request_pin,spec,children)),"TRANSITION_RECEIPT")
    pv.require(cp.verify(inputs,chart_pair,chart_pin)==before,"PARENT_CHANGED")
    return {"transition_pair_sha256":transition_pin,"fresh_media_audit":True,
            "frames_compared":{l:children[l]["audit"]["frames_compared"] for l in LANGS},
            "presentation_timestamps_verified":True,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("pair","root","chart-request","hindi-font","english-font","chart-pair","request","output"):
            a.add_argument("--"+name,type=Path,required=True)
        for name in ("pair","chart-request","hindi-font","english-font","chart-pair","request"):
            a.add_argument("--"+name+"-sha256",required=True)
        if mode=="verify":a.add_argument("--transition-pair-sha256",required=True)
    a=p.parse_args()
    try:
        inputs=(a.pair,a.pair_sha256,a.root,private_file(a.chart_request,cp.MAX_REQUEST),
                a.chart_request_sha256,{l:private_file(getattr(a,l+"_font"),cp.chart.ht.MAX_FONT) for l in LANGS},
                {l:getattr(a,l+"_font_sha256") for l in LANGS})
        common=(inputs,a.chart_pair,a.chart_pair_sha256,private_file(a.request,MAX_REQUEST),a.request_sha256,a.output)
        result=build(*common) if a.mode=="build" else verify(*common,a.transition_pair_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,sqlite3.Error,
            subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
