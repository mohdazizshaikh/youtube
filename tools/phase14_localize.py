"""Hindi draft intake, exact PCM timeline and shaped typography. Never authorizes release."""
import argparse, hashlib, io, json, subprocess, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, features
RATE, FPS, SPF = 48000, 30, 1600
PIN = 'eb5a7ef2df3f371cad4b9c51d8275df5f6e3bf0ee59f8b28f6e8f5b7318c1e54'
def digest(data): return hashlib.sha256(data).hexdigest()
def read(path, cap):
    path=Path(path)
    if path.is_symlink() or not path.is_file(): raise ValueError('regular local file required')
    with path.open('rb') as f: data=f.read(cap+1)
    if not data or len(data)>cap: raise ValueError('file size outside bound')
    return data

def load_plan(path):
    raw=read(path,100000); p=json.loads(raw)
    if p.get('schema')!=1 or p.get('locale')!='hi-IN' or p.get('source_plan_sha256')!=PIN or p.get('basis')!='unreviewed_original_adaptation': raise ValueError('unexpected plan provenance')
    ch=p.get('chapters')
    if not isinstance(ch,list) or len(ch)!=8: raise ValueError('eight chapters required')
    def text(s,limit):
        if not isinstance(s,str) or not s.strip() or len(s)>limit or any(ord(c)<32 or c in '{}\\<>' for c in s): raise ValueError('invalid localized text')
    text(p['title'],120)
    for i,c in enumerate(ch,1):
        if c['id']!=f'{i:02}': raise ValueError('chapter order')
        text(c['title'],80)
        for k,lim in [('beats',90),('segments',1800)]:
            if not isinstance(c[k],list) or len(c[k])!=3: raise ValueError('three beats and segments required')
            for s in c[k]: text(s,lim)
    return p,digest(raw)

def pcm(data):
    with wave.open(io.BytesIO(data),'rb') as w:
        n=w.getnframes()
        if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getcomptype())!=(1,2,RATE,'NONE') or not RATE<=n<=90*RATE: raise ValueError('PCM16 mono 48kHz, 1–90s required')
        b=w.readframes(n)
    if len(b)!=n*2 or not any(b): raise ValueError('truncated or silent WAV')
    return b,n

def intake(plan,manifest,assets):
    p,pin=load_plan(plan); raw=read(manifest,100000); m=json.loads(raw)
    if m.get('schema')!=1 or m.get('locale')!='hi-IN' or m.get('plan_sha256')!=pin: raise ValueError('manifest identity mismatch')
    basis=m.get('basis')
    if basis not in ('synthetic_espeak','owner_reviewed_recording','owner_reviewed_local_tts'): raise ValueError('unsupported basis')
    if basis!='synthetic_espeak' and (m.get('rights_attested') is not True or m.get('listening_attested') is not True or not isinstance(m.get('rights_reference'),str) or not m['rights_reference'].strip()): raise ValueError('private owner declarations required')
    assets=Path(assets)
    if assets.is_symlink() or not assets.is_dir(): raise ValueError('private asset directory required')
    shots=m.get('shots'); texts=[s for c in p['chapters'] for s in c['segments']]
    if not isinstance(shots,list) or len(shots)!=24: raise ValueError('24 shots required')
    out=[]; cursor=0
    for i,(s,txt) in enumerate(zip(shots,texts)):
        name=f'{i:02}.wav'
        if s.get('file')!=name or s.get('script_sha256')!=digest(txt.encode('utf8')): raise ValueError('shot script/name mismatch')
        data=read(assets/name,9_000_000)
        if s.get('wav_sha256')!=digest(data): raise ValueError('audio hash mismatch')
        b,n=pcm(data); frames=(n+SPF-1)//SPF; pad=frames*SPF-n
        out.append((b,dict(chapter=f'{i//3+1:02}',beat=i%3,start_frame=cursor,end_frame=cursor+frames,samples=n,padding_samples=pad,wav_sha256=digest(data))))
        cursor+=frames
    if not 24*FPS<=cursor<=900*FPS: raise ValueError('localized duration outside 24s–15 minutes')
    return p,pin,basis,out,digest(raw)

def run(*args,timeout=180): return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def fixture(plan,output):
    p,pin=load_plan(plan); output=Path(output); output.mkdir(exist_ok=False); (output/'INCOMPLETE').touch(); assets=output/'assets'; assets.mkdir(); shots=[]
    for i,txt in enumerate(s for c in p['chapters'] for s in c['segments']):
        raw=output/'temp.wav'; dest=assets/f'{i:02}.wav'
        run('espeak','-v','hi','-s','145','-w',str(raw),txt)
        run('ffmpeg','-v','error','-nostdin','-n','-i',str(raw),'-ac','1','-ar','48000','-c:a','pcm_s16le',str(dest)); raw.unlink()
        shots.append(dict(file=dest.name,script_sha256=digest(txt.encode('utf8')),wav_sha256=digest(read(dest,9_000_000))))
    m=dict(schema=1,locale='hi-IN',basis='synthetic_espeak',plan_sha256=pin,shots=shots)
    (output/'manifest.json').write_text(json.dumps(m,indent=2)+'\n'); (output/'INCOMPLETE').unlink()

