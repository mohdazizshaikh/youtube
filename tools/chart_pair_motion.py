"""Separate bilingual chart value-row highlight motion candidates.

Preserves chart geometry, data, and text. Equal frame stages are illustrative,
not speech aligned. No inherited editorial queue or publication eligibility.
"""
from __future__ import annotations
import argparse
import io
import json
import sqlite3
import subprocess
import wave
from pathlib import Path
from PIL import Image,ImageChops
from fontTools.ttLib import TTLibError

from tools import bilingual_chart_pilot as cp, chart_review_dashboard as dashboard
from tools import native_flow_motion as motion,pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file
from tools.paired_mix_snapshot import write_raw
from tools.bilingual_pilot import json_bytes

REQUEST="VIRALOS_CHART_PAIR_MOTION_REQUEST_V1"
SCHEMA="VIRALOS_CHART_PAIR_MOTION_V1"
MAX_REQUEST=16000
LANGS=cp.LANGS
MAX_STAGES=24
BACKGROUND=(32,55,77)
ACTIVE=(65,92,116)


def validate(raw,request_pin,chart_pair_pin):
    pv.pin(chart_pair_pin)
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","chart_pair_sha256","effect"}
               and obj["schema"]==REQUEST and obj["chart_pair_sha256"]==chart_pair_pin
               and obj["effect"]=="VALUE_ROW_HIGHLIGHT_V1","MOTION_REQUEST")
    return obj


def stages(frames,count):
    pv.require(pv.exact_int(count,3,5) and pv.exact_int(frames,count*5,750),"STAGE_FRAMES")
    q,r=divmod(frames,count)
    return [q+(i<r) for i in range(count)]


def row_boxes(fmt,count):
    pv.require(fmt in ("SHORT","LONG") and pv.exact_int(count,3,5),"ROW_LAYOUT")
    tx,ty,tw,th=(42,740,636,390) if fmt=="SHORT" else (655,178,583,414)
    rh=th//count
    # PIL crop rectangles are exclusive at right/bottom. Include the last
    # painted table pixel, but not the gap or any other chart element.
    return [(tx,ty+i*rh,tx+tw+1,ty+(i+1)*rh-5) for i in range(count)]


