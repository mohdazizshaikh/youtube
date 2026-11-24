"""Offline CLI: python -m tools.domain_storyboard --input plan.json --output-dir newdir"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from app.domain_storyboards import Storyboard, render_board
from app.domain_adapters import POLICIES


def demo_spec(domain, fmt):
    return Storyboard(domain=domain,format=fmt,title=f'{domain.title()} production example',synthetic_demo=True,
        claims=[{'text':'Synthetic example only: review original records before making a claim.', 'links':[
            {'source_id':'S1','relation':'SUPPORTS','locator':'Synthetic primary record'},
            {'source_id':'S2','relation':'SUPPORTS','locator':'Synthetic secondary record'}]}],
        sources=[{'source_id':'S1','url':'https://primary.invalid/record','publisher':'Demo primary','independence_group':'demo-primary','record_type':'PRIMARY','observed_at_utc':'2026-11-24T00:00:00Z'},
                 {'source_id':'S2','url':'https://secondary.invalid/record','publisher':'Demo secondary','independence_group':'demo-secondary','record_type':'SECONDARY','observed_at_utc':'2026-11-24T00:00:00Z'}],
        specialist_facts={k:'Synthetic fixture, not real evidence' for k in POLICIES[domain].specialist_fields})


def build_one(spec, dest, animatic=False):
    dest.mkdir(parents=True,exist_ok=False)
    (dest/'input.json').write_text(spec.model_dump_json(indent=2)+'\n',encoding='utf8')
    result=render_board(spec,dest/'board.png')
    if animatic:
        exe=shutil.which('ffmpeg')
        if not exe:raise RuntimeError('local FFmpeg required for animatic')
        video=dest/'animatic.mp4'
        # Short silent technical motion preview, not a completed Short or long film.
        subprocess.run([exe,'-nostdin','-hide_banner','-loglevel','error','-n','-loop','1','-i',str(dest/'board.png'),
                        '-vf','fps=24,fade=t=in:st=0:d=0.25,fade=t=out:st=2.75:d=0.25',
                        '-t','3','-an','-c:v','libx264','-threads','2','-preset','veryfast','-pix_fmt','yuv420p',
                        '-movflags','+faststart',str(video)],check=True,timeout=45)
        result.update(animatic_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),animatic_duration_seconds=3,
                      audio_present=False,accepted_video=False)
    (dest/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    inputs=p.add_mutually_exclusive_group(required=True);inputs.add_argument('--input',type=Path);inputs.add_argument('--demo-all',action='store_true')
    p.add_argument('--output-dir',required=True,type=Path);p.add_argument('--animatics',action='store_true');a=p.parse_args()
    if a.demo_all:
        a.output_dir.mkdir(parents=True,exist_ok=False)
        results=[]
        for domain in sorted(POLICIES):
            for fmt in ('SHORT','LONG'):
                results.append(build_one(demo_spec(domain,fmt),a.output_dir/f'{domain}_{fmt.lower()}',a.animatics))
        (a.output_dir/'index.json').write_text(json.dumps({'synthetic':True,'publication_eligible':False,'records':results},indent=2)+'\n',encoding='utf8')
        print(f'{len(results)} synthetic review drafts generated')
    else:
        spec=Storyboard.model_validate_json(a.input.read_text(encoding='utf8'))
        print(json.dumps(build_one(spec,a.output_dir,a.animatics),indent=2))

if __name__=='__main__':main()
