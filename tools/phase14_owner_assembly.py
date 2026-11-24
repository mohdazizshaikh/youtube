"""Owner-reviewed English narration reassembly; never grants release or infers word timings."""
import argparse, io, json, math, subprocess, time, wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
try:
    from . import phase14_localize as loc, phase14_bilingual as b, phase14_quality as q
except ImportError:
    import phase14_localize as loc, phase14_bilingual as b, phase14_quality as q


def validate(plan, folder, expected):
    folder=Path(folder); raw=loc.read(folder/'receipt.json',100000); r=json.loads(raw)
    if folder.is_symlink() or (folder/'INCOMPLETE').exists() or loc.digest(raw)!=b.pin(expected) or r.get('schema')!='VIRALOS_OWNER_RETIME_V1' or r.get('locale')!='en-US' or r.get('basis')!='owner_declared_manual_boundaries' or r.get('plan_sha256')!=loc.PIN or r.get('publication_authorized') is not False or r.get('acoustic_alignment_verified') is not False:raise ValueError('retime identity')
    b.pin(r['owner_manifest_sha256']);b.pin(r['boundaries_sha256'])
    p=loc.read(plan,100000)
    if loc.digest(p)!=loc.PIN:raise ValueError('pinned plan required')
    p=json.loads(p); rows=r.get('shots'); assets=folder/'assets'
    if not isinstance(rows,list) or len(rows)!=24 or assets.is_symlink() or not assets.is_dir():raise ValueError('24 private shots required')
    cursor=0; total=[]; texts=[]
    for i,row in enumerate(rows):
        chapter=p['scenes'][i//3];tokens=chapter['narration'].split(); name=f'{i:02}'
        if row['chapter']!=f'{i//3+1:02}' or row['beat']!=i%3:raise ValueError('shot order')
        a,z,u,v,n=(row[k] for k in ('source_start_sample','source_end_sample','word_start','word_end','samples'))
        if any(type(x) is not int for x in (a,z,u,v,n)) or not 0<=a<z or z-a!=n or not 0<=u<v<=len(tokens):raise ValueError('boundary mismatch')
        if i%3==0:
            if a or u:raise ValueError('chapter must start at zero')
        else:
            prev=rows[i-1]
            if a!=prev['source_end_sample'] or u!=prev['word_end'] or row['source_wav_sha256']!=prev['source_wav_sha256']:raise ValueError('boundary discontinuity')
        if i%3==2 and v!=len(tokens):raise ValueError('incomplete script')
        b.pin(row['source_wav_sha256']); text=loc.read(assets/(name+'.txt'),12000); wav=loc.read(assets/(name+'.wav'),9000000)
        if text!=' '.join(tokens[u:v]).encode('utf8') or loc.digest(text)!=row['script_sha256'] or loc.digest(wav)!=row['wav_sha256']:raise ValueError('shot hash or text mismatch')
        pcm,actual=loc.pcm(wav); frames=(actual+1599)//1600
        if n!=actual or row['start_frame']!=cursor or row['end_frame']!=cursor+frames or row['padding_samples']!=frames*1600-n:raise ValueError('frame timeline mismatch')
        total.append(pcm+b'\0'*(row['padding_samples']*2));texts.append(text.decode('utf8'));cursor+=frames
    if type(r['frames']) is not int or r['frames']!=cursor or not 720<=cursor<=27000:raise ValueError('duration mismatch')
    audio=loc.read(folder/'narration.wav',90000000)
    if loc.digest(audio)!=r['narration_sha256']:raise ValueError('assembled hash mismatch')
    with wave.open(io.BytesIO(audio),'rb') as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes(),w.getcomptype())!=(1,2,48000,cursor*1600,'NONE') or w.readframes(w.getnframes())!=b''.join(total):raise ValueError('assembled PCM mismatch')
    return p,r,audio,texts