def images(raw,fmt,count):
    boxes=row_boxes(fmt,count)
    with Image.open(io.BytesIO(raw)) as im:
        dims=(720,1280) if fmt=="SHORT" else (1280,720)
        pv.require(im.format=="PNG" and im.size==dims,"CHART_IMAGE")
        base=im.convert("RGB")
    result=[]
    for box in boxes:
        crop=base.crop(box)
        # Only exact flat table-background pixels change. Text, antialias
        # pixels, colored data markers, axes and warning remain byte-identical.
        diff=ImageChops.difference(crop,Image.new("RGB",crop.size,BACKGROUND))
        r,g,b=diff.split()
        mask=ImageChops.lighter(ImageChops.lighter(r,g),b).point(lambda x:255 if x==0 else 0)
        pv.require(mask.histogram()[255]>=crop.width*crop.height//3,"CHART_BACKGROUND")
        im=base.copy()
        im.paste(Image.new("RGB",crop.size,ACTIVE),box[:2],mask)
        buf=io.BytesIO()
        im.save(buf,format="PNG")
        result.append(buf.getvalue())
    pv.require(len({sha(x) for x in result})==count,"STAGE_DISTINCT")
    return result


def prepare(inputs,chart_pair,chart_pair_pin,request,request_pin):
    validate(request,request_pin,chart_pair_pin)
    checked=cp.verify(inputs,chart_pair,chart_pair_pin)
    chart_pair=ps.local_dir(chart_pair)
    raw=pv.read(chart_pair/"chart_pair.json",cp.MAX_REQUEST)
    obj=dashboard.records(raw,chart_pair_pin)
    pv.require(checked["fresh_media_audit"] is True and checked["duration_ms"]==obj["duration_ms"],
               "PARENT_AUDIT")
    counts=[]
    root=ps.local_dir(inputs[2])
    for row in obj["scenes"]:
        folder=ps.local_dir(root/f'scene_{row["scene"]:02}')
        data=cp.chart.validate_data(pv.read(folder/"data.json",cp.chart.MAX_JSON),row["data_sha256"],
                                    pv.read(folder/"source.bin",cp.chart.MAX_SOURCE),row["source_sha256"])
        counts.append(len(data["rows"]))
    pv.require(sum(counts)<=MAX_STAGES,"STAGE_BUDGET")
    tracks={}
    for lang in LANGS:
        parent=ps.local_dir(chart_pair/lang)
        record=obj["runs"][lang]
        manifest=pv.document(parent/"draft"/"manifest.json")
        pv.require(pv.file_hash(parent/"draft"/"manifest.json",pv.MAX_JSON)==record["manifest_sha256"]
                   and manifest["fps"]==25 and pv.exact_int(manifest["frames"],30,1500)
                   and manifest["duration_ms"]==obj["duration_ms"]
                   and len(manifest["scenes"])==len(counts),"MOTION_BUDGET")
        rendered=[]
        for i,(scene,count) in enumerate(zip(manifest["scenes"],counts),1):
            pv.require(scene["scene"]==i,"SCENE_ORDER")
            raw=pv.read(parent/"draft"/scene["board_file"],cp.chart.MAX_PNG)
            pv.require(sha(raw)==scene["board_sha256"],"BOARD_PIN")
            rendered.append(list(zip(stages(scene["frames"],count),images(raw,manifest["format"],count))))
        pv.require(sum(n for row in rendered for n,_ in row)==manifest["frames"],"MOTION_TOTAL")
        tracks[lang]=(parent,manifest,rendered)
    pv.require([[n for n,_ in row] for row in tracks["hindi"][2]]==
               [[n for n,_ in row] for row in tracks["english"][2]],"BILINGUAL_STAGES")
    return tracks,checked


def track_receipt(parent,manifest,rendered,output,audit):
    return {"parent_manifest_sha256":pv.file_hash(parent/"draft"/"manifest.json",pv.MAX_JSON),
            "parent_video_sha256":manifest["files_sha256"]["draft.mp4"],
            "motion_video_sha256":pv.file_hash(output/"motion.mp4",motion.MAX_VIDEO),
            "caption_sha256":pv.file_hash(output/"captions.vtt",128000),
            "duration_ms":manifest["duration_ms"],
            "stages":[[{"frames":n,"png_sha256":sha(png)} for n,png in row] for row in rendered],
            "audit":audit}


def receipt(chart_pair_pin,request_pin,children):
    pv.require(children["hindi"]["duration_ms"]==children["english"]["duration_ms"],"DURATION")
    return {"schema":SCHEMA,"chart_pair_sha256":chart_pair_pin,"request_sha256":request_pin,
            "duration_ms":children["hindi"]["duration_ms"],"fps":25,
            "effect":"VALUE_ROW_HIGHLIGHT_V1","tracks":children,
            "timing_method":"EQUAL_STAGE_NOT_WORD_ALIGNED","editorial_queue_created":False,
            "human_visual_review_required":True,"source_transcription_verified":False,
            "word_alignment_verified":False,"publication_eligible":False}


def build(inputs,chart_pair,chart_pair_pin,request,request_pin,output):
    tracks,before=prepare(inputs,chart_pair,chart_pair_pin,request,request_pin)
    output=ps.new_dir(output,ps.local_dir(chart_pair))
    for source in (inputs[0],inputs[2]):ps.new_dir(output,ps.local_dir(source))
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    children={}
    for lang,(parent,manifest,rendered) in tracks.items():
        child=output/lang
        child.mkdir(mode=0o700)
        motion.render_video(child,parent,manifest,rendered)
        write_raw(child/"captions.vtt",pv.read(parent/"draft"/"captions.vtt",128000))
        audit=motion.media_audit(child/"motion.mp4",parent,manifest,rendered)
        children[lang]=track_receipt(parent,manifest,rendered,child,audit)
    pv.require(cp.verify(inputs,chart_pair,chart_pair_pin)==before,"PARENT_CHANGED")
    raw=json_bytes(receipt(chart_pair_pin,request_pin,children))
    write_raw(output/"motion_pair.json",raw)
    marker.unlink()
    return {"motion_pair_sha256":sha(raw),"frames_compared":{l:children[l]["audit"]["frames_compared"] for l in LANGS},
            "publication_eligible":False}


def verify(inputs,chart_pair,chart_pair_pin,request,request_pin,output,motion_pair_pin):
    output=ps.local_dir(output)
    pv.require({p.name for p in output.iterdir()}==set(LANGS)|{"motion_pair.json"},"MOTION_INVENTORY")
    raw=pinned(pv.read(output/"motion_pair.json",pv.MAX_JSON),motion_pair_pin,pv.MAX_JSON)
    tracks,before=prepare(inputs,chart_pair,chart_pair_pin,request,request_pin)
    children={}
    for lang,(parent,manifest,rendered) in tracks.items():
        child=ps.local_dir(output/lang)
        pv.require({p.name for p in child.iterdir()}=={"motion.mp4","captions.vtt"},"TRACK_INVENTORY")
        pv.require(pv.read(child/"captions.vtt",128000)==pv.read(parent/"draft"/"captions.vtt",128000),
                   "MOTION_CAPTIONS")
        audit=motion.media_audit(child/"motion.mp4",parent,manifest,rendered)
        children[lang]=track_receipt(parent,manifest,rendered,child,audit)
    pv.require(raw==json_bytes(receipt(chart_pair_pin,request_pin,children)),"MOTION_RECEIPT")
    pv.require(cp.verify(inputs,chart_pair,chart_pair_pin)==before,"PARENT_CHANGED")
    return {"motion_pair_sha256":motion_pair_pin,"fresh_media_audit":True,
            "frames_compared":{l:children[l]["audit"]["frames_compared"] for l in LANGS},
            "publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("pair","root","chart-request","hindi-font","english-font","chart-pair","request","output"):
            a.add_argument("--"+name,type=Path,required=True)
        for name in ("pair","chart-request","hindi-font","english-font","chart-pair","request"):
            a.add_argument("--"+name+"-sha256",required=True)
        if mode=="verify":a.add_argument("--motion-pair-sha256",required=True)
    a=p.parse_args()
    try:
        inputs=(a.pair,a.pair_sha256,a.root,private_file(a.chart_request,cp.MAX_REQUEST),
                a.chart_request_sha256,
                {l:private_file(getattr(a,l+"_font"),cp.chart.ht.MAX_FONT) for l in LANGS},
                {l:getattr(a,l+"_font_sha256") for l in LANGS})
        common=(inputs,a.chart_pair,a.chart_pair_sha256,private_file(a.request,MAX_REQUEST),
                a.request_sha256,a.output)
        result=build(*common) if a.mode=="build" else verify(*common,a.motion_pair_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,sqlite3.Error,
            subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
