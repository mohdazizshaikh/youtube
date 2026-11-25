"""Separate synchronized mastered-narration video derivatives of a stopped original pair."""
from __future__ import annotations
import argparse
import json
import sqlite3
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

from app.domain_draft_video import DraftPlan
from tools import bilingual_dynamics as bd,bilingual_review_dashboard as dash
from tools import pilot_pipeline as pp,pilot_run_verify as pv,pilot_snapshot as ps
from tools import production_mix_pilot as pm
from tools.narration_prepare import pinned,sha
from tools.narration_qc import MAX_WAV,private_file
from tools.bilingual_pilot import json_bytes

REQUEST="VIRALOS_PAIRED_MASTERED_PILOT_REQUEST_V1"
SCHEMA="VIRALOS_PAIRED_MASTERED_PILOT_V1"
KEY="mastered_pilot_scene_v1"
MAX_REQUEST=64000
LANGS=bd.LANGS
RESERVED=("mastered_pilot_","production_mix_","native_hi_","chart_pilot_")


def validate(raw,request_pin,pair_pin):
    pv.pin(pair_pin)
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","pair_sha256","audio_request"}
               and obj["schema"]==REQUEST and obj["pair_sha256"]==pair_pin,"REQUEST_BINDING")
    sub=json_bytes(obj["audio_request"])
    bd.validate(sub,sha(sub))
    return obj,sub


def check_schedule(manifest,rows,duration):
    pv.require(manifest["fps"]==25 and manifest["duration_ms"]==duration
               and manifest["frames"]*40==duration and len(manifest["scenes"])==len(rows),
               "PARENT_TIMING")
    pos=0
    for i,(scene,row) in enumerate(zip(manifest["scenes"],rows),1):
        end=pos+row["frames"]*40
        pv.require(scene["scene"]==row["scene"]==i and scene["frames"]==row["frames"]
                   and scene["start_ms"]==pos and scene["end_ms"]==end,"PARENT_SCENE_TIMING")
        pos=end
    pv.require(pos==duration,"PARENT_TOTAL")


def derive(original,manifest,lang,assets,pair_pin,request_pin,audio_pin,parent_pin):
    data=original.model_dump()
    pv.require(len(data["scenes"])==len(manifest["scenes"]),"PLAN_SCENES")
    for i,(scene,row) in enumerate(zip(data["scenes"],manifest["scenes"]),1):
        facts=scene["board"]["specialist_facts"]
        pv.require(not any(k.startswith(RESERVED) for k in facts),"DERIVATIVE_PARENT")
        name=f"{lang}_{i:02}.wav"
        facts[KEY]=str(i)
        facts["mastered_pilot_parent_pair_sha256"]=pair_pin
        facts["mastered_pilot_parent_manifest_sha256"]=parent_pin
        facts["mastered_pilot_request_sha256"]=request_pin
        facts["mastered_pilot_audio_bundle_sha256"]=audio_pin
        facts["mastered_pilot_original_board_sha256"]=row["board_sha256"]
        facts["mastered_pilot_original_narration_sha256"]=scene["narration_sha256"]
        facts["mastered_pilot_audio_kind"]="DYNAMICS_PROCESSED_NARRATION"
        scene["narration_file"]=name
        scene["narration_sha256"]=sha(assets[name])
    return DraftPlan.model_validate(data)


def renderer(boards):
    def render(board,path):
        raw=boards[board.specialist_facts[KEY]]
        pv.require(sha(raw)==board.specialist_facts["mastered_pilot_original_board_sha256"],
                   "BOARD_BINDING")
        with path.open("xb") as f:f.write(raw)
        return {"board_sha256":sha(raw),"input_sha256":sha(
            json.dumps(board.model_dump(),sort_keys=True,ensure_ascii=False).encode())}
    return render


def parent_unchanged(pair,pair_pin,runs,duration,before):
    pv.require(dash.select_runs(pair,pair_pin)==(runs,duration) and
               dash.snapshot(runs,duration)=={**before,"fresh_media_audit":False},"PARENT_CHANGED")


