"""Separate bounded native flow step-highlight motion preview.

Never a regular pilot run or inherited editorial approval. Full frame count and
96x96 RGB diagnostics, not full-resolution pixel equality or word alignment.
"""
from __future__ import annotations
import argparse
import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops,ImageStat
from fontTools.ttLib import TTLibError
from app.domain_draft_video import DraftPlan
from app.m25_audio_conformance import _decoded_track
from tools import native_hindi_pilot as nh,pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file
from tools.bilingual_pilot import json_bytes

REQUEST="VIRALOS_NATIVE_FLOW_MOTION_REQUEST_V1"
SCHEMA="VIRALOS_NATIVE_FLOW_MOTION_V1"
MAX_REQUEST=16000
MAX_VIDEO=128*1024*1024
SIZE=96
BYTES=SIZE*SIZE*3


def validate(raw,request_pin,native_pin):
    pv.pin(native_pin)
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","native_sha256","effect"}
               and obj["schema"]==REQUEST and obj["native_sha256"]==native_pin
               and obj["effect"]=="STEP_HIGHLIGHT_V1","MOTION_REQUEST")
    return obj


def stages(frames):
    pv.require(pv.exact_int(frames,15,750),"MOTION_SCENE_FRAMES")
    q,r=divmod(frames,3)
    return [q+(i<r) for i in range(3)]


def images(raw,fmt):
    with Image.open(io.BytesIO(raw)) as im:
        dims=(720,1280) if fmt=="SHORT" else (1280,720)
        pv.require(im.format=="PNG" and im.size==dims,"MOTION_BOARD")
        base=im.convert("RGB")
    areas=([(84,240+i*290,636,440+i*290) for i in range(3)] if fmt=="SHORT" else
           [(48+i*408,250,416+i*408,500) for i in range(3)])
    results=[]
    for active in range(3):
        im=base.copy()
        # Tint inactive nodes, keeping all original text visible. Active outline
        # is outside the text area. No hidden/added labels or inferred timing.
        for i,box in enumerate(areas):
            if i!=active:
                crop=base.crop(box)
                im.paste(Image.blend(crop,Image.new("RGB",crop.size,"#101e31"),0.55),box[:2])
        ImageDraw.Draw(im).rounded_rectangle(areas[active],radius=22,outline="#ffd166",width=9)
        out=io.BytesIO()
        im.save(out,format="PNG")
        results.append(out.getvalue())
    return results


def prepare(pair,pair_pin,font,font_pin,visual_request,visual_pin,native,native_pin,request,request_pin):
    validate(request,request_pin,native_pin)
    checked=nh.verify(pair,pair_pin,font,font_pin,visual_request,visual_pin,native,native_pin)
    root=ps.local_dir(native)/"hindi"
    receipt=pv.document(root.parent/"native.json")
    pv.require(receipt["visual_mode"]==nh.FLOW_MODE,"FLOW_PARENT_REQUIRED")
    manifest=pv.document(root/"draft"/"manifest.json")
    plan=DraftPlan.model_validate(pv.document(root/"draft"/"plan.json"))
    pv.require(manifest["fps"]==25 and pv.exact_int(manifest["frames"],30,1500),"MOTION_BUDGET")
    rendered=[]
    for row,scene in zip(manifest["scenes"],plan.scenes):
        pv.require(pv.decode(scene.board.specialist_facts[nh.KEY].encode())["schema"]==nh.flow.SCHEMA,"FLOW_SCENE")
        board=pv.read(root/"draft"/row["board_file"],8*1024*1024)
        pv.require(sha(board)==row["board_sha256"],"BOARD_PIN")
        rendered.append(list(zip(stages(row["frames"]),images(board,manifest["format"]))))
    pv.require(sum(n for row in rendered for n,_ in row)==manifest["frames"],"MOTION_TOTAL")
    return root,manifest,rendered,checked


def mae(a,b):
    return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3


