"""Make a synthetic chapter-one fixture from the Phase 14C plan, never release media."""
import argparse
import json
import subprocess
from pathlib import Path
try:
    from .phase14_motion import sha
except ImportError:
    from phase14_motion import sha


def make(plan, root, espeak='espeak'):
    root=Path(root);plan=Path(plan);s=json.loads(plan.read_text(encoding='utf-8'))['scenes'][0]['narration']
    a=s.index('Today we');b=s.index('Then we');texts=[s[:a].strip(),s[a:b].strip(),s[b:].strip()]
    root.mkdir(exist_ok=False);(root/'INCOMPLETE').touch();assets=root/'assets';assets.mkdir();script=root/'script.txt';script.write_text(s+'\n',encoding='utf-8');shots=[];cursor=0
    for i,(text,visual) in enumerate(zip(texts,['file','compare','fingerprint'])):
        temp=root/f'raw{i}.wav';wav=assets/f'shot{i}.wav'
        subprocess.run([espeak,'-v','en-us','-s','155','-w',str(temp),text],check=True,timeout=60)
        subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(temp),'-ac','1','-ar','48000','-c:a','pcm_s16le',str(wav)],check=True,timeout=60)
        temp.unlink();end=cursor+len(text.split());shots.append(dict(visual=visual,word_start=cursor,word_end=end,text=text,wav=wav.name,wav_sha256=sha(wav)));cursor=end
    (root/'manifest.json').write_text(json.dumps(dict(schema=1,locale='en-US',basis='synthetic_fixture',script_sha256=sha(script),shots=shots),indent=2)+'\n',encoding='utf-8');(root/'INCOMPLETE').unlink()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--espeak',default='espeak');a=p.parse_args();make(a.plan,a.output,a.espeak)
