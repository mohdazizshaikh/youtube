"""Private, durable editorial progress ledger. Never authorizes a release.
Only digests, checklist counts and state are persisted, not paths or reviewer text.
"""
from __future__ import annotations
import os
import re
import sqlite3
from contextlib import contextmanager, closing
from pathlib import Path
from .domain_draft_review import review_packet, evaluate, _canonical

APP_ID = 0x564F5351
SCHEMA = '''
CREATE TABLE drafts (
 manifest_sha256 TEXT PRIMARY KEY, packet_sha256 TEXT NOT NULL,
 video_sha256 TEXT NOT NULL, domain TEXT NOT NULL, format TEXT NOT NULL,
 synthetic_demo INTEGER NOT NULL CHECK(synthetic_demo IN (0,1)),
 scene_count INTEGER NOT NULL CHECK(scene_count BETWEEN 2 AND 8),
 revision INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'PENDING'
);
CREATE TABLE submissions (
 manifest_sha256 TEXT NOT NULL REFERENCES drafts(manifest_sha256),
 revision INTEGER NOT NULL CHECK(revision > 0), review_sha256 TEXT NOT NULL,
 state TEXT NOT NULL, blocker_count INTEGER NOT NULL CHECK(blocker_count >= 0),
 PRIMARY KEY(manifest_sha256,revision), UNIQUE(manifest_sha256,review_sha256)
);
'''


def _pin(pin):
    if not isinstance(pin, str) or not re.fullmatch(r'[0-9a-f]{64}', pin):
        raise ValueError('exact lowercase SHA-256 pin required')
    return pin


def initialize(path: Path):
    path = Path(path)
    # Exclusive creation; never repurpose an application database.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(path)) as db:
            db.executescript(f'PRAGMA application_id={APP_ID}; PRAGMA user_version=1;'+SCHEMA)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


@contextmanager
def _db(path, write=False):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('initialize a separate local queue database first')
    db = sqlite3.connect(path.resolve().as_uri()+'?mode=rw', uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        if db.execute('PRAGMA application_id').fetchone()[0]!=APP_ID or db.execute('PRAGMA user_version').fetchone()[0]!=1:
            raise ValueError('not a supported ViralOS review queue database')
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def register(path, draft, assets, manifest_pin):
    """Fresh media audit outside transaction; register immutable draft identity."""
    _pin(manifest_pin)
    p = review_packet(draft, assets, manifest_pin)
    packet_pin = _canonical(p)
    values = (manifest_pin, packet_pin, _pin(p['video_sha256']), p['domain'], p['format'], int(p['synthetic_demo']), len(p['scenes']))
    with _db(path, True) as db:
        old = db.execute('SELECT * FROM drafts WHERE manifest_sha256=?',(manifest_pin,)).fetchone()
        if old:
            if tuple(old[k] for k in ('manifest_sha256','packet_sha256','video_sha256','domain','format','synthetic_demo','scene_count')) != values:
                raise ValueError('registered draft identity changed')
            return dict(old)
        db.execute('INSERT INTO drafts(manifest_sha256,packet_sha256,video_sha256,domain,format,synthetic_demo,scene_count) VALUES(?,?,?,?,?,?,?)',values)
        return dict(db.execute('SELECT * FROM drafts WHERE manifest_sha256=?',(manifest_pin,)).fetchone())


def submit(path, draft, assets, manifest_pin, expected_revision, review):
    """Evaluate exact reviewed media again; atomically append a new revision."""
    _pin(manifest_pin)
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError('nonnegative integer expected revision required')
    # The original evaluator re-audits files and rejects stale scene/packet pins.
    result = evaluate(draft, assets, manifest_pin, review)
    blockers = result['blockers']
    if result['synthetic_demo']:
        state = 'DEMO_BLOCKED'
    elif result['self_attested_editorial_checklist_complete']:
        state = 'SELF_ATTESTED'
    elif any(b['reason']=='REVISE' for b in blockers):
        state = 'NEEDS_REVISION'
    else:
        state = 'INCOMPLETE'
    with _db(path, True) as db:
        row=db.execute('SELECT * FROM drafts WHERE manifest_sha256=?',(manifest_pin,)).fetchone()
        if row is None:
            raise ValueError('draft not registered')
        if row['revision'] != expected_revision:
            raise ValueError('stale queue revision; reload status')
        if row['packet_sha256'] != review['packet_sha256'] or row['video_sha256'] != result['video_sha256'] or row['synthetic_demo'] != int(result['synthetic_demo']):
            raise ValueError('registered packet/media mismatch')
        review_pin=_pin(result['review_sha256'])
        if db.execute('SELECT 1 FROM submissions WHERE manifest_sha256=? AND review_sha256=?',(manifest_pin,review_pin)).fetchone():
            raise ValueError('review already recorded')
        revision=expected_revision+1
        db.execute('INSERT INTO submissions VALUES(?,?,?,?,?)',(manifest_pin,revision,review_pin,state,len(blockers)))
        db.execute('UPDATE drafts SET revision=?,state=? WHERE manifest_sha256=?',(revision,state,manifest_pin))
    return {'manifest_sha256':manifest_pin,'revision':revision,'state':state,'blocker_count':len(blockers),'publication_eligible':False}


def status(path):
    """Consistent read snapshot; never exports raw reviewer data or local paths."""
    with _db(path) as db:
        drafts=[dict(r) for r in db.execute('SELECT * FROM drafts ORDER BY domain,format,manifest_sha256')]
        history=[dict(r) for r in db.execute('SELECT * FROM submissions ORDER BY manifest_sha256,revision')]
    counts={s:0 for s in ('PENDING','INCOMPLETE','NEEDS_REVISION','DEMO_BLOCKED','SELF_ATTESTED')}
    for d in drafts: counts[d['state']]+=1
    return {'schema':'VIRALOS_DOMAIN_REVIEW_QUEUE_V1','draft_count':len(drafts),'counts':counts,'drafts':drafts,'history':history,'publication_eligible':False,'reviewer_identity_verified':False,'claims_independently_verified':False,'rights_legally_certified':False}
