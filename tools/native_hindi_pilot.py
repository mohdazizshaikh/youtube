"""Explicit private native Hindi derivative of a stopped, pinned bilingual pilot.

Preserve the original pair, evidence, PCM and scene captions. New review queue.
No translation verification, visual acceptance or publication authority.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
import wave
from pathlib import Path

from fontTools.ttLib import TTLibError
from app.domain_draft_video import DraftPlan
from tools import bilingual_pilot as bp, hindi_typography as ht, pilot_pipeline as pp
from tools import pilot_run_verify as pv, native_flow_diagram as flow
from tools.narration_prepare import pinned, private_root, sha
from tools.narration_qc import private_file
from tools.bilingual_snapshot import pair_records

SCHEMA="VIRALOS_NATIVE_HINDI_DERIVATIVE_V1"
REQUEST="VIRALOS_NATIVE_HINDI_REQUEST_V1"
FLOW_REQUEST="VIRALOS_NATIVE_HINDI_FLOW_REQUEST_V1"
TEXT_MODE="DEVANAGARI_RAQM_TEXT_CARDS"
FLOW_MODE="DEVANAGARI_RAQM_FLOW_DIAGRAMS"
VISUAL_MODES=(TEXT_MODE,FLOW_MODE)
MAX_REQUEST=64000
KEY="native_hi_visual_request_v1"


def request_rows(raw,request_pin,pair_pin,font_pin,plan):
    pinned(raw,request_pin,MAX_REQUEST)
    obj=pv.decode(raw)
    pv.require(type(obj) is dict and set(obj)=={"schema","pair_sha256","font_sha256",
               "font_rights_attested","license_reference","scenes"},"REQUEST_FIELDS")
    pv.require(obj["schema"] in (REQUEST,FLOW_REQUEST) and obj["pair_sha256"]==pair_pin
               and obj["font_sha256"]==font_pin,"REQUEST_BINDING")
    pv.require(obj["font_rights_attested"] is True,"FONT_RIGHTS")
    rows=obj["scenes"]
    pv.require(type(rows) is list and len(rows)==len(plan.scenes),"SCENE_COUNT")
    result=[]
    diagram=obj["schema"]==FLOW_REQUEST
    for i,(row,scene) in enumerate(zip(rows,plan.scenes),1):
        fields={"scene","title","nodes","source_declaration_sha256"} if diagram else {"scene","title","claims"}
        pv.require(type(row) is dict and set(row)==fields
                   and type(row["scene"]) is int and row["scene"]==i,"SCENE_FIELDS")
        visual={"schema":flow.SCHEMA if diagram else ht.SCHEMA,"locale":"hi-IN","format":scene.board.format,
                "font_sha256":font_pin,"font_rights_attested":True,
                "license_reference":obj["license_reference"],"title":row["title"]}
        if diagram:
            # Bind the owner's translated diagram to the full original board declaration.
            # This is provenance, not semantic/translation verification.
            original=sha(json.dumps(scene.board.model_dump(),sort_keys=True,ensure_ascii=False).encode())
            pv.require(row["source_declaration_sha256"]==original,"SOURCE_DECLARATION_PIN")
            visual.update(nodes=row["nodes"],source_declaration_sha256=original)
            vraw=bp.json_bytes(visual)
            flow.validate(vraw,sha(vraw),font_pin)
        else:
            pv.require(type(row["claims"]) is list and len(row["claims"])==len(scene.board.claims),
                       "CLAIM_COUNT")
            visual["lines"]=row["claims"]
            vraw=bp.json_bytes(visual)
            ht.validate(vraw,sha(vraw),font_pin)
        result.append(vraw)
    return result


def plans_and_pngs(plan,visuals,font,font_pin,request_pin,pair_pin):
    pinned(font,font_pin,ht.MAX_FONT)
    data=plan.model_dump()
    images={}
    for scene,raw in zip(data["scenes"],visuals):
        facts=scene["board"]["specialist_facts"]
        pv.require(not any(k.startswith("native_hi_") for k in facts),"NATIVE_DECLARATION_EXISTS")
        # Store the exact UTF-8 request as a reserved evidence declaration.
        # Existing schema and auditor remain compatible with historical runs.
        facts[KEY]=raw.decode("utf8")
        facts["native_hi_request_sha256"]=request_pin
        facts["native_hi_parent_pair_sha256"]=pair_pin
        schema=pv.decode(raw)["schema"]
        pv.require(schema in (ht.SCHEMA,flow.SCHEMA),"VISUAL_SCHEMA")
        png,report=(flow.render if schema==flow.SCHEMA else ht.render)(font,font_pin,raw,sha(raw))
        pv.require(report["raqm_used"] is True and report["publication_eligible"] is False,"TYPOGRAPHY_REPORT")
        images[sha(raw)]=png
    return DraftPlan.model_validate(data),images


def prepare(pair,pair_pin,font,font_pin,request,request_pin):
    pair=private_root(pair)
    pv.require({p.name for p in pair.iterdir()}==set(bp.LANGS)|{"pair.json"},"PAIR_INVENTORY")
    raw=pv.read(pair/"pair.json",bp.MAX_BOARDS)
    runs=pair_records(raw,pair_pin)
    obj=pv.decode(raw)
    pv.require(obj.get("visual_text_support")=="ASCII_ONLY","PARENT_VISUAL_MODE")
    for lang in bp.LANGS:
        child=pair/lang
        check=pv.verify(child,runs[lang]["manifest_sha256"],fresh=True)
        manifest=pv.document(child/"draft"/"manifest.json")
        pv.require(manifest["files_sha256"]["draft.mp4"]==runs[lang]["video_sha256"]
                   and manifest["duration_ms"]==runs[lang]["duration_ms"]==obj["duration_ms"],
                   "PARENT_CHILD_BINDING")
    plan=DraftPlan.model_validate(pv.document(pair/"hindi"/"draft"/"plan.json"))
    pv.require(obj["format"]==plan.scenes[0].board.format and obj["domain"]==plan.scenes[0].board.domain
               and obj["synthetic_demo"] is plan.scenes[0].board.synthetic_demo
               and obj["scene_count"]==len(plan.scenes),"PARENT_PLAN")
    visual=request_rows(request,request_pin,pair_pin,font_pin,plan)
    derived,images=plans_and_pngs(plan,visual,font,font_pin,request_pin,pair_pin)
    return obj,derived,images


def renderer(images):
    def render(board,path):
        raw=board.specialist_facts[KEY].encode("utf8")
        png=images[sha(raw)]
        with path.open("xb") as f:
            f.write(png)
        return {"board_sha256":sha(png),"input_sha256":sha(
            json.dumps(board.model_dump(),sort_keys=True,ensure_ascii=False).encode())}
    return render


def check_child(pair,output,plan,images,pin,parent):
    result=pv.verify(output,pin,fresh=True)
    draft=output/"draft"
    actual=DraftPlan.model_validate(pv.document(draft/"plan.json"))
    pv.require(actual.model_dump()==plan.model_dump(),"DERIVATIVE_PLAN")
    manifest=pv.document(draft/"manifest.json")
    original=pv.document(pair/"hindi"/"draft"/"manifest.json")
    pv.require(manifest["duration_ms"]==original["duration_ms"]==parent["duration_ms"]
               and manifest["frames"]==original["frames"] and manifest["fps"]==original["fps"],
               "DERIVATIVE_TIMING")
    for i,scene in enumerate(plan.scenes,1):
        expected=images[sha(scene.board.specialist_facts[KEY].encode("utf8"))]
        pv.require(pv.read(draft/f"scene_{i:02}.png",len(expected))==expected,"DERIVATIVE_PNG")
        old_record=original["scenes"][i-1]
        new_record=manifest["scenes"][i-1]
        for field in ("scene","start_ms","end_ms","frames","narration_input_sha256",
                      "narration_pcm_sha256","caption_text_sha256"):
            pv.require(new_record[field]==old_record[field],"DERIVATIVE_SCENE")
    for name in ("narration.wav","captions.vtt"):
        a=pv.read(draft/name,8*1024*1024)
        b=pv.read(pair/"hindi"/"draft"/name,8*1024*1024)
        if name.endswith(".vtt"):
            a,b=a.replace(b"\r\n",b"\n"),b.replace(b"\r\n",b"\n")
        pv.require(a==b,"DERIVATIVE_AUDIO_CAPTIONS")
    return result,manifest


def visual_mode(plan):
    schemas={pv.decode(s.board.specialist_facts[KEY].encode("utf8"))["schema"] for s in plan.scenes}
    pv.require(schemas in ({ht.SCHEMA},{flow.SCHEMA}),"MIXED_VISUAL_MODE")
    return FLOW_MODE if schemas=={flow.SCHEMA} else TEXT_MODE


def receipt(parent,pair_pin,font_pin,request_pin,manifest,pin,mode=TEXT_MODE):
    pv.require(mode in VISUAL_MODES,"VISUAL_MODE")
    return {"schema":SCHEMA,"parent_pair_sha256":pair_pin,
            "parent_hindi_manifest_sha256":parent["runs"]["hindi"]["manifest_sha256"],
            "english_manifest_sha256":parent["runs"]["english"]["manifest_sha256"],
            "font_sha256":font_pin,"request_sha256":request_pin,"manifest_sha256":pin,
            "video_sha256":manifest["files_sha256"]["draft.mp4"],"duration_ms":manifest["duration_ms"],
            "caption_timing":"SCENE_LEVEL_ONLY","visual_mode":mode,
            "source_evidence_preserved":True,"native_visual_accepted":False,
            "translation_verified":False,"human_review_verified":False,"publication_eligible":False}


def build(pair,pair_pin,font,font_pin,request,request_pin,output):
    pair=private_root(pair)
    from tools.bilingual_compose import destination
    output=destination(output,pair)
    parent,plan,images=prepare(pair,pair_pin,font,font_pin,request,request_pin)
    pv.require(shutil.which("ffmpeg") and shutil.which("ffprobe"),"LOCAL_MEDIA_TOOLS_REQUIRED")
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    with tempfile.TemporaryDirectory(dir=output) as temp:
        path=Path(temp)/"plan.json"
        path.write_bytes(bp.json_bytes(plan.model_dump()))
        report=pp.build(path,pair/"hindi"/"assets",output/"hindi",board_renderer=renderer(images))
    checked,manifest=check_child(pair,output/"hindi",plan,images,report["manifest_sha256"],parent)
    pv.require(checked["queue_state"]=="PENDING" and checked["queue_revision"]==0,"NEW_QUEUE")
    obj=receipt(parent,pair_pin,font_pin,request_pin,manifest,report["manifest_sha256"],visual_mode(plan))
    raw=bp.json_bytes(obj)
    with (output/"native.json").open("xb") as f:
        f.write(raw)
    pv.require(pv.read(output/"native.json",MAX_REQUEST)==raw,"RECEIPT_WRITE")
    marker.unlink()
    return {"native_sha256":sha(raw),"manifest_sha256":report["manifest_sha256"],
            "duration_ms":manifest["duration_ms"],"human_review_required":True,"publication_eligible":False}


def verify(pair,pair_pin,font,font_pin,request,request_pin,output,native_pin):
    pair,output=private_root(pair),private_root(output)
    pv.require({p.name for p in output.iterdir()}=={"native.json","hindi"},"NATIVE_INVENTORY")
    raw=pinned(pv.read(output/"native.json",MAX_REQUEST),native_pin,MAX_REQUEST)
    obj=pv.decode(raw)
    pv.require(type(obj) is dict and obj.get("schema")==SCHEMA,"NATIVE_SCHEMA")
    parent,plan,images=prepare(pair,pair_pin,font,font_pin,request,request_pin)
    checked,manifest=check_child(pair,output/"hindi",plan,images,obj["manifest_sha256"],parent)
    expected=receipt(parent,pair_pin,font_pin,request_pin,manifest,obj["manifest_sha256"],visual_mode(plan))
    pv.require(raw==bp.json_bytes(expected),"NATIVE_RECEIPT")
    en=pv.verify(pair/"english",parent["runs"]["english"]["manifest_sha256"],fresh=False)
    return {"integrity_passed":True,"fresh_media_audit":True,"native_sha256":native_pin,
            "review_states":{"hindi":{"revision":checked["queue_revision"],"state":checked["queue_state"]},
                             "english":{"revision":en["queue_revision"],"state":en["queue_state"]}},
            "human_review_verified":False,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("pair","font","request","output"):
            a.add_argument("--"+name,type=Path,required=True)
        for name in ("pair","font","request"):
            a.add_argument("--"+name+"-sha256",required=True)
        if mode=="verify":
            a.add_argument("--native-sha256",required=True)
    args=p.parse_args()
    try:
        pv.require(args.font.suffix.lower() in (".ttf",".otf"),"FONT_EXTENSION")
        values=(args.pair,args.pair_sha256,private_file(args.font,ht.MAX_FONT),args.font_sha256,
                private_file(args.request,MAX_REQUEST),args.request_sha256,args.output)
        result=build(*values) if args.mode=="build" else verify(*values,args.native_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,
            sqlite3.Error,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