def frame_check(raw,rendered):
    count=sum(n for row in rendered for n,_ in row)
    pv.require(len(raw)==count*BYTES,"MOTION_DECODE_COUNT")
    pos=0
    worst=0.0
    for row in rendered:
        refs=[]
        for _,png in row:
            with Image.open(io.BytesIO(png)) as img:
                refs.append(img.convert("RGB").resize((SIZE,SIZE),Image.Resampling.BILINEAR))
        for i,(n,_) in enumerate(row):
            for _ in range(n):
                actual=Image.frombytes("RGB",(SIZE,SIZE),raw[pos:pos+BYTES])
                pos+=BYTES
                scores=[mae(actual,ref) for ref in refs]
                pv.require(scores[i]<=12 and scores[i]+0.15<min(s for j,s in enumerate(scores) if i!=j),
                           "MOTION_FRAME_MISMATCH")
                worst=max(worst,scores[i])
    return {"frames_compared":count,"max_frame_mae":round(worst,4),
            "comparison_resolution":[SIZE,SIZE],"full_resolution_pixels_verified":False}


def execute(cmd,timeout=120):
    return subprocess.check_output(cmd,timeout=timeout,stdin=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def media_audit(video,root,manifest,rendered,*,frame_checker=frame_check):
    exe,probe=shutil.which("ffmpeg"),shutil.which("ffprobe")
    pv.require(exe and probe,"LOCAL_MEDIA_REQUIRED")
    pv.file_hash(video,MAX_VIDEO)
    obj=json.loads(execute([probe,"-v","error","-protocol_whitelist","file,pipe","-show_streams",
                            "-show_format","-of","json",str(video)],30))
    streams=obj["streams"]
    v=[x for x in streams if x["codec_type"]=="video"]
    a=[x for x in streams if x["codec_type"]=="audio"]
    dims=(720,1280) if manifest["format"]=="SHORT" else (1280,720)
    count=manifest["frames"]
    pv.require(len(streams)==2 and len(v)==len(a)==1 and v[0]["codec_name"]=="h264"
               and a[0]["codec_name"]=="aac" and (v[0]["width"],v[0]["height"])==dims
               and int(v[0]["nb_frames"])==count and v[0]["avg_frame_rate"]=="25/1"
               and abs(float(obj["format"]["duration"])-count/25)<=.04,"MOTION_STREAMS")
    parent=root/"draft"/"draft.mp4"
    before=_decoded_track(parent,exe)
    after=_decoded_track(video,exe)
    pv.require(before==after,"MOTION_AUDIO_CHANGED")
    raw=execute([exe,"-nostdin","-v","error","-protocol_whitelist","file,pipe","-i",str(video),
                 "-map","0:v:0","-frames:v",str(count+1),"-threads","1","-vf",f"scale={SIZE}:{SIZE}",
                 "-fps_mode","passthrough","-f","rawvideo","-pix_fmt","rgb24","pipe:1"])
    return {**frame_checker(raw,rendered),"decoded_parent_audio_equal":True}


def render_video(output,root,manifest,rendered):
    exe=shutil.which("ffmpeg")
    pv.require(exe,"LOCAL_FFMPEG_REQUIRED")
    with tempfile.TemporaryDirectory(dir=output) as tmp:
        stage=Path(tmp)
        cmd=[exe,"-nostdin","-v","error","-n"]
        counts=[]
        for n,png in (x for row in rendered for x in row):
            path=stage/f"stage_{len(counts):02}.png"
            path.write_bytes(png)
            counts.append(n)
            cmd+=["-protocol_whitelist","file,pipe","-loop","1","-framerate","25","-t",f"{n/25:.3f}","-i",str(path)]
        count=len(counts)
        graph="".join(f"[{i}:v]setsar=1,setpts=PTS-STARTPTS[v{i}];" for i in range(count))
        graph+="".join(f"[v{i}]" for i in range(count))+f"concat=n={count}:v=1:a=0,setpts=N/(25*TB)[v]"
        cmd+=["-protocol_whitelist","file,pipe","-i",str(root/"draft"/"draft.mp4"),
              "-filter_complex_threads","1","-filter_complex",graph,"-map","[v]","-map",f"{count}:a:0",
              "-r","25","-fps_mode","cfr","-c:v","libx264","-threads","2","-preset","veryfast",
              "-pix_fmt","yuv420p","-c:a","copy","-movflags","+faststart",str(output/"motion.mp4")]
        execute(cmd,300)


def receipt(native_pin,request_pin,root,manifest,rendered,output,audit):
    return {"schema":SCHEMA,"native_sha256":native_pin,"request_sha256":request_pin,
            "parent_manifest_sha256":pv.file_hash(root/"draft"/"manifest.json",pv.MAX_JSON),
            "parent_video_sha256":manifest["files_sha256"]["draft.mp4"],
            "motion_video_sha256":pv.file_hash(output/"motion.mp4",MAX_VIDEO),
            "caption_sha256":pv.file_hash(output/"captions.vtt",128000),
            "duration_ms":manifest["duration_ms"],"fps":25,
            "stages":[[{"frames":n,"png_sha256":sha(png)} for n,png in row] for row in rendered],
            "audit":audit,"editorial_queue_created":False,"human_visual_review_required":True,
            "word_alignment_verified":False,"publication_eligible":False}


def build(inputs,output):
    root,manifest,rendered,before=prepare(*inputs)
    output=ps.new_dir(output,root.parent)
    ps.new_dir(output,ps.local_dir(inputs[0]))
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    render_video(output,root,manifest,rendered)
    caps=pv.read(root/"draft"/"captions.vtt",128000)
    with (output/"captions.vtt").open("xb") as f:f.write(caps)
    audit=media_audit(output/"motion.mp4",root,manifest,rendered)
    pv.require(nh.verify(*inputs[:8])==before,"PARENT_CHANGED")
    raw=json_bytes(receipt(inputs[7],inputs[9],root,manifest,rendered,output,audit))
    with (output/"motion.json").open("xb") as f:f.write(raw)
    marker.unlink()
    return {"motion_sha256":sha(raw),"frames_compared":audit["frames_compared"],
            "publication_eligible":False}


def verify(inputs,output,motion_pin):
    output=ps.local_dir(output)
    pv.require({p.name for p in output.iterdir()}=={"motion.mp4","motion.json","captions.vtt"},"MOTION_INVENTORY")
    raw=pinned(pv.read(output/"motion.json",pv.MAX_JSON),motion_pin,pv.MAX_JSON)
    root,manifest,rendered,before=prepare(*inputs)
    pv.require(pv.read(output/"captions.vtt",128000)==pv.read(root/"draft"/"captions.vtt",128000),"MOTION_CAPTIONS")
    audit=media_audit(output/"motion.mp4",root,manifest,rendered)
    pv.require(raw==json_bytes(receipt(inputs[7],inputs[9],root,manifest,rendered,output,audit)),"MOTION_RECEIPT")
    pv.require(nh.verify(*inputs[:8])==before,"PARENT_CHANGED")
    return {"motion_sha256":motion_pin,"fresh_media_audit":True,**audit,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("pair","font","visual-request","native","request","output"):
            a.add_argument("--"+name,type=Path,required=True)
        for name in ("pair","font","visual-request","native","request"):
            a.add_argument("--"+name+"-sha256",required=True)
        if mode=="verify":a.add_argument("--motion-sha256",required=True)
    a=p.parse_args()
    try:
        inputs=(a.pair,a.pair_sha256,private_file(a.font,nh.ht.MAX_FONT),a.font_sha256,
                private_file(a.visual_request,nh.MAX_REQUEST),a.visual_request_sha256,
                a.native,a.native_sha256,private_file(a.request,MAX_REQUEST),a.request_sha256)
        result=build(inputs,a.output) if a.mode=="build" else verify(inputs,a.output,a.motion_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
