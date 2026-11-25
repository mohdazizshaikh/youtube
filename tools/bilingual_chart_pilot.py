"""Separate chart-video derivatives of a stopped original bilingual pilot.

All chart sources, data, requests and fonts remain independently pinned owner
inputs. Source bytes are bound to an owner-declared source URL, not authenticated.
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import subprocess
import tempfile
import wave
from pathlib import Path
from fontTools.ttLib import TTLibError
from app.domain_draft_video import DraftPlan
from tools import bilingual_data_chart as chart, bilingual_review_dashboard as dash
from tools import pilot_pipeline as pp,pilot_run_verify as pv,pilot_snapshot as ps
from tools.narration_prepare import pinned,sha
from tools.narration_qc import private_file,MAX_WAV
from tools.bilingual_pilot import json_bytes

REQUEST="VIRALOS_BILINGUAL_CHART_PILOT_REQUEST_V1"
SCHEMA="VIRALOS_BILINGUAL_CHART_PILOT_V1"
KEY="chart_pilot_declaration_v1"
LANGS=chart.LANGS
MAX_REQUEST=64000


def validate(raw,request_pin,pair_pin,count):
    pv.pin(pair_pin)
    obj=pv.decode(pinned(raw,request_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and set(obj)=={"schema","pair_sha256","font_sha256","scenes"}
               and obj["schema"]==REQUEST and obj["pair_sha256"]==pair_pin,"CHART_PILOT_REQUEST")
    fonts=obj["font_sha256"]
    pv.require(type(fonts) is dict and set(fonts)==set(LANGS),"FONTS")
    for value in fonts.values():pv.pin(value)
    rows=obj["scenes"]
    pv.require(pv.exact_int(count,2,8) and type(rows) is list and len(rows)==count,"SCENE_COUNT")
    for i,row in enumerate(rows,1):
        pv.require(type(row) is dict and set(row)=={"scene","source_id","source_sha256",
                   "data_sha256","request_sha256","board_sha256"} and type(row["scene"]) is int
                   and row["scene"]==i,"SCENE_FIELDS")
        import re
        pv.require(type(row["source_id"]) is str and re.fullmatch(r"[A-Z][A-Z0-9]{0,7}",row["source_id"]) is not None,
                   "SOURCE_ID")
        for key in ("source_sha256","data_sha256","request_sha256"):pv.pin(row[key])
        pv.require(type(row["board_sha256"]) is dict and set(row["board_sha256"])==set(LANGS),"BOARD_PINS")
        for pin in row["board_sha256"].values():pv.pin(pin)
    return obj


def board_pin(board):
    return sha(json.dumps(board.model_dump(),sort_keys=True,ensure_ascii=False).encode())


def source_binding(board,row,lang,reference):
    pv.require(not any(k.startswith(("chart_pilot_","native_hi_","production_mix_"))
                       for k in board.specialist_facts),"DERIVATIVE_PARENT")
    pv.require(board_pin(board)==row["board_sha256"][lang],"BOARD_BINDING")
    sources=[s for s in board.sources if s.source_id==row["source_id"]]
    pv.require(len(sources)==1 and str(sources[0].url)==reference,"SOURCE_REFERENCE_BINDING")
    pv.require(any(l.source_id==row["source_id"] and l.relation=="SUPPORTS"
                   for c in board.claims for l in c.links),"SOURCE_NOT_SUPPORTING")


def derive(original,row,lang,chart_receipt,pair_pin,request_pin,png):
    data=original.model_dump()
    facts=data["board"]["specialist_facts"]
    pv.require(not any(k.startswith("chart_pilot_") for k in facts),"DERIVATIVE_PARENT")
    facts[KEY]=json_bytes({"schema":"VIRALOS_CHART_SCENE_DECLARATION_V1","scene":row["scene"],
        "language":lang,"parent_board_sha256":row["board_sha256"][lang],
        "source_id":row["source_id"],"source_sha256":row["source_sha256"],
        "data_sha256":row["data_sha256"],"chart_request_sha256":row["request_sha256"],
        "chart_receipt_sha256":chart_receipt,"png_sha256":sha(png),"pair_sha256":pair_pin,
        "pilot_request_sha256":request_pin,"source_transcription_verified":False}).decode()
    return data


def renderer(images):
    def render(board,path):
        raw=board.specialist_facts[KEY].encode()
        png=images[sha(raw)]
        pv.require(sha(png)==pv.decode(raw)["png_sha256"],"CHART_PNG_PIN")
        with path.open("xb") as f:f.write(png)
        return {"board_sha256":sha(png),"input_sha256":board_pin(board)}
    return render


def prepare(pair,pair_pin,root,request,request_pin,fonts,font_pins):
    pair,root=ps.local_dir(pair),ps.local_dir(root)
    runs,duration=dash.select_runs(pair,pair_pin)
    before=dash.snapshot(runs,duration,fresh=True)
    originals={lang:DraftPlan.model_validate(pv.document(runs[lang][0]/"draft"/"plan.json")) for lang in LANGS}
    count=len(originals["hindi"].scenes)
    spec=validate(request,request_pin,pair_pin,count)
    pv.require(spec["font_sha256"]==font_pins,"FONT_PINS")
    pv.require(len(originals["english"].scenes)==count,"SCENE_COUNT")
    pv.require({p.name for p in root.iterdir()}=={f"scene_{i:02}" for i in range(1,count+1)},"SOURCE_INVENTORY")
    derived={lang:[] for lang in LANGS}
    images={lang:{} for lang in LANGS}
    records=[]
    for i,row in enumerate(spec["scenes"],1):
        folder=ps.local_dir(root/f"scene_{i:02}")
        pv.require({p.name for p in folder.iterdir()}=={"source.bin","data.json","request.json"},"SCENE_INVENTORY")
        source=pv.read(folder/"source.bin",chart.MAX_SOURCE)
        data=pv.read(folder/"data.json",chart.MAX_JSON)
        req=pv.read(folder/"request.json",chart.MAX_JSON)
        dataset=chart.validate_data(data,row["data_sha256"],source,row["source_sha256"])
        for lang in LANGS:
            source_binding(originals[lang].scenes[i-1].board,row,lang,dataset["source_reference"])
        results=chart.prepare(source,row["source_sha256"],data,row["data_sha256"],req,row["request_sha256"],fonts,font_pins)
        receipt=pv.decode(results["chart.json"])
        chart_pin=sha(results["chart.json"])
        for lang in LANGS:
            scene=originals[lang].scenes[i-1]
            pv.require(receipt["format"]==scene.board.format,"CHART_FORMAT")
            png=results[lang+".png"]
            new=derive(scene,row,lang,chart_pin,pair_pin,request_pin,png)
            images[lang][sha(new["board"]["specialist_facts"][KEY].encode())]=png
            derived[lang].append(new)
        records.append({"scene":i,"source_id":row["source_id"],"source_sha256":row["source_sha256"],
                        "data_sha256":row["data_sha256"],"chart_request_sha256":row["request_sha256"],
                        "chart_sha256":chart_pin})
    pv.require(dash.select_runs(pair,pair_pin)==(runs,duration)
               and dash.snapshot(runs,duration)=={**before,"fresh_media_audit":False},"PARENT_CHANGED")
    plans={lang:DraftPlan.model_validate({"scenes":derived[lang]}) for lang in LANGS}
    return runs,duration,before,plans,images,records


def check_child(parent,run,pin,plan,images):
    checked=pv.verify(run,pin,fresh=True)
    original=pv.document(parent/"draft"/"manifest.json")
    actual=pv.document(run/"draft"/"manifest.json")
    pv.require(DraftPlan.model_validate(pv.document(run/"draft"/"plan.json")).model_dump()==plan.model_dump(),
               "CHART_PLAN")
    pv.require(all(actual[k]==original[k] for k in ("domain","format","synthetic_demo","frames","fps","duration_ms")),
               "CHART_TIMING")
    for i,(scene,old,new) in enumerate(zip(plan.scenes,original["scenes"],actual["scenes"]),1):
        pv.require(all(new[k]==old[k] for k in ("scene","start_ms","end_ms","frames","narration_input_sha256",
                   "narration_pcm_sha256","caption_text_sha256")),"CHART_SCENE_TIMING")
        png=images[sha(scene.board.specialist_facts[KEY].encode())]
        pv.require(pv.read(run/"draft"/f"scene_{i:02}.png",len(png))==png,"CHART_PNG")
        name=scene.narration_file
        source=pv.read(parent/"assets"/name,1100000)
        pv.require(pv.read(run/"assets"/name,len(source))==source,"CHART_AUDIO_ASSET")
    for name,limit in (("narration.wav",MAX_WAV),("captions.vtt",128000)):
        a=pv.read(parent/"draft"/name,limit)
        b=pv.read(run/"draft"/name,limit)
        pv.require(a==b if name.endswith(".wav") else a.replace(b"\r\n",b"\n")==b.replace(b"\r\n",b"\n"),
                   "CHART_PARENT_AUDIO_CAPTIONS")
    return {"manifest_sha256":pin,"video_sha256":actual["files_sha256"]["draft.mp4"],
            "duration_ms":actual["duration_ms"]},{"revision":checked["queue_revision"],"state":checked["queue_state"]}


def receipt(pair_pin,request_pin,duration,records,children):
    pv.require(children["hindi"]["manifest_sha256"]!=children["english"]["manifest_sha256"],"DUPLICATE_CHILD")
    return {"schema":SCHEMA,"pair_sha256":pair_pin,"request_sha256":request_pin,
            "duration_ms":duration,"scenes":records,"runs":children,
            "visual_mode":"BILINGUAL_SOURCE_BOUND_CHARTS","caption_timing":"SCENE_LEVEL_ONLY",
            "source_transcription_verified":False,"translation_verified":False,
            "human_review_verified":False,"publication_eligible":False}


def build(inputs,output):
    runs,duration,before,plans,images,records=prepare(*inputs)
    output=ps.new_dir(output,ps.local_dir(inputs[0]))
    ps.new_dir(output,ps.local_dir(inputs[2]))
    output.mkdir(mode=0o700)
    marker=output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    children={}
    with tempfile.TemporaryDirectory(dir=output) as temp:
        for lang in LANGS:
            stage=Path(temp)/lang
            stage.mkdir()
            plan_path=stage/"plan.json"
            plan_path.write_bytes(json_bytes(plans[lang].model_dump()))
            parent,pin,_=runs[lang]
            report=pp.build(plan_path,parent/"assets",output/lang,board_renderer=renderer(images[lang]))
            child,state=check_child(parent,output/lang,report["manifest_sha256"],plans[lang],images[lang])
            pv.require(state=={"revision":0,"state":"PENDING"} and child["manifest_sha256"]!=pin,"NEW_QUEUE")
            children[lang]=child
    pv.require(dash.select_runs(inputs[0],inputs[1])==(runs,duration)
               and dash.snapshot(runs,duration)=={**before,"fresh_media_audit":False},"PARENT_CHANGED")
    raw=json_bytes(receipt(inputs[1],inputs[4],duration,records,children))
    ps.write_json(output/"chart_pair.json",pv.decode(raw))
    # Snapshot writer may use different JSON whitespace; pin actual bytes.
    actual=pv.read(output/"chart_pair.json",MAX_REQUEST)
    pv.require(pv.decode(actual)==pv.decode(raw),"RECEIPT_WRITE")
    marker.unlink()
    return {"chart_pair_sha256":sha(actual),"runs":children,"duration_ms":duration,"publication_eligible":False}


def verify(inputs,output,chart_pair_pin):
    output=ps.local_dir(output)
    pv.require({p.name for p in output.iterdir()}==set(LANGS)|{"chart_pair.json"},"CHART_PAIR_INVENTORY")
    obj=pv.decode(pinned(pv.read(output/"chart_pair.json",MAX_REQUEST),chart_pair_pin,MAX_REQUEST))
    pv.require(type(obj) is dict and obj.get("schema")==SCHEMA and type(obj.get("runs")) is dict
               and set(obj["runs"])==set(LANGS),"CHART_PAIR_SCHEMA")
    runs,duration,before,plans,images,records=prepare(*inputs)
    children,states={},{}
    for lang in LANGS:
        parent,pin,_=runs[lang]
        child_pin=pv.pin(obj["runs"][lang]["manifest_sha256"])
        pv.require(child_pin!=pin,"DERIVATIVE_IDENTITY")
        children[lang],states[lang]=check_child(parent,output/lang,child_pin,plans[lang],images[lang])
    pv.require(obj==receipt(inputs[1],inputs[4],duration,records,children),"CHART_PAIR_RECEIPT")
    pv.require(dash.select_runs(inputs[0],inputs[1])==(runs,duration)
               and dash.snapshot(runs,duration)=={**before,"fresh_media_audit":False},"PARENT_CHANGED")
    return {"chart_pair_sha256":chart_pair_pin,"fresh_media_audit":True,"review_states":states,
            "duration_ms":duration,"publication_eligible":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a=sub.add_parser(mode)
        for name in ("pair","root","request","hindi-font","english-font","output"):
            a.add_argument("--"+name,type=Path,required=True)
        for name in ("pair","request","hindi-font","english-font"):
            a.add_argument("--"+name+"-sha256",required=True)
        if mode=="verify":a.add_argument("--chart-pair-sha256",required=True)
    a=p.parse_args()
    try:
        inputs=(a.pair,a.pair_sha256,a.root,private_file(a.request,MAX_REQUEST),a.request_sha256,
                {l:private_file(getattr(a,l+"_font"),chart.ht.MAX_FONT) for l in LANGS},
                {l:getattr(a,l+"_font_sha256") for l in LANGS})
        result=build(inputs,a.output) if a.mode=="build" else verify(inputs,a.output,a.chart_pair_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,sqlite3.Error,
            subprocess.SubprocessError,TTLibError,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
