"""Build all 24 synthetic narrated CPU drafts with installed eSpeak and FFmpeg.
No external network/models, real factual claims, owner audio or publishing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from app.domain_adapters import POLICIES
from app.domain_draft_video import DraftPlan, compose
from tools.domain_storyboard import demo_spec


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args()
    espeak=shutil.which('espeak-ng') or shutil.which('espeak')
    ffmpeg=shutil.which('ffmpeg')
    if not espeak or not ffmpeg:raise RuntimeError('installed eSpeak and FFmpeg required')
    a.output_dir.mkdir(parents=True,exist_ok=False)
    records=[]
    for domain in sorted(POLICIES):
        for fmt in ('SHORT','LONG'):
            folder=a.output_dir/f'{domain}_{fmt.lower()}'
            folder.mkdir();assets=folder/'assets';assets.mkdir()
            scenes=[]
            for i,text in enumerate((f'{domain.title()} example. This is a synthetic draft.', 'Check original sources before making factual claims.'),1):
                raw=assets/f'raw{i}.wav';voice=assets/f'voice{i}.wav'
                subprocess.run([espeak,'-v','en-us','-s','165','-w',str(raw),text],check=True,timeout=30)
                subprocess.run([ffmpeg,'-nostdin','-v','error','-n','-i',str(raw),'-ac','1','-ar','16000','-c:a','pcm_s16le',str(voice)],check=True,timeout=30)
                raw.unlink()
                board=demo_spec(domain,fmt).model_copy(deep=True)
                board.title=f'{domain.title()}: '+('Illustrative example' if i==1 else 'Review evidence')
                scenes.append({'board':board.model_dump(),'narration_file':voice.name,'narration_sha256':hashlib.sha256(voice.read_bytes()).hexdigest(),'narration_text':text,'rights_attested':True})
            result=compose(DraftPlan.model_validate({'scenes':scenes}),assets,folder/'draft')
            records.append({'folder':folder.name,'duration_ms':result['duration_ms'],'manifest_sha256':hashlib.sha256((folder/'draft'/'manifest.json').read_bytes()).hexdigest(),'video_sha256':result['files_sha256']['draft.mp4']})
            print(folder.name,flush=True)
    (a.output_dir/'index.json').write_text(json.dumps({'synthetic_demo':True,'voice':'installed eSpeak synthetic English','publication_eligible':False,'records':records},indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
