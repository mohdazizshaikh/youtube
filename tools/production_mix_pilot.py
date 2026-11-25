"""Separate, pinned music-mix derivative of a stopped pilot; never a release gate.

The child narration assets contain mixed PCM. Original clean narration remains
in the parent; captions and scene timing are unchanged. No automatic substitution.
"""
from __future__ import annotations
import argparse
import json
import shutil
import sqlite3
import subprocess
import tempfile
import wave
from pathlib import Path

from app.domain_draft_video import DraftPlan
from tools import pilot_run_verify as pv, pilot_pipeline as pp, pilot_snapshot as ps
from tools import narration_mix as mix, narration_duck as duck, narration_loudness as loud
from tools.narration_prepare import pinned, sha
from tools.narration_qc import MAX_WAV, RATE, private_file, analyze_pcm
from tools.bilingual_pilot import json_bytes

REQUEST="VIRALOS_PRODUCTION_MIX_REQUEST_V1"
SCHEMA="VIRALOS_PRODUCTION_MIX_PILOT_V1"
MAX_REQUEST=48000
KEY="production_mix_scene_v1"


def validate(raw,request_pin,parent_pin):
    pv.pin(parent_pin)
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","parent_manifest_sha256","mode","audio_request"}
               and obj["schema"]==REQUEST and obj["parent_manifest_sha256"]==parent_pin,
               "REQUEST_BINDING")
    pv.require(obj["mode"] in ("STATIC","DUCK"),"MIX_MODE")
    sub=json_bytes(obj["audio_request"])
    if obj["mode"]=="STATIC":
        mix.validate(sub,sha(sub))
    else:
        duck.validate(sub,sha(sub))
    return obj,sub


def split_master(raw,records):
    qc=analyze_pcm(raw)
    samples=mix.samples(raw)
    pv.require(type(records) is list and 2<=len(records)<=8,"SCENE_COUNT")
    pos=0
    chunks={}
    for i,row in enumerate(records,1):
        pv.require(type(row) is dict and type(row["scene"]) is int and row["scene"]==i
                   and pv.exact_int(row["frames"],13,750)
                   and type(row["start_ms"]) is int and type(row["end_ms"]) is int,
                   "SCENE_RECORD")
        count=row["frames"]*640
        pv.require(row["start_ms"]*16==pos and row["end_ms"]*16==pos+count
                   and pos+count<=len(samples),"SCENE_BOUNDARY")
        name=f"mixed_{i:02}.wav"
        part=mix.wav(samples[pos:pos+count])
        pv.require(any(samples[pos:pos+count]),"SILENT_MIX_SCENE")
        chunks[name]=part
        pos+=count
    pv.require(pos==qc["frames"]==len(samples),"MIX_TOTAL")
    return chunks


def derive_plan(original,records,chunks,parent_pin,request_pin,master_pin,music_pin,mode):
    data=original.model_dump()
    pv.require(len(data["scenes"])==len(records)==len(chunks),"SCENE_COUNT")
    for i,(scene,record) in enumerate(zip(data["scenes"],records),1):
        facts=scene["board"]["specialist_facts"]
        pv.require(not any(k.startswith("production_mix_") for k in facts),"ALREADY_MIXED")
        facts[KEY]=str(i)
        facts["production_mix_parent_manifest_sha256"]=parent_pin
        facts["production_mix_request_sha256"]=request_pin
        facts["production_mix_master_sha256"]=master_pin
        facts["production_mix_music_sha256"]=music_pin
        facts["production_mix_mode"]=mode
        facts["production_mix_original_narration_sha256"]=scene["narration_sha256"]
        facts["production_mix_original_board_sha256"]=record["board_sha256"]
        facts["production_mix_audio_kind"]="MIXED_VOICE_AND_MUSIC"
        name=f"mixed_{i:02}.wav"
        scene["narration_file"]=name
        scene["narration_sha256"]=sha(chunks[name])
    return DraftPlan.model_validate(data)


