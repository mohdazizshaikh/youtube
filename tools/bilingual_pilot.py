"""Build and re-audit paired local pilot videos from a pinned bilingual audio bundle.

Existing storyboard renderer remains ASCII-only. No speech, translation, rights
or human review verification, and no account or publishing integration.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
import wave
from pathlib import Path

from app.domain_draft_video import DraftPlan
from tools import bilingual_compose as bc, pilot_pipeline as pp, pilot_run_verify as pv
from tools.narration_prepare import private_root, pinned, sha
from tools.narration_qc import private_file

LANGS = ("hindi", "english")
SCHEMA = "VIRALOS_BILINGUAL_PILOT_V1"
BOARD_SCHEMA = "VIRALOS_BILINGUAL_PILOT_BOARDS_V1"
MAX_BOARDS = 512000


def json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)+"\n").encode("utf8")


def validate_boards(raw, board_pin, audio_manifest, bundle_pin, captions):
    pinned(raw, board_pin, MAX_BOARDS)
    data = pv.decode(raw)
    pv.require(type(data) is dict and set(data) == {"schema", "bundle_manifest_sha256", "scenes"}
               and data["schema"] == BOARD_SCHEMA and data["bundle_manifest_sha256"] == bundle_pin,
               "BOARD_REQUEST")
    rows = data["scenes"]
    pv.require(type(rows) is list and len(rows) == len(audio_manifest["scenes"]), "BOARD_COUNT")
    plans = {lang: [] for lang in LANGS}
    for i, (row, audio, caption) in enumerate(zip(rows, audio_manifest["scenes"], captions), 1):
        pv.require(type(row) is dict and set(row) == {"scene","hindi","english","rights_attested"}
                   and type(row["scene"]) is int and row["scene"] == i, "BOARD_SCENE")
        pv.require(type(row["rights_attested"]) is dict and set(row["rights_attested"]) == set(LANGS)
                   and all(row["rights_attested"][lang] is True for lang in LANGS), "OWNER_RIGHTS_REQUIRED")
        for lang in LANGS:
            board = row[lang]
            pv.require(type(board) is dict and type(board.get("synthetic_demo")) is bool, "BOARD_DEMO_TYPE")
            pv.require(board.get("format") == audio_manifest["format"], "BOARD_FORMAT")
            name = audio[lang]["file"]
            plans[lang].append({"board": board, "narration_file": name,
                "narration_sha256": audio_manifest["files"][name]["sha256"],
                "narration_text": caption[lang], "rights_attested": True})
    result = {lang: DraftPlan.model_validate({"scenes": plans[lang]}) for lang in LANGS}
    for hi, en in zip(result["hindi"].scenes, result["english"].scenes):
        h, e = hi.board, en.board
        pv.require((h.domain,h.format,h.synthetic_demo) == (e.domain,e.format,e.synthetic_demo),
                   "PAIR_BOARD_IDENTITY")
        # Both versions reference exactly the same declared evidence. No claim
        # equivalence or translation assertion is inferred from shared sources.
        pv.require(sorted((s.model_dump() for s in h.sources),key=lambda s:s["source_id"]) ==
                   sorted((s.model_dump() for s in e.sources),key=lambda s:s["source_id"]),
                   "PAIR_SOURCE_DECLARATIONS")
        pv.require(len(h.claims) == len(e.claims), "PAIR_CLAIM_COUNT")
        for hc, ec in zip(h.claims,e.claims):
            pv.require(sorted((l.model_dump() for l in hc.links),key=lambda l:l["source_id"]) ==
                       sorted((l.model_dump() for l in ec.links),key=lambda l:l["source_id"]),
                       "PAIR_CLAIM_LINKS")
    return result


def prepare(root, request, request_pin, captions, captions_pin, bundle, bundle_pin,
            boards, board_pin):
    root, bundle = private_root(root), private_root(bundle)
    outputs, manifest = bc.prepare(root, request, request_pin, captions, captions_pin)
    pinned(outputs["manifest.json"], bundle_pin, bc.MAX_REQUEST)
    pv.require({p.name for p in bundle.iterdir()} == set(outputs), "BUNDLE_INVENTORY")
    for name, raw in outputs.items():
        pv.require(pv.read(bundle/name,len(raw)) == raw, "BUNDLE_BYTES")
    caption_rows = bc.load_captions(captions,captions_pin,request_pin,pv.decode(request))
    plans = validate_boards(boards,board_pin,manifest,bundle_pin,caption_rows)
    return outputs, manifest, plans


def audit_run(run, lang, expected, audio, plan, run_pin):
    checked = pv.verify(run,run_pin,fresh=True)
    draft = run/"draft"
    manifest = pv.document(draft/"manifest.json")
    actual = DraftPlan.model_validate(pv.document(draft/"plan.json"))
    pv.require(actual.model_dump() == plan.model_dump(), "PILOT_PLAN_MISMATCH")
    pv.require(manifest["duration_ms"] == audio["duration_ms"] and manifest["fps"] == 25
               and manifest["frames"]*640 == audio["total_samples_per_track"], "PILOT_TIMING")
    for scene, scheduled in zip(manifest["scenes"],audio["scenes"]):
        pv.require(scene["start_ms"] == scheduled["start_ms"] and scene["end_ms"] == scheduled["end_ms"]
                   and scene["frames"] == scheduled["video_frames"], "PILOT_SCENE_TIMING")
    for scene in plan.scenes:
        raw = expected[scene.narration_file]
        pv.require(pv.read(run/"assets"/scene.narration_file,len(raw)) == raw, "PILOT_ASSET_BYTES")
    # Compare exact WAV PCM, not RIFF header bytes (the writer can differ).
    def pcm(raw):
        import io
        with wave.open(io.BytesIO(raw),"rb") as w:
            pv.require((w.getnchannels(),w.getsampwidth(),w.getframerate()) == (1,2,16000),"PILOT_PCM_FORMAT")
            return w.readframes(w.getnframes())
    master = expected[lang+".wav"]
    pv.require(pcm(pv.read(draft/"narration.wav",bc.MAX_WAV)) == pcm(master), "PILOT_MASTER_PCM")
    # Windows text-mode writers may emit CRLF; normalize only newline encoding.
    vtt = pv.read(draft/"captions.vtt",bc.MAX_CAPTIONS).replace(b"\r\n",b"\n")
    pv.require(vtt == expected[lang+".vtt"], "PILOT_CAPTIONS")
    return {"manifest_sha256":run_pin,"video_sha256":manifest["files_sha256"]["draft.mp4"],
            "duration_ms":manifest["duration_ms"],"queue_revision":checked["queue_revision"],
            "queue_state":checked["queue_state"],"publication_eligible":False}


def receipt(request_pin,captions_pin,bundle_pin,board_pin,audio,plans,runs):
    return {"schema":SCHEMA,"timing_request_sha256":request_pin,"captions_request_sha256":captions_pin,
            "audio_bundle_manifest_sha256":bundle_pin,"boards_sha256":board_pin,
            "duration_ms":audio["duration_ms"],"scene_count":len(audio["scenes"]),
            "domain":plans["hindi"].scenes[0].board.domain,"format":audio["format"],
            "synthetic_demo":plans["hindi"].scenes[0].board.synthetic_demo,
            "english_locale":audio["english_locale"],"runs":runs,
            "visual_text_support":"ASCII_ONLY","caption_timing":"SCENE_LEVEL_ONLY",
            "translation_verified":False,"word_alignment_verified":False,
            "human_review_verified":False,"publication_eligible":False}


def build(root,request,request_pin,captions,captions_pin,bundle,bundle_pin,boards,board_pin,output):
    root,bundle = private_root(root),private_root(bundle)
    output = bc.destination(output,root)
    bc.destination(output,bundle)
    expected,audio,plans = prepare(root,request,request_pin,captions,captions_pin,bundle,bundle_pin,boards,board_pin)
    pv.require(shutil.which("ffmpeg") and shutil.which("ffprobe"),"LOCAL_MEDIA_TOOLS_REQUIRED")
    output.mkdir(mode=0o700)
    marker = output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    runs = {}
    # Temporary plans/assets are private siblings of child runs and removed
    # after rendering. Each child preserves its own staged assets and review DB.
    with tempfile.TemporaryDirectory(dir=output) as temp:
        stage = Path(temp)
        for lang in LANGS:
            assets = stage/lang
            assets.mkdir()
            for scene in plans[lang].scenes:
                with (assets/scene.narration_file).open("xb") as f:
                    f.write(expected[scene.narration_file])
            plan_path = stage/(lang+".json")
            plan_path.write_bytes(json_bytes(plans[lang].model_dump()))
            report = pp.build(plan_path,assets,output/lang)
            checked = audit_run(output/lang,lang,expected,audio,plans[lang],report["manifest_sha256"])
            pv.require(checked["queue_state"] == "PENDING" and checked["queue_revision"] == 0,
                       "NEW_QUEUE_STATE")
            runs[lang] = {k:checked[k] for k in ("manifest_sha256","video_sha256","duration_ms")}
    obj = receipt(request_pin,captions_pin,bundle_pin,board_pin,audio,plans,runs)
    raw = json_bytes(obj)
    with (output/"pair.json").open("xb") as f:
        f.write(raw)
    pv.require(pv.read(output/"pair.json",MAX_BOARDS) == raw,"PAIR_WRITE")
    pv.require({p.name for p in output.iterdir()} == set(LANGS)|{"pair.json","INCOMPLETE"},
               "PAIR_INVENTORY")
    marker.unlink()
    return {"pair_sha256":sha(raw),"runs":runs,"duration_ms":audio["duration_ms"],
            "human_review_required":True,"publication_eligible":False}


def verify(root,request,request_pin,captions,captions_pin,bundle,bundle_pin,boards,board_pin,output,pair_pin):
    output = private_root(output)
    pv.require({p.name for p in output.iterdir()} == set(LANGS)|{"pair.json"},"PAIR_INVENTORY")
    raw = pinned(pv.read(output/"pair.json",MAX_BOARDS),pair_pin,MAX_BOARDS)
    obj = pv.decode(raw)
    pv.require(type(obj) is dict and type(obj.get("runs")) is dict and set(obj["runs"]) == set(LANGS),
               "PAIR_FIELDS")
    expected,audio,plans = prepare(root,request,request_pin,captions,captions_pin,bundle,bundle_pin,boards,board_pin)
    runs, states = {}, {}
    for lang in LANGS:
        record = obj["runs"][lang]
        pv.require(type(record) is dict and set(record) == {"manifest_sha256","video_sha256","duration_ms"},
                   "RUN_FIELDS")
        checked = audit_run(output/lang,lang,expected,audio,plans[lang],record["manifest_sha256"])
        runs[lang] = {k:checked[k] for k in ("manifest_sha256","video_sha256","duration_ms")}
        states[lang] = {"revision":checked["queue_revision"],"state":checked["queue_state"]}
    pv.require(raw == json_bytes(receipt(request_pin,captions_pin,bundle_pin,board_pin,audio,plans,runs)),
               "PAIR_RECEIPT")
    return {"integrity_passed":True,"fresh_media_audit":True,"pair_sha256":pair_pin,
            "review_states":states,"human_review_verified":False,"publication_eligible":False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode",required=True)
    for mode in ("build","verify"):
        a = sub.add_parser(mode)
        a.add_argument("--root",type=Path,required=True)
        for name in ("request","captions","bundle","boards"):
            a.add_argument("--"+name,type=Path,required=True)
            a.add_argument("--"+name+"-sha256",required=True)
        a.add_argument("--output",type=Path,required=True)
        if mode == "verify":
            a.add_argument("--pair-sha256",required=True)
    args = p.parse_args()
    try:
        values = (args.root,private_file(args.request,bc.MAX_REQUEST),args.request_sha256,
                  private_file(args.captions,bc.MAX_CAPTIONS),args.captions_sha256,
                  args.bundle,args.bundle_sha256,private_file(args.boards,MAX_BOARDS),args.boards_sha256,args.output)
        result = build(*values) if args.mode == "build" else verify(*values,args.pair_sha256)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,EOFError,wave.Error,
            sqlite3.Error,RecursionError) as exc:
        print(json.dumps({"completed":False,"error_type":type(exc).__name__,"publication_eligible":False}))
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