def prepare(pair,pair_pin,request,request_pin):
    obj,sub=validate(request,request_pin,pair_pin)
    pair=ps.local_dir(pair)
    runs,duration=dash.select_runs(pair,pair_pin)
    before=dash.snapshot(runs,duration,fresh=True)
    voices,plans,manifests,boards={},{},{},{}
    for lang,(parent,pin,_) in runs.items():
        manifest=pv.document(parent/"draft"/"manifest.json")
        check_schedule(manifest,obj["audio_request"]["scenes"],duration)
        original=DraftPlan.model_validate(pv.document(parent/"draft"/"plan.json"))
        pv.require(not any(k.startswith(RESERVED) for s in original.scenes
                           for k in s.board.specialist_facts),"DERIVATIVE_PARENT")
        voice=pv.read(parent/"draft"/"narration.wav",MAX_WAV)
        pv.require(sha(voice)==manifest["files_sha256"]["narration.wav"]==
                   obj["audio_request"]["tracks"][lang]["voice_sha256"],"PARENT_VOICE_PIN")
        voices[lang]=voice
        manifests[lang]=manifest
        plans[lang]=original
        boards[lang]={}
        for i,row in enumerate(manifest["scenes"],1):
            png=pv.read(parent/"draft"/f"scene_{i:02}.png",8*1024*1024)
            pv.require(sha(png)==row["board_sha256"],"PARENT_BOARD_PIN")
            boards[lang][str(i)]=png
    assets,audio=bd.prepare(voices,sub,sha(sub))
    audio_pin=sha(assets["pair_dynamics.json"])
    pv.require(audio["duration_ms"]==duration and audio["publication_eligible"] is False,
               "AUDIO_BINDING")
    derived={lang:derive(plans[lang],manifests[lang],lang,assets,pair_pin,request_pin,audio_pin,
                        runs[lang][1]) for lang in LANGS}
    parent_unchanged(pair,pair_pin,runs,duration,before)
    return runs,duration,before,derived,manifests,boards,assets,audio


def audit_child(parent,run,pin,plan,old,boards,assets,audio,lang):
    checked=pv.verify(run,pin,fresh=True)
    draft=run/"draft"
    actual=pv.document(draft/"manifest.json")
    pv.require(DraftPlan.model_validate(pv.document(draft/"plan.json")).model_dump()==plan.model_dump(),
               "DERIVATIVE_PLAN")
    pv.require(all(actual[k]==old[k] for k in ("domain","format","synthetic_demo","fps","frames","duration_ms"))
               and len(actual["scenes"])==len(old["scenes"]),"DERIVATIVE_TIMING")
    for i,(scene,original) in enumerate(zip(actual["scenes"],old["scenes"]),1):
        pv.require(all(scene[k]==original[k] for k in ("scene","start_ms","end_ms","frames","board_sha256",
                   "caption_text_sha256")),"DERIVATIVE_SCENE")
        png=boards[str(i)]
        pv.require(pv.read(draft/f"scene_{i:02}.png",len(png))==png,"DERIVATIVE_BOARD")
        name=f"{lang}_{i:02}.wav"
        pv.require(pv.read(run/"assets"/name,len(assets[name]))==assets[name],"DERIVATIVE_ASSET")
    pv.require(bd.mix.samples(pv.read(draft/"narration.wav",MAX_WAV))==
               bd.mix.samples(assets[lang+"_master.wav"]),"DERIVATIVE_MASTER")
    caps=lambda path:pv.read(path,128000).replace(b"\r\n",b"\n")
    pv.require(caps(draft/"captions.vtt")==caps(parent/"draft"/"captions.vtt"),"DERIVATIVE_CAPTIONS")
    encoded=pm.encoded_measure(draft/"draft.mp4",actual["frames"]*640,audio["ceiling_dbtp"])
    return {"manifest_sha256":pin,"video_sha256":actual["files_sha256"]["draft.mp4"],
            "duration_ms":actual["duration_ms"],"decoded_16khz_audio":encoded}, {
            "revision":checked["queue_revision"],"state":checked["queue_state"]}


def receipt(pair_pin,request_pin,duration,assets,audio,children):
    pv.require(children["hindi"]["manifest_sha256"]!=children["english"]["manifest_sha256"],
               "DUPLICATE_CHILD")
    return {"schema":SCHEMA,"pair_sha256":pair_pin,"request_sha256":request_pin,
            "audio_bundle_sha256":sha(assets["pair_dynamics.json"]),"duration_ms":duration,
            "audio_report":audio,"runs":children,"visual_bytes_preserved":True,
            "caption_timing":"SCENE_LEVEL_ONLY","human_listening_required":True,
            "professional_mastering_verified":False,"word_alignment_verified":False,
            "human_review_verified":False,"publication_eligible":False}