def prepare(parent,parent_pin,music,request,request_pin):
    parent=ps.local_dir(parent)
    obj,sub=validate(request,request_pin,parent_pin)
    checked=pv.verify(parent,parent_pin,fresh=True)
    manifest=pv.document(parent/"draft"/"manifest.json")
    original=DraftPlan.model_validate(pv.document(parent/"draft"/"plan.json"))
    pv.require(not any(k.startswith("production_mix_") for s in original.scenes
                       for k in s.board.specialist_facts),"ALREADY_MIXED")
    voice=pv.read(parent/"draft"/"narration.wav",MAX_WAV)
    cfg=obj["audio_request"] if obj["mode"]=="STATIC" else obj["audio_request"]["mix"]
    pv.require(sha(voice)==cfg["voice_sha256"]==manifest["files_sha256"]["narration.wav"],
               "PARENT_VOICE_PIN")
    pinned(music,cfg["music_sha256"],MAX_WAV)
    mixed,report=(mix.mix if obj["mode"]=="STATIC" else duck.duck)(voice,music,sub,sha(sub))
    chunks=split_master(mixed,manifest["scenes"])
    plan=derive_plan(original,manifest["scenes"],chunks,parent_pin,request_pin,
                     sha(mixed),cfg["music_sha256"],obj["mode"])
    boards={}
    for i,row in enumerate(manifest["scenes"],1):
        raw=pv.read(parent/"draft"/f"scene_{i:02}.png",8*1024*1024)
        pv.require(sha(raw)==row["board_sha256"],"PARENT_BOARD_PIN")
        boards[str(i)]=raw
    pv.require(pv.verify(parent,parent_pin,fresh=False)=={**checked,"fresh_media_audit":False},
               "PARENT_CHANGED")
    return plan,chunks,boards,mixed,manifest,obj,report


def renderer(boards):
    def render(board,path):
        raw=boards[board.specialist_facts[KEY]]
        pv.require(sha(raw)==board.specialist_facts["production_mix_original_board_sha256"],
                   "BOARD_BINDING")
        with path.open("xb") as f:f.write(raw)
        return {"board_sha256":sha(raw),"input_sha256":sha(
            json.dumps(board.model_dump(),sort_keys=True,ensure_ascii=False).encode())}
    return render


def encoded_measure(path,expected_frames,ceiling):
    # Measure decoded AAC at 16k PCM, not container metadata. This is explicitly
    # a decoded 16 kHz diagnostic, not native-rate codec true-peak certification.
    from app.m25_audio_conformance import _decoded_track
    exe=shutil.which("ffmpeg")
    pv.require(bool(exe),"LOCAL_FFMPEG_REQUIRED")
    pcm=_decoded_track(path,exe)
    pv.require(abs(len(pcm)-expected_frames)<=RATE*0.15,"ENCODED_DURATION")
    raw=mix.wav(pcm)
    report=loud.measure(raw,sha(raw))
    pv.require(report["true_peak_dbtp"]<=ceiling,"ENCODED_TRUE_PEAK")
    return report


def audit_child(parent,run,pin,prepared):
    plan,chunks,boards,mixed,old,obj,report=prepared
    checked=pv.verify(run,pin,fresh=True)
    draft=run/"draft"
    manifest=pv.document(draft/"manifest.json")
    actual=DraftPlan.model_validate(pv.document(draft/"plan.json"))
    pv.require(actual.model_dump()==plan.model_dump(),"DERIVATIVE_PLAN")
    pv.require(all(manifest[k]==old[k] for k in ("domain","format","synthetic_demo","fps","frames","duration_ms")),
               "DERIVATIVE_IDENTITY")
    for i,(a,b) in enumerate(zip(manifest["scenes"],old["scenes"]),1):
        pv.require(all(a[k]==b[k] for k in ("scene","start_ms","end_ms","frames","board_sha256",
                                          "caption_text_sha256")),"DERIVATIVE_SCENE")
        raw=boards[str(i)]
        pv.require(pv.read(draft/f"scene_{i:02}.png",len(raw))==raw,"DERIVATIVE_BOARD")
        name=f"mixed_{i:02}.wav"
        pv.require(pv.read(run/"assets"/name,len(chunks[name]))==chunks[name],"DERIVATIVE_ASSET")
    master=pv.read(draft/"narration.wav",MAX_WAV)
    pv.require(mix.samples(master)==mix.samples(mixed),"DERIVATIVE_MASTER")
    caps=lambda path:pv.read(path,128000).replace(b"\r\n",b"\n")
    pv.require(caps(draft/"captions.vtt")==caps(parent/"draft"/"captions.vtt"),"DERIVATIVE_CAPTIONS")
    cfg=obj["audio_request"] if obj["mode"]=="STATIC" else obj["audio_request"]["mix"]
    encoded=encoded_measure(draft/"draft.mp4",manifest["frames"]*640,cfg["ceiling_dbtp"])
    return checked,manifest,encoded


