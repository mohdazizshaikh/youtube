"""Prepare 24 local domain review packets, with pinned batch index and no release authority."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from app.domain_adapters import POLICIES
from app.domain_draft_review import review_packet, template


def prepare(root: Path, index_pin: str, output: Path) -> dict:
    root,output=Path(root),Path(output)
    if root.is_symlink() or not root.is_dir():raise ValueError('local non-symlink root required')
    if output.resolve().is_relative_to(root.resolve()):raise ValueError('output must be separate from inputs')
    p=root/'index.json'
    if p.is_symlink() or not p.is_file() or p.stat().st_size>128000:raise ValueError('unsafe index')
    raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=index_pin:raise ValueError('batch index pin mismatch')
    index=json.loads(raw)
    records=index.get('records')
    expected={f'{d}_{f}' for d in POLICIES for f in ('short','long')}
    if not isinstance(records,list) or len(records)!=24 or any(not isinstance(x,dict) or not isinstance(x.get('folder'),str) for x in records) or {x.get('folder') for x in records}!=expected:
        raise ValueError('exact 24 domain/format entries required')
    output.mkdir(parents=False,exist_ok=False)
    try:
        result=[]
        for r in records:
            name=r['folder'];folder=root/name
            if folder.is_symlink() or not folder.is_dir():raise ValueError('unsafe domain directory')
            packet=review_packet(folder/'draft',folder/'assets',r['manifest_sha256'])
            if f"{packet['domain']}_{packet['format'].lower()}"!=name or packet['video_sha256']!=r.get('video_sha256'):
                raise ValueError('batch identity or video pin mismatch')
            if packet['synthetic_demo'] is not index.get('synthetic_demo'):
                raise ValueError('demo classification mismatch')
            body={'packet':packet,'review_template':template(packet)}
            data=(json.dumps(body,ensure_ascii=False,indent=2)+'\n').encode('utf8')
            filename=name+'.json';(output/filename).write_bytes(data)
            result.append({'folder':name,'packet_file':filename,'packet_file_sha256':hashlib.sha256(data).hexdigest(),'scene_count':len(packet['scenes']),'synthetic_demo':packet['synthetic_demo']})
        summary={'schema':'VIRALOS_DOMAIN_REVIEW_BATCH_V1','batch_index_sha256':index_pin,'packets_created':len(result),'records':result,'human_reviews_completed':0,'publication_eligible':False}
        (output/'index.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
        return summary
    except BaseException:
        shutil.rmtree(output);raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--index-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=prepare(a.root,a.index_sha256,a.output);print(f"{r['packets_created']} packets; 0 human reviews completed; no publishing permission")

if __name__=='__main__':main()
