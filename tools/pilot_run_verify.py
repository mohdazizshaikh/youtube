"""Read-only Phase 14 pilot resume preflight. No upload or review approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r"[0-9a-f]{64}")
WAV = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.wav", re.I)
MAX_JSON = 2_000_000
MAX_MEDIA = 512 * 1024 * 1024
APP_ID = 0x564F5351


def require(condition, code):
    if not condition:
        raise ValueError(code)


def plain(path, directory=False):
    st = path.lstat()
    require(not getattr(st, "st_file_attributes", 0) & 0x400, "REPARSE_POINT")
    require(not stat.S_ISLNK(st.st_mode), "SYMLINK")
    require(stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode),
            "WRONG_FILE_TYPE")
    return st


def read(path, limit):
    st = plain(path)
    require(0 < st.st_size <= limit, "FILE_SIZE")
    with path.open("rb") as f:
        raw = f.read(limit + 1)
    require(len(raw) == st.st_size, "FILE_CHANGED")
    return raw


def file_hash(path, limit=MAX_MEDIA):
    st = plain(path)
    require(0 < st.st_size <= limit, "FILE_SIZE")
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            size += len(chunk)
            require(size <= limit, "FILE_SIZE")
            h.update(chunk)
    require(size == st.st_size, "FILE_CHANGED")
    return h.hexdigest()


def unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj


def invalid_constant(value):
    raise ValueError("NONFINITE_JSON")


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)


def document(path):
    return decode(read(path, MAX_JSON))


def canonical(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def pin(value):
    require(isinstance(value, str) and PIN.fullmatch(value) is not None, "INVALID_PIN")
    return value


def exact_int(value, low, high):
    return type(value) is int and low <= value <= high


def check_queue(path, expected, demo):
    st = plain(path)
    require(0 < st.st_size <= 64 * 1024 * 1024, "QUEUE_SIZE")
    # No live or uncheckpointed journal may be present. Never use immutable=1
    # on a database with possible pending journal changes.
    for suffix in ("-wal", "-shm", "-journal"):
        journal = path.with_name(path.name + suffix)
        require(not journal.exists() and not journal.is_symlink(), "QUEUE_ACTIVE")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        require(db.execute("PRAGMA application_id").fetchone()[0] == APP_ID, "QUEUE_ID")
        require(db.execute("PRAGMA user_version").fetchone()[0] == 1, "QUEUE_VERSION")
        require(db.execute("PRAGMA quick_check(1)").fetchone()[0] == "ok", "QUEUE_CORRUPT")
        require(db.execute("PRAGMA foreign_key_check").fetchone() is None, "QUEUE_FOREIGN_KEY")
        rows = db.execute("SELECT manifest_sha256, packet_sha256, video_sha256, domain, format,"
                          " synthetic_demo, scene_count, revision, state FROM drafts LIMIT 2").fetchall()
        require(len(rows) == 1 and rows[0][:7] == expected, "QUEUE_IDENTITY")
        revision, state = rows[0][7:]
        require(exact_int(revision, 0, 100000), "QUEUE_REVISION")
        require(state in {"PENDING", "DEMO_BLOCKED", "SELF_ATTESTED",
                          "NEEDS_REVISION", "INCOMPLETE"}, "QUEUE_STATE")
        require((revision == 0) == (state == "PENDING"), "QUEUE_STATE_REVISION")
        require(state == "PENDING" or (state == "DEMO_BLOCKED") == demo, "DEMO_STATE")
        history = db.execute("SELECT revision, state, review_sha256, blocker_count FROM submissions"
                             " WHERE manifest_sha256=? ORDER BY revision LIMIT 100001",
                             (expected[0],)).fetchall()
        require(len(history) == revision, "QUEUE_HISTORY_LENGTH")
        seen = set()
        for i, (rev, status, review, blockers) in enumerate(history, 1):
            require(rev == i and status in {"DEMO_BLOCKED", "SELF_ATTESTED",
                                          "NEEDS_REVISION", "INCOMPLETE"}, "QUEUE_HISTORY")
            require((status == "DEMO_BLOCKED") == demo, "DEMO_HISTORY")
            require(pin(review) not in seen and exact_int(blockers, 0, 10000), "QUEUE_HISTORY")
            seen.add(review)
        require(not history or history[-1][1] == state, "QUEUE_HISTORY_STATE")
    return revision, state


def verify(run, manifest_pin, fresh=False):
    """Check a stopped local run against a separately recorded trusted pin.

    Hash and SQLite checks are not a media decode or authenticated review.
    Use fresh=True to re-run the existing independent media/packet auditor.
    """
    pin(manifest_pin)
    run = Path(run).absolute()
    plain(run, True)
    run = run.resolve(strict=True)
    require(not run.is_relative_to(ROOT), "PRIVATE_RUN_REQUIRED")
    require(not (run / "INCOMPLETE").exists() and not (run / "INCOMPLETE").is_symlink(),
            "RUN_INCOMPLETE")
    draft, assets = run / "draft", run / "assets"
    plain(draft, True)
    plain(assets, True)
    receipt = document(run / "run.json")
    raw = read(draft / "manifest.json", MAX_JSON)
    require(hashlib.sha256(raw).hexdigest() == manifest_pin, "MANIFEST_PIN")
    manifest = decode(raw)
    packet = document(run / "review_packet.json")
    plan = document(draft / "plan.json")
    template = document(run / "review_template.json")
    catalog = document(run / "catalog.json")
    require(receipt["schema"] == "VIRALOS_PILOT_RUN_V1", "RUN_SCHEMA")
    require(manifest["schema"] == "VIRALOS_DOMAIN_NARRATED_DRAFT_V1", "MANIFEST_SCHEMA")
    require(packet["schema"] == "VIRALOS_DOMAIN_DRAFT_REVIEW_PACKET_V1", "PACKET_SCHEMA")
    require(template["schema_version"] == "VIRALOS_DOMAIN_DRAFT_REVIEW_V1", "TEMPLATE_SCHEMA")
    for obj in (receipt, packet):
        require(obj["manifest_sha256"] == manifest_pin, "RECEIPT_PIN")
        require(obj["technical_audit_passed"] is True, "TECHNICAL_FLAG")
        require(obj["human_review_verified"] is False, "REVIEW_FLAG")
    for obj in (receipt, manifest, packet):
        require(obj["publication_eligible"] is False, "PUBLICATION_FLAG")
        require(type(obj["synthetic_demo"]) is bool, "DEMO_TYPE")
        for key in ("domain", "format", "synthetic_demo"):
            require(obj[key] == manifest[key], "DRAFT_IDENTITY")
    require(receipt["live_account_tested"] is False, "ACCOUNT_FLAG")
    require(receipt["console_configuration_valid"] is True, "CONSOLE_FLAG")
    require(type(receipt["review_pending"]) is bool, "PENDING_FLAG")
    elapsed = receipt["elapsed_seconds"]
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0, "ELAPSED")
    require(manifest["stream_qc_passed"] is True, "STREAM_FLAG")
    for key in ("caption_word_alignment_verified", "speech_content_verified",
                "claim_truth_verified", "rights_cleared"):
        require(manifest[key] is False, "UNSUPPORTED_ACCEPTANCE_FLAG")
    n = receipt["scenes"]
    require(exact_int(n, 2, 8), "SCENE_COUNT")
    require(all(len(obj["scenes"]) == n for obj in (manifest, packet, plan, template)), "SCENE_COUNT")
    require(type(manifest["fps"]) is int and manifest["fps"] == 25, "FPS")
    require(exact_int(manifest["frames"], 1, 6000), "FRAME_COUNT")
    require(type(manifest["duration_ms"]) is int and manifest["duration_ms"] == manifest["frames"] * 40,
            "DURATION")
    require(type(receipt["duration_ms"]) is int and receipt["duration_ms"] == manifest["duration_ms"],
            "RECEIPT_DURATION")
    expected_files = {"draft.mp4", "plan.json", "captions.vtt", "narration.wav"}
    expected_files.update(f"scene_{i:02}.png" for i in range(1, n + 1))
    require(set(manifest["files_sha256"]) == expected_files, "MANIFEST_INVENTORY")
    require({p.name for p in draft.iterdir()} == expected_files | {"manifest.json"}, "DRAFT_INVENTORY")
    for name, expected_hash in manifest["files_sha256"].items():
        require(file_hash(draft / name) == pin(expected_hash), "DRAFT_HASH")
    video = manifest["files_sha256"]["draft.mp4"]
    require(receipt["video_sha256"] == packet["video_sha256"] == video, "VIDEO_PIN")
    expected_assets = set()
    end = 0
    for i, (s, p, a, t) in enumerate(zip(manifest["scenes"], packet["scenes"],
                                          plan["scenes"], template["scenes"]), 1):
        require(all(type(o["scene"]) is int and o["scene"] == i for o in (s, p, t)), "SCENE_ORDER")
        require(s["start_ms"] == end and exact_int(s["frames"], 1, 750), "SCENE_TIMING")
        end += s["frames"] * 40
        require(s["end_ms"] == end and p["start_ms"] == s["start_ms"] and p["end_ms"] == end,
                "SCENE_TIMING")
        name = f"scene_{i:02}.png"
        require(s["board_file"] == p["board_file"] == name, "BOARD_NAME")
        require(s["board_sha256"] == p["board_sha256"] == manifest["files_sha256"][name], "BOARD_PIN")
        require(a["rights_attested"] is True and s["rights_self_attested"] is True
                and p["rights_self_attested"] is True, "RIGHTS_DECLARATION")
        asset = a["narration_file"]
        require(isinstance(asset, str) and WAV.fullmatch(asset) is not None, "ASSET_NAME")
        require(asset.casefold() not in expected_assets, "ASSET_DUPLICATE")
        expected_assets.add(asset.casefold())
        require(file_hash(assets / asset, 1_100_000) == pin(a["narration_sha256"])
                == p["narration_sha256"] == s["narration_input_sha256"], "ASSET_HASH")
        require(p["narration_text"] == a["narration_text"], "NARRATION_TEXT")
        require(hashlib.sha256(a["narration_text"].encode()).hexdigest() == s["caption_text_sha256"],
                "CAPTION_PIN")
        require(canonical({k: v for k, v in p.items() if k != "scene_sha256"})
                == pin(p["scene_sha256"]) == t["scene_sha256"], "SCENE_PIN")
    require(end == manifest["duration_ms"], "SCENE_DURATION")
    require({p.name.casefold() for p in assets.iterdir()} == expected_assets
            and len(list(assets.iterdir())) == n, "ASSET_INVENTORY")
    packet_pin = canonical(packet)
    require(template["manifest_sha256"] == manifest_pin and template["packet_sha256"] == packet_pin,
            "TEMPLATE_PIN")
    require(template["reviewer"] == "", "TEMPLATE_REVIEWER")
    checks = {"source_accuracy", "narration_accuracy", "visual_accuracy",
              "asset_rights", "originality", "caption_accuracy"}
    require(len(packet["checks"]) == len(checks) and set(packet["checks"]) == checks, "PACKET_CHECKS")
    for scene in template["scenes"]:
        require(scene["checks"] == dict.fromkeys(checks, "NOT_REVIEWED")
                and scene["notes"] == "", "TEMPLATE_CHECKS")
    require(catalog == [{"manifest_sha256": manifest_pin, "draft": str(draft),
                         "assets": str(assets)}], "CATALOG_RELOCATION_OR_TAMPER")
    expected = (manifest_pin, packet_pin, video, manifest["domain"], manifest["format"],
                int(manifest["synthetic_demo"]), n)
    revision, state = check_queue(run / "reviews.sqlite", expected, manifest["synthetic_demo"])
    if fresh:
        from app.domain_draft_review import review_packet
        require(review_packet(draft, assets, manifest_pin) == packet, "FRESH_PACKET_MISMATCH")
    return {"schema": "VIRALOS_PILOT_RESUME_PREFLIGHT_V1", "manifest_sha256": manifest_pin,
            "integrity_passed": True, "fresh_media_audit": fresh, "queue_revision": revision,
            "queue_state": state, "synthetic_demo": manifest["synthetic_demo"],
            "human_review_verified": False, "publication_eligible": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--metadata-only", action="store_true",
                        help="Skip fresh media decode; not sufficient for resume acceptance")
    args = parser.parse_args()
    try:
        result = verify(args.run, args.manifest_sha256, fresh=not args.metadata_only)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, RuntimeError) as exc:
        # Avoid leaking private absolute paths, SQL, reviewer text or asset names.
        print(json.dumps({"integrity_passed": False, "error_type": type(exc).__name__,
                          "publication_eligible": False}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