def font(path,size):
    if not features.check_feature('raqm'): raise RuntimeError('RAQM shaping required')
    return ImageFont.truetype(str(path),size,layout_engine=ImageFont.Layout.RAQM)
def line(draw,text,xy,f,fill,maxwidth):
    if draw.textlength(text,font=f)>maxwidth: raise ValueError('text overflow')
    draw.text(xy,text,font=f,fill=fill)
def board(c,i,fontpath,latinfont):
    im=Image.new('RGB',(1920,1080),'#101f32'); d=ImageDraw.Draw(im); f=lambda s:font(fontpath,s); lf=lambda s:font(latinfont,s)
    d.rectangle((75,120,1845,940),fill='#193449'); line(d,f'SHA-256  /  {c["id"]}',(100,35),lf(42),'#79dfcc',1700)
    line(d,c['title'],(125,170),f(72),'white',1650)
    for j,b in enumerate(c['beats']):
        y=365+j*150; d.rounded_rectangle((125,y,1795,y+112),18,fill='#285069' if i==j else '#203b50'); line(d,b,(165,y+20),f(56),'#ffdf87' if i==j else '#d7e6ef',1540)
    line(d,'UNREVIEWED HINDI DRAFT / NO RELEASE',(100,990),lf(33),'#ffdf87',1700)
    return im