def build(pair,pair_pin,request,request_pin,output):
    pair=ps.local_dir(pair)
    output=ps.new_dir(output,pair)
    runs,duration,before,plans,manifests,boards,assets,audio=prepare(pair,pair_pin,request,request_pin)
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    children={}
    with tempfile.TemporaryDirectory(dir=output) as temp:
        for lang in LANGS:
            stage=Path(temp)/lang
            stage.mkdir()
            for scene in plans[lang].scenes:
                (stage/scene.narration_file).write_bytes(assets[scene.narration_file])
            plan_path=Path(temp)/(lang+".json")
            plan_path.write_bytes(json_bytes(plans[lang].model_dump()))
            result=pp.build(plan_path,stage,output/lang,board_renderer=renderer(boards[lang]))
            pin=result["manifest_sha256"]
            child,state=audit_child(runs[lang][0],output/lang,pin,plans[lang],manifests[lang],
                                   boards[lang],assets,audio,lang)
            pv.require(pin!=runs[lang][1] and state=={"revision":0,"state":"PENDING"},"NEW_QUEUE")
            children[lang]=child
    parent_unchanged(pair,pair_pin,runs,duration,before)
    # Retain exact recomputable audio receipt; master and scene audio already
    # reside in each child's draft and staged asset directories.
    bd.dynamics.write(output/"pair_dynamics.json",assets["pair_dynamics.json"])
    raw=json_bytes(receipt(pair_pin,request_pin,duration,assets,audio,children))
    bd.dynamics.write(output/"mastered_pair.json",raw)
    pv.require({x.name for x in output.iterdir()}==set(LANGS)|{"pair_dynamics.json","mastered_pair.json","INCOMPLETE"},
               "PAIR_INVENTORY")
    marker.unlink()
    return {"mastered_pair_sha256":sha(raw),"runs":children,"duration_ms":duration,
            "publication_eligible":False}


def verify(pair,pair_pin,request,request_pin,output,mastered_pin):
    output=ps.local_dir(output)
    pv.require({x.name for x in output.iterdir()}==set(LANGS)|{"pair_dynamics.json","mastered_pair.json"},
               "PAIR_INVENTORY")
    raw=pinned(pv.read(output/"mastered_pair.json",pv.MAX_JSON),mastered_pin,pv.MAX_JSON)
    obj=pv.decode(raw)
    pv.require(type(obj) is dict and obj.get("schema")==SCHEMA and type(obj.get("runs")) is dict
               and set(obj["runs"])==set(LANGS),"MASTERED_SCHEMA")
    runs,duration,before,plans,manifests,boards,assets,audio=prepare(pair,pair_pin,request,request_pin)
    pv.require(pv.read(output/"pair_dynamics.json",pv.MAX_JSON)==assets["pair_dynamics.json"],"AUDIO_RECEIPT")
    children,states={},{}
    for lang in LANGS:
        pin=pv.pin(obj["runs"][lang]["manifest_sha256"])
        pv.require(pin!=runs[lang][1],"DERIVATIVE_IDENTITY")
        children[lang],states[lang]=audit_child(runs[lang][0],output/lang,pin,plans[lang],
                         manifests[lang],boards[lang],assets,audio,lang)
    pv.require(raw==json_bytes(receipt(pair_pin,request_pin,duration,assets,audio,children)),"MASTERED_RECEIPT")
    parent_unchanged(pair,pair_pin,runs,duration,before)
    return {"mastered_pair_sha256":mastered_pin,"duration_ms":duration,"review_states":states,
            "fresh_media_audit":True,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("pair","request","output"):a.add_argument("--"+name,type=Path,required=True)
        for name in ("pair","request"):a.add_argument("--"+name+"-sha256",required=True)
        if mode=="verify":a.add_argument("--mastered-pair-sha256",required=True)
    a=p.parse_args()
    try:
        args=(a.pair,a.pair_sha256,private_file(a.request,MAX_REQUEST),a.request_sha256,a.output)
        result=build(*args) if a.mode=="build" else verify(*args,a.mastered_pair_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,struct.error,
            OverflowError,sqlite3.Error,subprocess.SubprocessError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
