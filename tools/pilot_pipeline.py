"""One local pilot: pinned inputs, CPU render, fresh audit, private review queue."""
import argparse
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path
from app.domain_draft_video import DraftPlan, compose, digest, _read_pcm
from app.domain_draft_review import review_packet, template
from app.domain_review_queue import initialize, register, status
from app.domain_review_web import create_app, load_catalog

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, obj):
    with path.open('x', encoding='utf8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def private_output(path, inputs=()):
    path = Path(path).resolve()
    if path.is_relative_to(ROOT) or any(path.is_relative_to(Path(p).resolve()) for p in inputs):
        raise ValueError('choose a new output directory outside source and input assets')
    if path.exists() or not path.parent.is_dir():
        raise ValueError('new output directory with existing parent required')
    return path


def make_example(folder):
    """Factual-topic pilot with explicitly provisional eSpeak narration."""
    exe = shutil.which('espeak-ng') or shutil.which('espeak')
    ffmpeg = shutil.which('ffmpeg')
    if not exe or not ffmpeg:
        raise RuntimeError('installed eSpeak and FFmpeg required for synthetic pilot')
    folder = private_output(folder); folder.mkdir()
    assets = folder/'assets'; assets.mkdir()
    original, changed = b'ViralOS pilot: approved', b'ViralOS pilot: Approved'
    a,b = digest(original),digest(changed)
    sources = [
      {'source_id':'NIST','url':'https://www.nist.gov/publications/secure-hash-standard','publisher':'NIST','independence_group':'nist','record_type':'PRIMARY','observed_at_utc':'2026-11-24T00:00:00Z'},
      {'source_id':'PY','url':'https://docs.python.org/3/library/hashlib.html','publisher':'Python documentation','independence_group':'python','record_type':'PRIMARY','observed_at_utc':'2026-11-24T00:00:00Z'}]
    evidence = [{'source_id':'NIST','relation':'SUPPORTS','locator':'Secure Hash Standard abstract: message digests detect changes'}, {'source_id':'PY','relation':'SUPPORTS','locator':'hashlib: SHA256, hash.update and hexdigest examples'}]
    items = [
      ('Can you spot a one-byte edit?', 'SHA-256 computes a digest from input bytes.', 'Two files can look almost identical. How can you check whether a download changed? SHA two fifty six turns its bytes into a fingerprint.'),
      ('One capital letter, different hash', f'Local example: {a[:12]} vs {b[:12]} (prefixes only).', 'In our Python experiment, we changed one lowercase letter to uppercase. The two SHA two fifty six digests are different. These prefixes come from that calculation.'),
      ('Compare against a trusted original', 'Compare the full digest with a trusted expected value.', 'Compute the full digest of your download and compare it with a trusted expected digest. A mismatch means the bytes differ. A matching hash alone does not prove who made it.')]
    scenes=[]
    for i,(title,claim,text) in enumerate(items,1):
        raw=assets/f'raw{i}.wav'; wav=assets/f'voice{i}.wav'
        subprocess.run([exe,'-v','en-us','-s','150','-w',str(raw),text],check=True,timeout=60)
        subprocess.run([ffmpeg,'-nostdin','-v','error','-n','-i',str(raw),'-ac','1','-ar','16000','-c:a','pcm_s16le',str(wav)],check=True,timeout=60)
        raw.unlink()
        board={'domain':'technology','format':'SHORT','title':title,'claims':[{'text':claim,'links':evidence}], 'sources':sources,'synthetic_demo':True,'specialist_facts':{'product_version':f'Python {platform.python_version()} hashlib.sha256','reproduction_steps':'Hash the two UTF-8 inputs in experiment.json; compare full hex digests','tested_environment':'Local CPU Python experiment; eSpeak placeholder narration'}}
        scenes.append({'board':board,'narration_file':wav.name,'narration_sha256':digest(wav.read_bytes()),'narration_text':text,'rights_attested':True})
    plan=DraftPlan.model_validate({'scenes':scenes})
    write_json(folder/'plan.json',plan.model_dump())
    write_json(folder/'experiment.json',{'inputs_utf8':[original.decode(),changed.decode()],'sha256':[a,b],'equal':a==b,'python':platform.python_version(),'source_review':'Human review pending; sources support hashing method, experiment is local original evidence','voice':'provisional eSpeak synthetic; no professional voice or commercial rights certification','publication_eligible':False})
    return folder/'plan.json', assets


def build(plan_path, assets, output, *, board_renderer=None):
    plan_path, assets = Path(plan_path), Path(assets).resolve(strict=True)
    if plan_path.is_symlink() or not plan_path.is_file() or not assets.is_dir():
        raise ValueError('regular plan and assets directory required')
    with plan_path.open('rb') as f: raw=f.read(256001)
    if len(raw)>256000: raise ValueError('plan too large')
    plan=DraftPlan.model_validate_json(raw)
    output=private_output(output,(assets,))
    for scene in plan.scenes: _read_pcm(assets,scene)
    output.mkdir(); started=time.monotonic()
    marker=output/'INCOMPLETE'; marker.touch(exist_ok=False)
    staged=output/'assets'; staged.mkdir()
    for scene in plan.scenes:
        src=assets/scene.narration_file
        if src.is_symlink(): raise ValueError('symlink narration rejected')
        with src.open('rb') as f: data=f.read(1_100_000)
        if digest(data)!=scene.narration_sha256: raise ValueError('narration changed during staging')
        with (staged/src.name).open('xb') as f: f.write(data)
    draft=output/'draft'
    manifest=compose(plan,staged,draft) if board_renderer is None else compose(plan,staged,draft,board_renderer=board_renderer)
    pin=digest((draft/'manifest.json').read_bytes())
    packet=review_packet(draft,staged,pin)
    write_json(output/'review_packet.json',packet)
    write_json(output/'review_template.json',template(packet))
    db=output/'reviews.sqlite'; initialize(db); register(db,draft,staged,pin)
    catalog=output/'catalog.json'
    write_json(catalog,[{'manifest_sha256':pin,'draft':str(draft),'assets':str(staged)}])
    create_app(db,load_catalog(catalog))
    report={'schema':'VIRALOS_PILOT_RUN_V1','domain':packet['domain'],'format':packet['format'],'synthetic_demo':packet['synthetic_demo'],'manifest_sha256':pin,'video_sha256':packet['video_sha256'],'scenes':len(packet['scenes']),'duration_ms':manifest['duration_ms'],'elapsed_seconds':round(time.monotonic()-started,3),'technical_audit_passed':True,'review_pending':status(db)['counts']['PENDING']==1,'console_configuration_valid':True,'human_review_verified':False,'publication_eligible':False,'live_account_tested':False}
    write_json(output/'run.json',report); marker.unlink()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='mode',required=True)
    e=sub.add_parser('example'); e.add_argument('--output',type=Path,required=True)
    b=sub.add_parser('build'); b.add_argument('--plan',type=Path,required=True); b.add_argument('--assets',type=Path,required=True); b.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.mode=='example': make_example(a.output); print('Provisional example inputs created; run build next.')
    else: print(json.dumps(build(a.plan,a.assets,a.output),indent=2))

if __name__=='__main__':main()