def prepare(plan,manifest,assets,output,fontpath,latinfont):
    p,pin,basis,shots,mpin=intake(plan,manifest,assets); output=Path(output); output.mkdir(exist_ok=False); (output/'INCOMPLETE').touch()
    with wave.open(str(output/'narration.wav'),'wb') as w:
        w.setparams((1,2,RATE,0,'NONE','not compressed'))
        for b,r in shots: w.writeframes(b+b'\0'*(2*r['padding_samples']))
    for i in range(24): board(p['chapters'][i//3],i%3,fontpath,latinfont).save(output/f'{i:02}.png')
    board_hashes=[digest(read(output/f'{i:02}.png',8_000_000)) for i in range(24)]
    records=[r for _,r in shots]; n=records[-1]['end_frame']; receipt=dict(schema='VIRALOS_HINDI_INTAKE_V1',locale='hi-IN',basis=basis,plan_sha256=pin,manifest_sha256=mpin,narration_sha256=digest(read(output/'narration.wav',90_000_000)),frames=n,duration_seconds=n/FPS,board_sha256=board_hashes,shots=records,human_review_required=True,natural_voice_verified=False,acoustic_alignment_verified=False,publication_authorized=False)
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n'); (output/'INCOMPLETE').unlink();return receipt
def request(plan,output):
    """Write exact script files and an intentionally incomplete owner manifest."""
    p,pin=load_plan(plan); output=Path(output);output.mkdir(exist_ok=False);(output/'INCOMPLETE').touch();(output/'assets').mkdir();(output/'scripts').mkdir()
    shots=[]
    for i,txt in enumerate(s for c in p['chapters'] for s in c['segments']):
        (output/'scripts'/f'{i:02}.txt').write_bytes(txt.encode('utf8'))
        shots.append(dict(file=f'{i:02}.wav',script_sha256=digest(txt.encode('utf8')),wav_sha256=None))
    m=dict(schema=1,locale='hi-IN',basis='owner_reviewed_recording',plan_sha256=pin,rights_attested=False,listening_attested=False,rights_reference='',shots=shots)
    (output/'manifest.template.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
    (output/'INSTRUCTIONS.txt').write_text('Record or synthesize each exact script in assets/NN.wav, mono PCM16 at 48000 Hz, 1–90 seconds. Only use licensed owner-approved speech. Record actual local SHA-256 hashes in a new manifest.json and attest rights/listening only after review. Never commit recordings or private rights records. Template is deliberately invalid for rendering. Actual alignment and independent editorial review remain required.\n',encoding='utf8')
    (output/'INCOMPLETE').unlink();return dict(shots=24,ready_for_intake=False,publication_authorized=False)

def preview(prepared,output,chapter=1):
    """Render one chapter from prepared local assets; always private and unreviewed."""
    prepared,output=Path(prepared).resolve(),Path(output).resolve()
    if (prepared/'INCOMPLETE').exists() or not 1<=chapter<=8: raise ValueError('incomplete input or invalid chapter')
    raw=read(prepared/'receipt.json',100000); rec=json.loads(raw)
    if rec.get('schema')!='VIRALOS_HINDI_INTAKE_V1' or rec.get('publication_authorized') is not False or len(rec.get('shots',[]))!=24 or len(rec.get('board_sha256',[]))!=24: raise ValueError('invalid prepared receipt')
    cursor=0
    for i,r in enumerate(rec['shots']):
        n=r['samples']; f=(n+SPF-1)//SPF
        if type(n) is not int or not RATE<=n<=90*RATE or r['chapter']!=f'{i//3+1:02}' or r['beat']!=i%3 or r['start_frame']!=cursor or r['end_frame']!=cursor+f or r['padding_samples']!=f*SPF-n: raise ValueError('invalid prepared timing')
        cursor+=f
    wav=read(prepared/'narration.wav',90_000_000)
    if digest(wav)!=rec['narration_sha256'] or cursor!=rec['frames']: raise ValueError('prepared audio mismatch')
    with wave.open(io.BytesIO(wav),'rb') as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes(),w.getcomptype())!=(1,2,RATE,cursor*SPF,'NONE'): raise ValueError('prepared PCM format mismatch')
        begin=rec['shots'][(chapter-1)*3]['start_frame']; end=rec['shots'][chapter*3-1]['end_frame']; w.setpos(begin*SPF); audio=w.readframes((end-begin)*SPF)
    if len(audio)!=(end-begin)*SPF*2: raise ValueError('truncated chapter PCM')
    output.mkdir(exist_ok=False); (output/'INCOMPLETE').touch()
    with wave.open(str(output/'chapter.wav'),'wb') as w:
        w.setparams((1,2,RATE,0,'NONE','not compressed')); w.writeframes(audio)
    for i in range((chapter-1)*3,chapter*3):
        data=read(prepared/f'{i:02}.png',8_000_000)
        if digest(data)!=rec['board_sha256'][i]: raise ValueError('board hash mismatch')
        png=output/f'{i:02}.png'; png.write_bytes(data); r=rec['shots'][i]
        run('ffmpeg','-v','error','-nostdin','-loop','1','-framerate','30','-i',str(png),'-frames:v',str(r['end_frame']-r['start_frame']),'-an','-c:v','libx264','-threads','2','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',str(output/f'{i:02}.mp4'))
    concat=output/'concat.txt'; concat.write_text(''.join(f"file '{i:02}.mp4'\n" for i in range((chapter-1)*3,chapter*3)))
    dest=output/'hindi_chapter.mp4'; run('ffmpeg','-v','error','-nostdin','-f','concat','-safe','1','-i',str(concat),'-i',str(output/'chapter.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(dest))
    streams=json.loads(run('ffprobe','-v','error','-show_streams','-of','json',str(dest)).stdout)['streams']; v,a=streams
    if (v['codec_name'],v['width'],v['height'],v['avg_frame_rate'],int(v['nb_frames']),a['codec_name'],a['sample_rate'],a['channels'])!=('h264',1920,1080,'30/1',end-begin,'aac','48000',1) or any(abs(float(s['duration'])-(end-begin)/FPS)>.06 for s in streams): raise ValueError('stream audit failed')
    run('ffmpeg','-v','error','-xerror','-nostdin','-i',str(dest),'-f','null','-')
    result=dict(schema='VIRALOS_HINDI_CHAPTER_V1',chapter=chapter,basis=rec['basis'],prepared_receipt_sha256=digest(raw),video_sha256=digest(read(dest,128*1024*1024)),frames=end-begin,duration_seconds=(end-begin)/FPS,full_decode_pass=True,natural_voice_verified=False,acoustic_alignment_verified=False,publication_authorized=False)
    (output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n'); (output/'INCOMPLETE').unlink();return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest='cmd',required=True)
    f=sub.add_parser('fixture'); r=sub.add_parser('prepare'); k=sub.add_parser('request')
    for s in (f,r,k): s.add_argument('--plan',required=True,type=Path);s.add_argument('--output',required=True,type=Path)
    for n in ('manifest','assets','fontpath','latinfont'):r.add_argument('--'+n,required=True,type=Path)
    v=sub.add_parser('preview'); v.add_argument('--prepared',required=True,type=Path); v.add_argument('--output',required=True,type=Path); v.add_argument('--chapter',type=int,default=1)
    args=vars(ap.parse_args()); cmd=args.pop('cmd'); result={'fixture':fixture,'prepare':prepare,'preview':preview,'request':request}[cmd](**args); print(json.dumps(result,indent=2))