def board(scene,beat,fontpath,fixture=False):
    img=Image.new('RGB',(1920,1080),'#101d2d');d=ImageDraw.Draw(img)
    def t(x,y,text,size=42,color='#f5f8fc'):
        f=ImageFont.truetype(str(fontpath),size)
        if d.textlength(text,font=f)>1700:raise ValueError('board text too wide')
        d.text((x,y),text,font=f,fill=color)
    t(100,70,'SHA-256 / CHAPTER '+scene['id'],30,'#9cbbd0');t(100,130,scene['title'],65)
    layout=scene['layout']; beats=scene['beats']
    if layout=='bits':
        import hashlib
        a=int.from_bytes(hashlib.sha256(b'hello').digest(),'big');z=int.from_bytes(hashlib.sha256(b'Hello').digest(),'big')
        for j in range(256):
            x=110+j%32*52;y=300+j//32*65
            d.rounded_rectangle((x,y,x+40,y+46),radius=4,fill='#e6aa55' if (a^z)>>(255-j)&1 and beat>=1 else '#3a6077')
        t(110,850,beats[beat],48)
    elif layout=='flow':
        for j,s in enumerate(beats):
            y=270+j*210;d.rounded_rectangle((110,y,1810,y+145),radius=24,fill='#24475b' if j<=beat else '#192a3e',outline='#79c9bf' if j==beat else '#42596e',width=5)
            t(155,y+42,s,50 if len(s)<45 else 39)
    else:
        for j,s in enumerate(beats):
            y=290+j*185;d.rounded_rectangle((110,y,1810,y+130),radius=20,fill='#263b50' if j<=beat else '#192a3e',outline='#e6aa55' if j==beat else '#42596e',width=5)
            t(150,y+38,s,46 if len(s)<45 else 36)
    t(100,1005,'ARTIFICIAL PCM TEST / NO SPEECH / NO RELEASE' if fixture else 'UNVERIFIED OWNER NARRATION / CAPTIONS NOT ALIGNED / NO RELEASE',27,'#f5c36b')
    return img


def render(plan, folder, expected, output, fontpath, fixture=False):
    p,r,audio,_=validate(plan,folder,expected);out=Path(output).resolve();out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch();work=out/'work';work.mkdir();start=time.monotonic()
    (work/'narration.wav').write_bytes(audio)
    for i,s in enumerate(r['shots']):board(p['scenes'][i//3],i%3,fontpath,fixture).save(work/f'{i:02}.png')
    def encode(i):
        s=r['shots'][i];n=s['end_frame']-s['start_frame'];name=f'{i:02}'
        subprocess.run(['ffmpeg','-v','error','-xerror','-nostdin','-n','-loop','1','-framerate','30','-i',name+'.png','-vf','fade=t=in:n=4','-frames:v',str(n),'-an','-c:v','libx264','-threads','2','-filter_threads','1','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',name+'.mp4'],cwd=work,check=True,capture_output=True,timeout=180)
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(encode,range(24)))
    (work/'concat.txt').write_text(''.join(f"file '{i:02}.mp4'\n" for i in range(24)),encoding='ascii');video=out/'owner_review.mp4'
    loc.run('ffmpeg','-v','error','-xerror','-nostdin','-n','-f','concat','-safe','1','-i',str(work/'concat.txt'),'-i',str(work/'narration.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(video),timeout=300)
    report=b.audit(video,r['frames']);report.update(schema='VIRALOS_OWNER_ASSEMBLY_REVIEW_V1',locale='en-US',retime_sha256=expected,narration_sha256=r['narration_sha256'],caption_basis='omitted_no_verified_alignment',artificial_pcm_fixture=fixture,natural_voice_verified=False,acoustic_alignment_verified=False,human_review_required=True,shots=24,elapsed_seconds=round(time.monotonic()-start,2));b.dump(out/'receipt.json',report);(out/'INCOMPLETE').unlink();return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','folder','expected','output','fontpath'):p.add_argument('--'+n,required=True)
    p.add_argument('--fixture',action='store_true');print(json.dumps(render(**vars(p.parse_args())),indent=2))
