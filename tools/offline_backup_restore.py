#!/usr/bin/env python3
"""Local-only ViralOS SQLite WAL backup / verified restore.

Never uploads or reads OAuth keyring. Backups may contain unpublished videos and
private facts: keep outside Git and protect with OS filesystem encryption.

  python tools/offline_backup_restore.py backup --archive C:/Private/snapshot.viralbackup.zip
  python tools/offline_backup_restore.py verify --archive C:/Private/snapshot.viralbackup.zip
  python tools/offline_backup_restore.py restore --archive C:/Private/snapshot.viralbackup.zip \
      --target-root C:/RestoredViralOS --acknowledge-private-data

Restore refuses any occupied output/database destination. For real disaster
recovery, install the matching code/schema and restore on a clean target.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import db

MAX_ITEMS = 20_000
MAX_UNCOMPRESSED = 30 * 1024**3


def digest_file(file: Path) -> str:
    h = hashlib.sha256()
    with file.open('rb') as f:
        for chunk in iter(lambda:f.read(2**20),b''):
            h.update(chunk)
    return h.hexdigest()


def _check_db(path: Path):
    c=sqlite3.connect(str(path))
    try:
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity_check failed')
        versions=[r[0] for r in c.execute('SELECT version FROM schema_migrations ORDER BY version')]
        if not versions or versions[0]!='001':
            raise ValueError('ViralOS migration history missing')
        return versions
    finally:
        c.close()


def make_backup(archive:Path, source_db:Path, outputs:Path) -> dict:
    archive=archive.resolve()
    source_db=source_db.resolve()
    outputs=outputs.resolve()
    if archive.exists():
        raise ValueError('Backup file already exists; refusing overwrite')
    if not source_db.is_file():
        raise ValueError('Local ViralOS SQLite database does not exist')
    if archive.is_relative_to(outputs):
        raise ValueError('Do not place the backup inside the outputs directory')
    archive.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='viral-backup-') as temp:
        snapshot=Path(temp)/'snapshot.sqlite'
        live=sqlite3.connect(f'file:{source_db.as_posix()}?mode=ro',uri=True)
        stable=sqlite3.connect(str(snapshot))
        try:
            live.backup(stable,pages=128)
        finally:
            stable.close();live.close()
        versions=_check_db(snapshot)
        files={'data/viral.db':snapshot}
        if outputs.exists():
            for f in sorted(outputs.rglob('*')):
                if f.is_symlink():
                    raise ValueError('Output symlink not backed up; remove or resolve it manually')
                if f.is_file():
                    rel=f.relative_to(outputs).as_posix()
                    files[f'outputs/{rel}']=f
        if len(files)>MAX_ITEMS or sum(x.stat().st_size for x in files.values())>MAX_UNCOMPRESSED:
            raise ValueError('Local backup size/count budget exceeded')
        listing={path:{'sha256':digest_file(file),'bytes':file.stat().st_size} for path,file in files.items()}
        manifest={'schema':'VIRALOS_LOCAL_BACKUP_V1','created_at_utc':datetime.now(timezone.utc).isoformat(),
                  'migrations':versions,'entries':listing,'oauth_secrets_included':False,
                  'contains_local_private_data':True,'source_remote_fetched':False}
        try:
            with ZipFile(archive,'x',compression=ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
                for path,file in files.items():
                    z.write(file,path)
                z.writestr('manifest.json',json.dumps(manifest,sort_keys=True))
        except Exception:
            archive.unlink(missing_ok=True)
            raise
    verify_backup(archive)
    return {'archive':str(archive),'file_count':len(files),'migrations':versions}


def _safe_name(name:str)->bool:
    p=PurePosixPath(name)
    return bool(name) and '\\' not in name and not p.is_absolute() and '..' not in p.parts and name==str(p)


def verify_backup(archive:Path) -> dict:
    with ZipFile(archive,'r') as z:
        names=z.namelist()
        if len(names)<2 or len(names)>MAX_ITEMS+1 or len(names)!=len(set(names)) or 'manifest.json' not in names:
            raise ValueError('Invalid or duplicate backup manifest entries')
        if any(not _safe_name(x) for x in names):
            raise ValueError('Unsafe relative file path in backup archive')
        manifest=json.loads(z.read('manifest.json'))
        if manifest.get('schema')!='VIRALOS_LOCAL_BACKUP_V1':
            raise ValueError('Unknown backup schema')
        files=manifest.get('entries')
        if not isinstance(files,dict) or set(names)-{'manifest.json'} != set(files):
            raise ValueError('Backup manifest does not match archive files')
        if 'data/viral.db' not in files or any(not p.startswith(('outputs/','data/viral.db')) for p in files):
            raise ValueError('Backup must contain the correct DB and outputs only')
        total=sum(z.getinfo(n).file_size for n in names if n!='manifest.json')
        if total>MAX_UNCOMPRESSED:
            raise ValueError('Backup decompressed size budget exceeded')
        with tempfile.TemporaryDirectory(prefix='viral-backup-check-') as temp:
            snapshot=Path(temp)/'snapshot.sqlite'
            for name,details in files.items():
                digest=hashlib.sha256();size=0
                with z.open(name,'r') as f:
                    destination=snapshot.open('wb') if name=='data/viral.db' else None
                    try:
                        for chunk in iter(lambda:f.read(2**20),b''):
                            digest.update(chunk);size+=len(chunk)
                            if destination:destination.write(chunk)
                    finally:
                        if destination:destination.close()
                if size!=details['bytes'] or digest.hexdigest()!=details['sha256']:
                    raise ValueError('Backup data checksum mismatch: '+name)
            versions=_check_db(snapshot)
            if versions!=manifest.get('migrations'):
                raise ValueError('Restored DB migration versions changed')
    return {'verified':True,'file_count':len(files),'migrations':versions}


def restore_backup(archive:Path,target_root:Path) -> dict:
    info=verify_backup(archive)
    root=target_root.resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError('Target directory must be empty; will not replace existing data or outputs')
    # Validate archive contents again before first writing; no zip-slip extract().
    with ZipFile(archive,'r') as z:
        names=[n for n in z.namelist() if n!='manifest.json']
        root.mkdir(parents=True,exist_ok=True)
        for name in names:
            if not _safe_name(name):
                raise ValueError('Unsafe backup archive entry')
            dest=(root / name).resolve()
            if not dest.is_relative_to(root):
                raise ValueError('Archive path would escape target directory')
            dest.parent.mkdir(parents=True,exist_ok=True)
            with z.open(name,'r') as f, dest.open('xb') as out:
                shutil.copyfileobj(f,out,length=2**20)
    _check_db(root/'data'/'viral.db')
    return {**info,'restored_to':str(root),'owner_review_required':True}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='cmd',required=True)
    b=sub.add_parser('backup');b.add_argument('--archive',required=True,type=Path)
    v=sub.add_parser('verify');v.add_argument('--archive',required=True,type=Path)
    r=sub.add_parser('restore');r.add_argument('--archive',required=True,type=Path)
    r.add_argument('--target-root',required=True,type=Path)
    r.add_argument('--acknowledge-private-data',action='store_true')
    args=p.parse_args(argv)
    if args.cmd=='backup':
        result=make_backup(args.archive,db.path(),db.ROOT/'outputs')
    elif args.cmd=='verify':
        result=verify_backup(args.archive)
    else:
        if not args.acknowledge_private_data:
            p.error('Restoring private data requires --acknowledge-private-data')
        result=restore_backup(args.archive,args.target_root)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
