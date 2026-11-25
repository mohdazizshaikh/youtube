"""Owner-local pronunciation coverage, gain-only mastering, bilingual scene planning.

No TTS, ASR, translation, word alignment, or publish authority. All media remains local.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import struct
import unicodedata
import wave
from pathlib import Path

from tools.narration_qc import (RATE, MAX_WAV, MAX_SCRIPT, LOCALES, analyze_pcm,
                                private_file, script_stats)
from tools.pilot_run_verify import ROOT, decode, pin, plain, require

MAX_REQUEST = 128000
FRAME = RATE // 25


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(raw, expected, limit):
    pin(expected)
    require(type(raw) is bytes and 0 < len(raw) <= limit, "INPUT_SIZE")
    require(sha(raw) == expected, "INPUT_PIN")
    return raw


def finite_number(value, minimum, maximum):
    require(type(value) in (int, float) and math.isfinite(value)
            and minimum <= value <= maximum, "NUMERIC_RANGE")
    return value


def master(raw, audio_pin, target_rms=-20, peak_ceiling=-3):
    """Apply one constant gain to PCM; never trim, stretch, denoise or compress."""
    pinned(raw, audio_pin, MAX_WAV)
    target_rms = finite_number(target_rms, -26, -16)
    peak_ceiling = finite_number(peak_ceiling, -6, -1)
    before = analyze_pcm(raw)
    # Do not conceal existing technical problems by normalizing them.
    require(not before["audio_flags"], "SOURCE_AUDIO_REVIEW_REQUIRED")
    with wave.open(io.BytesIO(raw), "rb") as wf:
        n = wf.getnframes()
        pcm = wf.readframes(n)
    samples = struct.unpack(f"<{n}h", pcm)
    peak = max(map(abs, samples))
    rms = math.sqrt(sum(x*x for x in samples) / n)
    require(peak > 0 and rms > 0, "SILENT_INPUT")
    desired = 20 * math.log10(32768 * 10**(target_rms/20) / rms)
    ceiling = math.floor(32768 * 10**(peak_ceiling/20))
    peak_limit = 20 * math.log10(ceiling / peak)
    gain_db = min(6, max(-12, desired), peak_limit)
    require(gain_db >= -12, "EXCESSIVE_ATTENUATION_REQUIRED")
    gain = 10**(gain_db/20)
    mastered = tuple(round(x*gain) for x in samples)
    require(max(map(abs, mastered)) <= ceiling, "PEAK_LIMIT")
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setparams((1, 2, RATE, n, "NONE", "not compressed"))
        wf.writeframes(struct.pack(f"<{n}h", *mastered))
    result = out.getvalue()
    after = analyze_pcm(result)
    require(after["frames"] == before["frames"], "TIMING_CHANGED")
    require(not after["audio_flags"], "MASTERED_AUDIO_REVIEW_REQUIRED")
    return result, {"schema": "VIRALOS_GAIN_MASTER_V1", "source": before, "output": after,
                    "target_rms_dbfs": target_rms, "peak_ceiling_dbfs": peak_ceiling,
                    "applied_gain_db": round(gain_db, 4),
                    "target_reached_within_1db": abs(after["rms_dbfs"]-target_rms) <= 1,
                    "timing_preserved": True, "human_listening_required": True,
                    "professional_mastering_verified": False, "publication_eligible": False}


def tokens(text):
    """NFC + casefold, contiguous Unicode letters/marks/numbers, not phonemes."""
    text = unicodedata.normalize("NFC", text.casefold())
    result, current = [], []
    for c in text:
        if unicodedata.category(c)[0] in "LMN" or c in "\u200c\u200d":
            current.append(c)
        elif current:
            result.append("".join(current))
            current = []
    if current:
        result.append("".join(current))
    return tuple(result)


def glossary_text(value):
    require(type(value) is str and 1 <= len(value) <= 160 and value == value.strip(),
            "GLOSSARY_TEXT")
    require(not any(unicodedata.category(c)[0] == "C" and c not in "\u200c\u200d"
                    for c in value), "GLOSSARY_CONTROL")
    require(bool(tokens(value)) and len(tokens(value)) <= 8, "GLOSSARY_TOKENS")
    return value


def pronunciation(script, script_pin, glossary, glossary_pin, locale):
    require(locale in LOCALES, "LOCALE")
    pinned(script, script_pin, MAX_SCRIPT)
    pinned(glossary, glossary_pin, MAX_REQUEST)
    script_stats(script, locale)
    data = decode(glossary)
    require(type(data) is dict and set(data) == {"schema", "locale", "entries"}
            and data["schema"] == "VIRALOS_PRONUNCIATION_GLOSSARY_V1"
            and data["locale"] == locale, "GLOSSARY_SCHEMA")
    require(type(data["entries"]) is list and 1 <= len(data["entries"]) <= 200, "GLOSSARY_COUNT")
    source = tokens(script.decode("utf-8"))
    ids, phrases, results = set(), set(), []
    for entry in data["entries"]:
        require(type(entry) is dict and set(entry) == {"id", "term", "spoken_hint",
                "required", "owner_reviewed"}, "ENTRY_FIELDS")
        ident = entry["id"]
        require(type(ident) is str and re.fullmatch(r"[A-Z][A-Z0-9_-]{0,39}", ident)
                and ident not in ids, "ENTRY_ID")
        ids.add(ident)
        term = tokens(glossary_text(entry["term"]))
        glossary_text(entry["spoken_hint"])
        require(term not in phrases, "DUPLICATE_TERM")
        phrases.add(term)
        require(type(entry["required"]) is bool and type(entry["owner_reviewed"]) is bool,
                "ENTRY_BOOLEAN")
        matches = sum(source[i:i+len(term)] == term for i in range(len(source)-len(term)+1))
        flags = []
        if entry["required"] and not matches:
            flags.append("REQUIRED_TERM_NOT_FOUND")
        if matches and not entry["owner_reviewed"]:
            flags.append("HINT_OWNER_REVIEW_PENDING")
        results.append({"id": ident, "occurrences": matches, "required": entry["required"],
                        "owner_reviewed_declaration": entry["owner_reviewed"], "flags": flags})
    return {"schema": "VIRALOS_PRONUNCIATION_COVERAGE_V1", "locale": locale,
            "script_sha256": script_pin, "glossary_sha256": glossary_pin,
            "entries": results, "matched_entries": sum(r["occurrences"] > 0 for r in results),
            "coverage_review_flags": sum(len(r["flags"]) for r in results),
            "script_modified": False, "spoken_pronunciation_verified": False,
            "human_listening_required": True, "publication_eligible": False}


def private_root(root):
    root = Path(root).absolute()
    plain(root, True)
    root = root.resolve(strict=True)
    require(not root.is_relative_to(ROOT), "PRIVATE_ROOT")
    return root


def scene_audio(root, track, locale):
    require(type(track) is dict and set(track) == {"locale", "file", "sha256"}
            and track["locale"] == locale, "TRACK_SCHEMA")
    name = track["file"]
    require(type(name) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.wav", name),
            "TRACK_FILENAME")
    require(not re.fullmatch(r"(?i:con|prn|aux|nul|com[0-9]|lpt[0-9])", name[:-4]),
            "TRACK_RESERVED")
    raw = private_file(root / name, MAX_WAV)
    pinned(raw, track["sha256"], MAX_WAV)
    report = analyze_pcm(raw)
    require(report["frames"] <= RATE*30, "SCENE_DURATION")
    return report


def timing(root, request, request_pin):
    """Build a 25 fps shared scene duration proposal; output no edited media."""
    root = private_root(root)
    pinned(request, request_pin, MAX_REQUEST)
    data = decode(request)
    require(type(data) is dict and set(data) == {"schema", "format", "scenes"}
            and data["schema"] == "VIRALOS_BILINGUAL_SCENE_REQUEST_V1"
            and data["format"] in ("SHORT", "LONG"), "TIMING_SCHEMA")
    require(type(data["scenes"]) is list and 2 <= len(data["scenes"]) <= 8, "SCENE_COUNT")
    results, seen_names, seen_pcm, all_flags = [], set(), set(), []
    cursor = 0
    for index, scene in enumerate(data["scenes"], 1):
        require(type(scene) is dict and set(scene) == {"scene", "hindi", "english"}
                and type(scene["scene"]) is int and scene["scene"] == index, "SCENE_ORDER")
        require(type(scene["english"]) is dict and scene["english"].get("locale") in ("en-IN","en-US"),
                "ENGLISH_LOCALE")
        require(type(scene["hindi"]) is dict, "TRACK_SCHEMA")
        hi = scene_audio(root, scene["hindi"], "hi-IN")
        en = scene_audio(root, scene["english"], scene["english"]["locale"])
        require(hi["pcm_sha256"] != en["pcm_sha256"], "DUPLICATE_LANGUAGE_PCM")
        flags = []
        for language, track, report in (("HI", scene["hindi"], hi), ("EN", scene["english"], en)):
            key = track["file"].casefold()
            require(key not in seen_names, "REUSED_FILENAME")
            seen_names.add(key)
            if report["pcm_sha256"] in seen_pcm:
                flags.append(language+"_REUSED_PCM_REVIEW")
            seen_pcm.add(report["pcm_sha256"])
            flags.extend(language+"_"+f for f in report["audio_flags"])
        n = (max(hi["frames"], en["frames"]) + FRAME - 1)//FRAME
        hp, ep = n*FRAME-hi["frames"], n*FRAME-en["frames"]
        if max(hp, ep) > RATE*1.5:
            flags.append("EXCESSIVE_PADDING_REVIEW")
        if max(hi["frames"], en["frames"])/min(hi["frames"],en["frames"]) > 1.5:
            flags.append("DURATION_RATIO_REVIEW")
        results.append({"scene": index, "start_ms": cursor*40, "end_ms": (cursor+n)*40,
                        "video_frames": n, "hindi_audio_sha256": hi["audio_sha256"],
                        "english_audio_sha256": en["audio_sha256"], "hindi_pad_samples": hp,
                        "english_pad_samples": ep, "flags": flags})
        cursor += n
        all_flags.extend({"scene": index, "flag": f} for f in flags)
    limit = 60 if data["format"] == "SHORT" else 120
    require(cursor <= limit*25, "TOTAL_DURATION")
    return {"schema": "VIRALOS_BILINGUAL_SCENE_TIMING_V1", "request_sha256": request_pin,
            "format": data["format"], "fps": 25, "sample_rate": RATE,
            "total_video_frames": cursor, "duration_ms": cursor*40, "scenes": results,
            "review_flags": all_flags, "timing_proposal_only": True, "audio_modified": False,
            "word_alignment_verified": False, "translation_verified": False,
            "human_review_required": True, "publication_eligible": False}


def write_private(path, data):
    path = Path(path).absolute()
    parent = private_root(path.parent)
    path = parent / path.name
    require(path.suffix == ".wav", "OUTPUT_EXTENSION")
    with path.open("xb") as f:
        f.write(data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    a = sub.add_parser("master")
    a.add_argument("--audio", type=Path, required=True)
    a.add_argument("--audio-sha256", required=True)
    a.add_argument("--output", type=Path, required=True)
    a.add_argument("--target-rms", type=float, default=-20)
    a.add_argument("--peak-ceiling", type=float, default=-3)
    b = sub.add_parser("pronunciation")
    b.add_argument("--script", type=Path, required=True)
    b.add_argument("--script-sha256", required=True)
    b.add_argument("--glossary", type=Path, required=True)
    b.add_argument("--glossary-sha256", required=True)
    b.add_argument("--locale", choices=sorted(LOCALES), required=True)
    c = sub.add_parser("timing")
    c.add_argument("--root", type=Path, required=True)
    c.add_argument("--request", type=Path, required=True)
    c.add_argument("--request-sha256", required=True)
    args = p.parse_args()
    try:
        if args.mode == "master":
            raw, result = master(private_file(args.audio, MAX_WAV), args.audio_sha256,
                                 args.target_rms, args.peak_ceiling)
            write_private(args.output, raw)
        elif args.mode == "pronunciation":
            result = pronunciation(private_file(args.script, MAX_SCRIPT), args.script_sha256,
                                   private_file(args.glossary, MAX_REQUEST), args.glossary_sha256,
                                   args.locale)
        else:
            result = timing(args.root, private_file(args.request, MAX_REQUEST), args.request_sha256)
    except (OSError, ValueError, TypeError, KeyError, EOFError, wave.Error,
            OverflowError, struct.error, RecursionError) as exc:
        print(json.dumps({"completed": False, "error_type": type(exc).__name__,
                          "publication_eligible": False}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
