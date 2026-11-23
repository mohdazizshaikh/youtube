#!/usr/bin/env python3
"""Read-only-with-respect-to-owner-data backup/restore *synthetic* acceptance drill.

Creates a brand new temporary SQLite database with current migrations and a
synthetic output. Backs them up, validates the ZIP, restores to a clean folder,
and checks both SQLite/data and output integrity. Nothing is read from the
owner's real data/, OAuth keyring, or any remote source.

  python tools/offline_acceptance_drill.py --json-out C:/Private/viralos-drill.json

The result is proof of an *isolated fixture drill*, NOT a successful recovery
of an existing owner dataset or a real Windows installation acceptance.
"""
from __future__ import annotations
import argparse, json, os, sqlite3, sys, tempfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app import db
from tools.offline_backup_restore import make_backup,verify_backup,restore_backup,digest_file

ROOT=Path(__file__).resolve().parent.parent


def run_drill(base:Path) -> dict:
    base=Path(base).resolve()
    base.mkdir(parents=True,exist_ok=True)
    fresh_db=base/'fixture'/'source.sqlite'
    fixture_outputs=base/'fixture'/'outputs'
    fixture_outputs.mkdir(parents=True,exist_ok=True)
    art=fixture_outputs/'synthetic-smoke.txt'
    art.write_text('SYNTHETIC OFFLINE ONLY; NOT PRIVATE USER DATA\n',encoding='utf8')
    old=os.environ.get('VIRALOS_DB')
    try:
        os.environ['VIRALOS_DB']=str(fresh_db)
        db.initialize()
        with db.read() as c:
            expected=c.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0]
            assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally:
        if old is None:os.environ.pop('VIRALOS_DB',None)
        else:os.environ['VIRALOS_DB']=old
    archive=base/'fixture.viralbackup.zip'
    backed=make_backup(archive,fresh_db,fixture_outputs)
    verified=verify_backup(archive)
    restored=restore_backup(archive,base/'restored')
    target_db=base/'restored'/'data'/'viral.db'
    c=sqlite3.connect(str(target_db))
    try:
        actual=c.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0]
        integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
    finally:c.close()
    content_ok=(digest_file(art)==digest_file(base/'restored'/'outputs'/'synthetic-smoke.txt'))
    if expected!=actual or integrity!='ok' or not content_ok:
        raise RuntimeError('Synthetic restore did not preserve data or artifact bytes')
    return {'gate':'M4_ISOLATED_SYNTHETIC_BACKUP_RESTORE',
            'status':'SYNTHETIC_RESTORE_INTEGRITY_PASSED',
            'schema_migrations_count':actual,'artifact_sha256_match':content_ok,
            'sqlite_integrity_check':integrity,
            'verified_backup_entries':verified['file_count'],
            'real_owner_data_accessed':False,'oauth_tokens_accessed':False,
            'remote_git_contacted':False,'external_network_requests':False,
            'real_windows_hardware_accepted':False,'owner_dataset_restore_accepted':False}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--json-out',type=Path,help='Existing files are never overwritten; keep owner reports outside Git')
    args=ap.parse_args(argv)
    if args.json_out:
        out=args.json_out.resolve()
        if out.is_relative_to(ROOT) or out.exists():
            ap.error('Choose a NEW private report path outside the source repository')
    with tempfile.TemporaryDirectory(prefix='viralos-fixture-drill-') as temp:
        info=run_drill(Path(temp))
    if args.json_out:
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(info,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
