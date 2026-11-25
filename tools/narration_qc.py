"""Offline bilingual narration technical diagnostics; not speech recognition or approval."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import stat
import struct
import unicodedata
import wave
from pathlib import Path

from tools.pilot_run_verify import ROOT, decode, pin, require, read

RATE = 16000
MAX_SECONDS = 120
MAX_WAV = RATE * MAX_SECONDS * 2 + 65536
MAX_SCRIPT = 32768
LOCALES = {"hi-IN", "en-IN", "en-US"}
SCHEMA = "VIRALOS_NARRATION_QC_V1"
PAIR_SCHEMA = "VIRALOS_BILINGUAL_QC_V1"


def private_file(path, limit):
    path = Path(path).absolute()
    raw = read(path, limit)
    require(not path.resolve().is_relative_to(ROOT), "PRIVATE_INPUT_REQUIRED")
    return raw


def dbfs(value):
    return round(20 * math.log10(max(value / 32768, 1e-8)), 2)


def script_stats(raw, locale):
    require(locale in LOCALES, "UNSUPPORTED_LOCALE")
    require(type(raw) is bytes and 0 < len(raw) <= MAX_SCRIPT, "SCRIPT_SIZE")
    text = raw.decode("utf-8", errors="strict")
    require(not text.startswith("\ufeff"), "SCRIPT_BOM")
    require(not any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} and c not in "\n\r\t\u200c\u200d"
                    for c in text), "SCRIPT_CONTROL")
    words = text.split()
    require(1 <= len(words) <= 1000, "WORD_COUNT")
    require(all(len(w) <= 120 for w in words), "WORD_LENGTH")
    letters = [c for c in text if c.isalpha()]
    require(bool(letters), "SCRIPT_NO_LETTERS")
    devanagari = sum("\u0900" <= c <= "\u097f" for c in letters)
    latin = sum("LATIN" in unicodedata.name(c, "") for c in letters)
    flags = []
    if locale == "hi-IN" and devanagari / len(letters) < 0.5:
        flags.append("HINDI_SCRIPT_REVIEW")
    if locale != "hi-IN" and latin / len(letters) < 0.8:
        flags.append("ENGLISH_SCRIPT_REVIEW")
    return {"script_sha256": hashlib.sha256(raw).hexdigest(), "words": len(words),
            "letters": len(letters), "devanagari_letter_fraction": round(devanagari / len(letters), 4),
            "latin_letter_fraction": round(latin / len(letters), 4), "script_flags": flags}


def analyze_pcm(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_WAV, "WAV_SIZE")
    with wave.open(io.BytesIO(raw), "rb") as wf:
        require((wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getcomptype())
                == (1, 2, RATE, "NONE"), "PCM_FORMAT")
        frames = wf.getnframes()
        require(RATE // 2 <= frames <= RATE * MAX_SECONDS, "PCM_DURATION")
        pcm = wf.readframes(frames)
    require(len(pcm) == frames * 2, "PCM_TRUNCATED")
    peak = squares = signed = clipped = near_zero = 0
    window = RATE // 50  # 20 ms
    silent = []
    for offset in range(0, frames, window):
        count = min(window, frames - offset)
        samples = struct.unpack_from(f"<{count}h", pcm, 2 * offset)
        energy = sum(x*x for x in samples)
        squares += energy
        signed += sum(samples)
        peak = max(peak, max(abs(x) for x in samples))
        clipped += sum(abs(x) >= 32760 for x in samples)
        near_zero += sum(abs(x) < 130 for x in samples)
        silent.append((math.sqrt(energy / count) < 200, count))
    lead = tail = longest = current = 0
    for quiet, count in silent:
        if not quiet:
            break
        lead += count
    for quiet, count in reversed(silent):
        if not quiet:
            break
        tail += count
    for quiet, count in silent:
        current = current + count if quiet else 0
        longest = max(longest, current)
    quiet_frames = sum(n for q, n in silent if q)
    rms = math.sqrt(squares / frames)
    flags = []
    if rms < 200: flags.append("LOW_RMS")
    if clipped / frames > 0.001: flags.append("CLIPPING")
    if quiet_frames / frames > 0.6: flags.append("MOSTLY_QUIET")
    if lead >= RATE: flags.append("LONG_LEADING_QUIET")
    if tail >= RATE: flags.append("LONG_TRAILING_QUIET")
    if longest >= 2 * RATE: flags.append("LONG_QUIET_INTERVAL")
    if abs(signed / frames) >= 328: flags.append("DC_OFFSET")
    if peak > 0 and rms > 0 and peak / rms < 1.1: flags.append("LOW_CREST_FACTOR")
    return {"audio_sha256": hashlib.sha256(raw).hexdigest(), "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            "sample_rate_hz": RATE, "frames": frames, "duration_ms": round(frames*1000/RATE),
            "peak_dbfs": dbfs(peak), "rms_dbfs": dbfs(rms),
            "clipped_fraction": round(clipped/frames, 6), "near_zero_fraction": round(near_zero/frames, 6),
            "quiet_window_fraction": round(quiet_frames/frames, 6),
            "leading_quiet_ms": round(lead*1000/RATE), "trailing_quiet_ms": round(tail*1000/RATE),
            "longest_quiet_ms": round(longest*1000/RATE),
            "dc_offset_fraction": round(signed/frames/32768, 6),
            "crest_factor": round(peak/rms, 3) if rms else None, "audio_flags": flags}


def diagnose(audio, script, locale, audio_pin, script_pin):
    pin(audio_pin)
    pin(script_pin)
    a = analyze_pcm(audio)
    t = script_stats(script, locale)
    require(a["audio_sha256"] == audio_pin and t["script_sha256"] == script_pin, "INPUT_PIN")
    wpm = t["words"] * 60 * RATE / a["frames"]
    flags = a["audio_flags"] + t["script_flags"]
    if wpm < 70 or wpm > 220:
        flags.append("DECLARED_TEXT_PACE_REVIEW")
    return {"schema": SCHEMA, "locale": locale, "audio": a, "script": t,
            "declared_words_per_minute": round(wpm, 2), "review_flags": flags,
            "technical_diagnostics_clean": not flags, "human_listening_required": True,
            "spoken_words_verified": False, "voice_license_verified": False,
            "publication_eligible": False}


def load_track(root, track, expected_locale):
    require(type(track) is dict and set(track) == {"locale", "audio", "script",
            "audio_sha256", "script_sha256"}, "TRACK_FIELDS")
    require(track["locale"] == expected_locale, "TRACK_LOCALE")
    for field, extension in (("audio", ".wav"), ("script", ".txt")):
        name = track[field]
        require(type(name) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}" + re.escape(extension), name),
                "TRACK_LEAF_NAME")
        require(not re.fullmatch(r"(?i:con|prn|aux|nul|com[0-9]|lpt[0-9])", name.rsplit(".", 1)[0]),
                "TRACK_RESERVED_NAME")
    return diagnose(private_file(root / track["audio"], MAX_WAV),
                    private_file(root / track["script"], MAX_SCRIPT),
                    expected_locale, track["audio_sha256"], track["script_sha256"])


def pair(root, request, request_pin):
    root = Path(root).absolute()
    st = root.lstat()
    require(stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode)
            and not getattr(st, "st_file_attributes", 0) & 0x400, "TRACK_ROOT")
    root = root.resolve(strict=True)
    require(not root.is_relative_to(ROOT), "PRIVATE_INPUT_REQUIRED")
    pin(request_pin)
    require(hashlib.sha256(request).hexdigest() == request_pin, "REQUEST_PIN")
    data = decode(request)
    require(type(data) is dict and set(data) == {"schema", "hindi", "english"}
            and data["schema"] == "VIRALOS_BILINGUAL_QC_REQUEST_V1", "PAIR_FIELDS")
    require(type(data["hindi"]) is dict and type(data["english"]) is dict, "TRACK_FIELDS")
    en_locale = data["english"].get("locale")
    require(en_locale in ("en-IN", "en-US"), "TRACK_LOCALE")
    hi = load_track(root, data["hindi"], "hi-IN")
    en = load_track(root, data["english"], en_locale)
    require(hi["audio"]["pcm_sha256"] != en["audio"]["pcm_sha256"], "REUSED_PCM")
    require(hi["script"]["script_sha256"] != en["script"]["script_sha256"], "REUSED_SCRIPT")
    ratio = hi["audio"]["frames"] / en["audio"]["frames"]
    flags = ["DURATION_RATIO_REVIEW"] if not 0.65 <= ratio <= 1.5 else []
    return {"schema": PAIR_SCHEMA, "request_sha256": request_pin, "hindi": hi, "english": en,
            "hindi_to_english_duration_ratio": round(ratio, 4), "pair_flags": flags,
            "technical_diagnostics_clean": not flags and hi["technical_diagnostics_clean"]
            and en["technical_diagnostics_clean"], "translation_verified": False,
            "alignment_verified": False, "human_listening_required": True,
            "publication_eligible": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    one = sub.add_parser("single")
    one.add_argument("--audio", type=Path, required=True)
    one.add_argument("--script", type=Path, required=True)
    one.add_argument("--locale", choices=sorted(LOCALES), required=True)
    one.add_argument("--audio-sha256", required=True)
    one.add_argument("--script-sha256", required=True)
    two = sub.add_parser("pair")
    two.add_argument("--root", type=Path, required=True)
    two.add_argument("--request", type=Path, required=True)
    two.add_argument("--request-sha256", required=True)
    args = p.parse_args()
    try:
        if args.mode == "single":
            result = diagnose(private_file(args.audio, MAX_WAV), private_file(args.script, MAX_SCRIPT),
                              args.locale, args.audio_sha256, args.script_sha256)
        else:
            result = pair(args.root, private_file(args.request, MAX_SCRIPT), args.request_sha256)
    except (ValueError, OSError, EOFError, wave.Error, TypeError, KeyError, OverflowError, struct.error) as exc:
        print(json.dumps({"diagnostics_completed": False, "error_type": type(exc).__name__,
                          "publication_eligible": False}))
        return 1
    print(json.dumps(result, indent=2))
    # A diagnostic with warnings completed successfully; it is not a release pass.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
