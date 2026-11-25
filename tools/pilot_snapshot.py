"""Offline stopped-pilot snapshot and non-destructive restore, never a release gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path

from tools.pilot_run_verify import (ROOT, MAX_JSON, MAX_MEDIA, plain, read, decode,
                                    pin, require, file_hash, verify)

SCHEMA = "VIRALOS_PILOT_SNAPSHOT_V1"
TOP = {"run.json", "review_packet.json", "review_template.json", "catalog.json",
       "reviews.sqlite"}
DRAFT = {"manifest.json", "plan.json", "draft.mp4", "captions.vtt", "narration.wav"}
ASSET = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.wav")
BOARD = re.compile(r"scene_0[1-8]\.png")
MAX_TOTAL = 1024 * 1024 * 1024


def local_dir(path):
    path = Path(path).absolute()
    plain(path, True)
    path = path.resolve(strict=True)
    require(not path.is_relative_to(ROOT), "PRIVATE_PATH_REQUIRED")
    return path


def new_dir(path, source):
    path = Path(path).absolute()
    parent = local_dir(path.parent)
    path = parent / path.name
    require(not path.is_relative_to(source) and not source.is_relative_to(path),
            "OVERLAPPING_PATH")
    require(not path.exists() and not path.is_symlink(), "DESTINATION_EXISTS")
    return path


def limit(name):
    if name == "reviews.sqlite":
        return 64 * 1024 * 1024
    if name.startswith("assets/"):
        return 1_100_000
    if name.endswith(".json"):
        return MAX_JSON
    return MAX_MEDIA


def validate_names(names):
    require(isinstance(names, (list, set)) and 14 <= len(names) <= 26, "INVENTORY_SIZE")
    require(all(isinstance(n, str) for n in names), "INVENTORY_TYPE")
    require(len(set(n.casefold() for n in names)) == len(names), "INVENTORY_DUPLICATE")
    top, draft, assets = set(), set(), set()
    for name in names:
        parts = name.split("/")
        if len(parts) == 1 and name in TOP:
            top.add(name)
        elif len(parts) == 2 and parts[0] == "draft" and (parts[1] in DRAFT or BOARD.fullmatch(parts[1])):
            draft.add(parts[1])
        elif len(parts) == 2 and parts[0] == "assets" and ASSET.fullmatch(parts[1]):
            # Windows reserved device stems cannot be copied safely.
            require(not re.fullmatch(r"(?i:con|prn|aux|nul|com[0-9]|lpt[0-9])",
                                     parts[1][:-4]), "RESERVED_ASSET")
            assets.add(parts[1])
        else:
            raise ValueError("UNSAFE_INVENTORY_NAME")
    n = len(assets)
    require(2 <= n <= 8 and top == TOP, "INVENTORY_REQUIRED")
    require(draft == DRAFT | {f"scene_{i:02}.png" for i in range(1, n+1)},
            "INVENTORY_REQUIRED")
    return sorted(names)


def inventory(root):
    require({p.name for p in root.iterdir()} == TOP | {"draft", "assets"},
            "ROOT_INVENTORY")
    names = list(TOP)
    for folder in ("draft", "assets"):
        plain(root / folder, True)
        names.extend(f"{folder}/{p.name}" for p in (root / folder).iterdir())
    names = validate_names(names)
    records = {}
    total = 0
    for name in names:
        p = root / name
        size = plain(p).st_size
        total += size
        require(total <= MAX_TOTAL, "TOTAL_SIZE")
        records[name] = {"bytes": size, "sha256": file_hash(p, limit(name))}
    return records


def validate_records(records):
    require(type(records) is dict, "RECORDS_TYPE")
    validate_names(list(records))
    total = 0
    for name, record in records.items():
        require(type(record) is dict and set(record) == {"bytes", "sha256"}, "RECORD_FIELDS")
        size = record["bytes"]
        require(type(size) is int and 0 < size <= limit(name), "RECORD_SIZE")
        pin(record["sha256"])
        total += size
        require(total <= MAX_TOTAL, "TOTAL_SIZE")
    return records


def write_json(path, data):
    with path.open("x", encoding="utf8") as f:
        json.dump(data, f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def copy_exact(source, destination, record, max_bytes):
    st = plain(source)
    require(st.st_size == record["bytes"], "SOURCE_SIZE_CHANGED")
    h, count = hashlib.sha256(), 0
    with source.open("rb") as src, destination.open("xb") as dst:
        while chunk := src.read(1024 * 1024):
            count += len(chunk)
            require(count <= record["bytes"] <= max_bytes, "COPY_LIMIT")
            h.update(chunk)
            dst.write(chunk)
        require(count == record["bytes"] and h.hexdigest() == record["sha256"],
                "COPY_HASH_MISMATCH")
        dst.flush()
        os.fsync(dst.fileno())
    require(file_hash(destination, max_bytes) == record["sha256"], "DESTINATION_HASH")


def copy_payload(source, destination, records):
    (destination / "draft").mkdir(mode=0o700)
    (destination / "assets").mkdir(mode=0o700)
    for name, record in records.items():
        copy_exact(source / name, destination / name, record, limit(name))


def inspect(snapshot, snapshot_pin, manifest_pin):
    snapshot = local_dir(snapshot)
    pin(snapshot_pin)
    pin(manifest_pin)
    require({p.name for p in snapshot.iterdir()} == {"snapshot.json", "payload"},
            "SNAPSHOT_INVENTORY")
    raw = read(snapshot / "snapshot.json", MAX_JSON)
    require(hashlib.sha256(raw).hexdigest() == snapshot_pin, "SNAPSHOT_PIN")
    meta = decode(raw)
    require(type(meta) is dict and set(meta) == {"schema", "manifest_sha256", "files",
            "publication_eligible", "queue_revision", "queue_state"}, "SNAPSHOT_FIELDS")
    require(meta["schema"] == SCHEMA and meta["manifest_sha256"] == manifest_pin,
            "SNAPSHOT_IDENTITY")
    require(meta["publication_eligible"] is False, "PUBLICATION_FLAG")
    require(type(meta["queue_revision"]) is int and 0 <= meta["queue_revision"] <= 100000,
            "QUEUE_REVISION")
    require(meta["queue_state"] in {"PENDING", "DEMO_BLOCKED", "SELF_ATTESTED",
                                    "NEEDS_REVISION", "INCOMPLETE"}, "QUEUE_STATE")
    records = validate_records(meta["files"])
    payload = snapshot / "payload"
    plain(payload, True)
    require(inventory(payload) == records, "SNAPSHOT_BYTES")
    require(records["draft/manifest.json"]["sha256"] == manifest_pin, "MANIFEST_PIN")
    return meta


def backup(run, output, manifest_pin):
    run = local_dir(run)
    output = new_dir(output, run)
    checked = verify(run, manifest_pin, fresh=True)
    records = inventory(run)
    require(records["draft/manifest.json"]["sha256"] == manifest_pin, "MANIFEST_PIN")
    output.mkdir(mode=0o700)
    marker = output / "INCOMPLETE"
    marker.touch(exist_ok=False)
    payload = output / "payload"
    payload.mkdir(mode=0o700)
    copy_payload(run, payload, records)
    require(inventory(run) == inventory(payload) == records, "SOURCE_CHANGED")
    second = verify(run, manifest_pin, fresh=True)
    require(second == checked and inventory(run) == records, "SOURCE_CHANGED")
    meta = {"schema": SCHEMA, "manifest_sha256": manifest_pin, "files": records,
            "queue_revision": checked["queue_revision"], "queue_state": checked["queue_state"],
            "publication_eligible": False}
    write_json(output / "snapshot.json", meta)
    snapshot_pin = file_hash(output / "snapshot.json", MAX_JSON)
    marker.unlink()
    try:
        inspect(output, snapshot_pin, manifest_pin)
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"snapshot_sha256": snapshot_pin, "manifest_sha256": manifest_pin,
            "files": len(records), "queue_revision": checked["queue_revision"],
            "publication_eligible": False}


def restore(snapshot, output, snapshot_pin, manifest_pin):
    snapshot = local_dir(snapshot)
    output = new_dir(output, snapshot)
    meta = inspect(snapshot, snapshot_pin, manifest_pin)
    output.mkdir(mode=0o700)
    marker = output / "INCOMPLETE"
    marker.touch(exist_ok=False)
    copy_payload(snapshot / "payload", output, meta["files"])
    # Confirm all copied bytes, including the old absolute catalog, before rewriting
    # only that catalog for the new location. The original snapshot is untouched.
    require(inspect(snapshot, snapshot_pin, manifest_pin) == meta, "SNAPSHOT_CHANGED")
    old_catalog = output / "catalog.json"
    require(file_hash(old_catalog, MAX_JSON) == meta["files"]["catalog.json"]["sha256"],
            "CATALOG_COPY")
    old_catalog.unlink()
    write_json(old_catalog, [{"manifest_sha256": manifest_pin, "draft": str(output / "draft"),
                              "assets": str(output / "assets")}])
    marker.unlink()
    try:
        checked = verify(output, manifest_pin, fresh=True)
        require(checked["queue_revision"] == meta["queue_revision"]
                and checked["queue_state"] == meta["queue_state"], "QUEUE_RESTORE_MISMATCH")
        restored = inventory(output)
        require(all(restored[k] == v for k, v in meta["files"].items() if k != "catalog.json"),
                "RESTORE_BYTES")
    except BaseException:
        marker.touch(exist_ok=True)
        raise
    return {"restored": True, "manifest_sha256": manifest_pin,
            "queue_revision": checked["queue_revision"], "queue_state": checked["queue_state"],
            "fresh_media_audit": True, "publication_eligible": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("backup", "verify", "restore"):
        p = sub.add_parser(mode)
        p.add_argument("--run" if mode == "backup" else "--snapshot", required=True, type=Path)
        p.add_argument("--manifest-sha256", required=True)
        if mode != "backup":
            p.add_argument("--snapshot-sha256", required=True)
        if mode != "verify":
            p.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "backup":
            result = backup(args.run, args.output, args.manifest_sha256)
        elif args.mode == "restore":
            result = restore(args.snapshot, args.output, args.snapshot_sha256, args.manifest_sha256)
        else:
            meta = inspect(args.snapshot, args.snapshot_sha256, args.manifest_sha256)
            result = {"snapshot_integrity_passed": True, "files": len(meta["files"]),
                      "fresh_media_audit": False, "publication_eligible": False}
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error) as exc:
        print(json.dumps({"success": False, "error_type": type(exc).__name__,
                          "publication_eligible": False}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
