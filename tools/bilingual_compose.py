"""Compose hash-pinned bilingual scene PCM and scene captions, offline.

No TTS, translation, word alignment, video generation or publication authority.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import unicodedata
import wave
from pathlib import Path

from tools.narration_prepare import FRAME, MAX_REQUEST, pinned, private_root, sha, timing
from tools.narration_qc import RATE, MAX_WAV, private_file, script_stats
from tools.pilot_run_verify import decode, plain, require, read, file_hash

SCHEMA = "VIRALOS_BILINGUAL_AUDIO_BUNDLE_V1"
CAPTION_SCHEMA = "VIRALOS_BILINGUAL_SCENE_CAPTIONS_V1"
LANGUAGES = ("hindi", "english")
MAX_CAPTIONS = 64000


def caption_text(value, locale):
    require(type(value) is str and 3 <= len(value) <= 500 and value == value.strip(),
            "CAPTION_LENGTH")
    require("-->" not in value and not any(
        unicodedata.category(c)[0] == "C" and c not in "\u200c\u200d"
        or unicodedata.category(c) in {"Zl", "Zp"} for c in value), "CAPTION_CONTROL")
    stats = script_stats(value.encode("utf8"), locale)
    require(not stats["script_flags"], "CAPTION_SCRIPT_REVIEW")
    return value


def load_captions(raw, expected, schedule_pin, request):
    pinned(raw, expected, MAX_CAPTIONS)
    data = decode(raw)
    require(type(data) is dict and set(data) == {"schema", "timing_request_sha256", "scenes"}
            and data["schema"] == CAPTION_SCHEMA
            and data["timing_request_sha256"] == schedule_pin, "CAPTION_SCHEMA")
    require(type(data["scenes"]) is list and len(data["scenes"]) == len(request["scenes"]),
            "CAPTION_COUNT")
    for index, (row, scene) in enumerate(zip(data["scenes"], request["scenes"]), 1):
        require(type(row) is dict and set(row) == {"scene", "hindi", "english"}
                and type(row["scene"]) is int and row["scene"] == index, "CAPTION_SCENE")
        for lang in LANGUAGES:
            caption_text(row[lang], scene[lang]["locale"])
        require(row["hindi"] != row["english"], "CAPTION_REUSE")
    return data["scenes"]


def timestamp(ms):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02}.{milli:03}"


def wav_bytes(pcm):
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        w.writeframes(pcm)
    return out.getvalue()


def source_pcm(root, track, samples):
    raw = private_file(root / track["file"], MAX_WAV)
    pinned(raw, track["sha256"], MAX_WAV)
    with wave.open(io.BytesIO(raw), "rb") as w:
        require((w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype())
                == (1, 2, RATE, "NONE"), "PCM_FORMAT")
        require(w.getnframes() == samples, "PCM_CHANGED")
        pcm = w.readframes(samples)
    require(len(pcm) == 2*samples, "PCM_TRUNCATED")
    return pcm


def prepare(root, request, request_pin, captions, captions_pin):
    root = private_root(root)
    schedule = timing(root, request, request_pin)
    require(not schedule["review_flags"], "TIMING_REVIEW_REQUIRED")
    data = decode(request)
    require(len({row["english"]["locale"] for row in data["scenes"]}) == 1,
            "ENGLISH_LOCALE_CHANGED")
    caption_rows = load_captions(captions, captions_pin, request_pin, data)
    outputs, scenes = {}, []
    masters = {lang: bytearray() for lang in LANGUAGES}
    cues = {lang: ["WEBVTT", ""] for lang in LANGUAGES}
    for row, planned, caption in zip(data["scenes"], schedule["scenes"], caption_rows):
        n = planned["video_frames"]*FRAME
        scene = {"scene": planned["scene"], "start_ms": planned["start_ms"],
                 "end_ms": planned["end_ms"], "video_frames": planned["video_frames"]}
        for lang in LANGUAGES:
            pad = planned[lang+"_pad_samples"]
            pcm = source_pcm(root, row[lang], n-pad)
            padded = pcm + b"\0"*(2*pad)
            require(len(padded) == n*2, "SCENE_LENGTH")
            name = f"{lang}_{planned['scene']:02}.wav"
            outputs[name] = wav_bytes(padded)
            masters[lang].extend(padded)
            text = caption[lang]
            cues[lang].extend([f"{timestamp(planned['start_ms'])} --> {timestamp(planned['end_ms'])}",
                               html.escape(text, quote=False), ""])
            scene[lang] = {"source_audio_sha256": row[lang]["sha256"],
                           "source_pcm_sha256": sha(pcm), "source_samples": n-pad,
                           "padding_samples": pad, "padded_pcm_sha256": sha(padded),
                           "file": name, "caption_text_sha256": sha(text.encode("utf8"))}
        scenes.append(scene)
    total = schedule["total_video_frames"]*FRAME
    for lang in LANGUAGES:
        require(len(masters[lang]) == 2*total, "MASTER_LENGTH")
        outputs[lang+".wav"] = wav_bytes(bytes(masters[lang]))
        outputs[lang+".vtt"] = ("\n".join(cues[lang])+"\n").encode("utf8")
    manifest = {"schema": SCHEMA, "timing_request_sha256": request_pin,
                "captions_request_sha256": captions_pin, "format": schedule["format"],
                "fps": 25, "sample_rate_hz": RATE, "duration_ms": schedule["duration_ms"],
                "total_samples_per_track": total, "scenes": scenes,
                "english_locale": data["scenes"][0]["english"]["locale"],
                "files": {k: {"sha256": sha(v), "bytes": len(v)} for k,v in sorted(outputs.items())},
                "caption_timing": "SCENE_LEVEL_ONLY", "source_pcm_preserved": True,
                "word_alignment_verified": False, "speech_content_verified": False,
                "translation_verified": False, "human_review_required": True,
                "publication_eligible": False}
    outputs["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2,
                                           sort_keys=True)+"\n").encode("utf8")
    return outputs, manifest


def destination(output, root):
    output = Path(output).absolute()
    parent = private_root(output.parent)
    output = parent / output.name
    require(not output.is_relative_to(root) and not root.is_relative_to(output),
            "OVERLAPPING_OUTPUT")
    require(not output.exists() and not output.is_symlink(), "OUTPUT_EXISTS")
    return output


def compose(root, request, request_pin, captions, captions_pin, output):
    root = private_root(root)
    output = destination(output, root)
    outputs, manifest = prepare(root, request, request_pin, captions, captions_pin)
    output.mkdir(mode=0o700)
    marker = output/"INCOMPLETE"
    marker.touch(exist_ok=False)
    for name, raw in outputs.items():
        with (output/name).open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        require(file_hash(output/name) == sha(raw), "OUTPUT_WRITE_HASH")
    manifest_pin = sha(outputs["manifest.json"])
    require({p.name for p in output.iterdir()} == set(outputs)|{"INCOMPLETE"},
            "OUTPUT_INVENTORY")
    marker.unlink()
    return {"manifest_sha256": manifest_pin, "duration_ms": manifest["duration_ms"],
            "total_samples_per_track": manifest["total_samples_per_track"],
            "files": len(outputs), "human_review_required": True,
            "publication_eligible": False}


def verify(root, request, request_pin, captions, captions_pin, bundle, manifest_pin):
    bundle = private_root(bundle)
    expected, manifest = prepare(root, request, request_pin, captions, captions_pin)
    pinned(expected["manifest.json"], manifest_pin, MAX_REQUEST)
    require({p.name for p in bundle.iterdir()} == set(expected), "BUNDLE_INVENTORY")
    for name, raw in expected.items():
        require(read(bundle/name, len(raw)) == raw, "BUNDLE_BYTES")
    return {"integrity_passed": True, "fresh_recomposition": True,
            "manifest_sha256": manifest_pin, "duration_ms": manifest["duration_ms"],
            "human_review_required": True, "publication_eligible": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    for mode in ("compose","verify"):
        a = sub.add_parser(mode)
        a.add_argument("--root", type=Path, required=True)
        a.add_argument("--request", type=Path, required=True)
        a.add_argument("--request-sha256", required=True)
        a.add_argument("--captions", type=Path, required=True)
        a.add_argument("--captions-sha256", required=True)
        if mode == "compose":
            a.add_argument("--output", type=Path, required=True)
        else:
            a.add_argument("--bundle", type=Path, required=True)
            a.add_argument("--manifest-sha256", required=True)
    args = p.parse_args()
    try:
        values = (args.root, private_file(args.request, MAX_REQUEST), args.request_sha256,
                  private_file(args.captions, MAX_CAPTIONS), args.captions_sha256)
        result = (compose(*values,args.output) if args.mode == "compose"
                  else verify(*values,args.bundle,args.manifest_sha256))
    except (OSError, ValueError, TypeError, KeyError, EOFError, wave.Error,
            OverflowError, RecursionError) as exc:
        print(json.dumps({"completed": False,"error_type":type(exc).__name__,
                          "publication_eligible":False}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