def receipt(parent_pin,request_pin,pin,prepared,manifest,encoded):
    _,_,_,mixed,old,obj,report=prepared
    return {"schema":SCHEMA,"parent_manifest_sha256":parent_pin,"request_sha256":request_pin,
            "manifest_sha256":pin,"parent_video_sha256":old["files_sha256"]["draft.mp4"],
            "video_sha256":manifest["files_sha256"]["draft.mp4"],
            "mixed_master_sha256":sha(mixed),"duration_ms":manifest["duration_ms"],"mode":obj["mode"],
            "mix_report":report,"decoded_16khz_audio":encoded,"visual_bytes_preserved":True,
            "caption_timing":"SCENE_LEVEL_ONLY","original_voice_retained_in_parent":True,
            "human_listening_required":True,"speech_intelligibility_verified":False,
            "native_visual_accepted":False,"human_review_verified":False,"publication_eligible":False}


def build(parent,parent_pin,music,request,request_pin,output):
    parent=ps.local_dir(parent)
    output=ps.new_dir(output,parent)
    prepared=prepare(parent,parent_pin,music,request,request_pin)
    plan,chunks,boards,*_=prepared
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    with tempfile.TemporaryDirectory(dir=output) as temp:
        stage=Path(temp)
        assets=stage/"assets"
        assets.mkdir()
        for name,raw in chunks.items():
            with (assets/name).open("xb") as f:f.write(raw)
        plan_path=stage/"plan.json"
        plan_path.write_bytes(json_bytes(plan.model_dump()))
        result=pp.build(plan_path,assets,output/"run",board_renderer=renderer(boards))
    pin=result["manifest_sha256"]
    checked,manifest,encoded=audit_child(parent,output/"run",pin,prepared)
    pv.require(checked["queue_state"]=="PENDING" and checked["queue_revision"]==0,"NEW_QUEUE")
    raw=json_bytes(receipt(parent_pin,request_pin,pin,prepared,manifest,encoded))
    with (output/"mix.json").open("xb") as f:f.write(raw)
    pv.require(pv.read(output/"mix.json",MAX_REQUEST)==raw,"RECEIPT_WRITE")
    pv.require({x.name for x in output.iterdir()}=={"run","mix.json","INCOMPLETE"},"MIX_INVENTORY")
    marker.unlink()
    return {"mix_sha256":sha(raw),"manifest_sha256":pin,"duration_ms":manifest["duration_ms"],
            "human_listening_required":True,"publication_eligible":False}


def verify(parent,parent_pin,music,request,request_pin,output,mix_pin):
    parent,output=ps.local_dir(parent),ps.local_dir(output)
    pv.require({x.name for x in output.iterdir()}=={"run","mix.json"},"MIX_INVENTORY")
    raw=pinned(pv.read(output/"mix.json",MAX_REQUEST),mix_pin,MAX_REQUEST)
    obj=pv.decode(raw)
    pv.require(type(obj) is dict and obj.get("schema")==SCHEMA,"MIX_SCHEMA")
    prepared=prepare(parent,parent_pin,music,request,request_pin)
    pin=obj["manifest_sha256"]
    checked,manifest,encoded=audit_child(parent,output/"run",pin,prepared)
    pv.require(raw==json_bytes(receipt(parent_pin,request_pin,pin,prepared,manifest,encoded)),
               "MIX_RECEIPT")
    return {"integrity_passed":True,"fresh_media_audit":True,"mix_sha256":mix_pin,
            "queue_state":checked["queue_state"],"queue_revision":checked["queue_revision"],
            "human_listening_required":True,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("parent","music","request","output"):
            a.add_argument("--"+name,type=Path,required=True)
        a.add_argument("--parent-sha256",required=True)
        a.add_argument("--request-sha256",required=True)
        if mode=="verify":a.add_argument("--mix-sha256",required=True)
    a=p.parse_args()
    try:
        args=(a.parent,a.parent_sha256,private_file(a.music,MAX_WAV),
              private_file(a.request,MAX_REQUEST),a.request_sha256,a.output)
        result=build(*args) if a.mode=="build" else verify(*args,a.mix_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,
            sqlite3.Error,subprocess.SubprocessError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
