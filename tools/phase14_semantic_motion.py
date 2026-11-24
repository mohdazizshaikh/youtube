"""Original semantic chapter-one animation, synthetic audio review only."""
import argparse, hashlib, json, subprocess, time, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
try:
    from . import phase14_bilingual as b
except ImportError:
    import phase14_bilingual as b

W,H=960,540
BG='#0b1829'; WHITE='#f2f5f8'; MUTED='#a8c0d1'; TEAL='#63dfcf'; GOLD='#ffd36a'; PANEL='#152e45'

def experiment():
    a,b=(hashlib.sha256(x).digest() for x in (b'hello',b'Hello'))
    bits=[(x>>i)&1 for x in bytes(x^y for x,y in zip(a,b)) for i in range(7,-1,-1)]
    return a.hex(),b.hex(),bits

def load_chain(video,receipt,timeline,receipt_sha,timeline_sha):
    from pathlib import Path
    r,t=[json.loads(Path(p).read_bytes()) for p in (receipt,timeline)]
    if b.q.sha(Path(receipt))!=b.pin(receipt_sha) or b.q.sha(Path(timeline))!=b.pin(timeline_sha):raise ValueError('receipt pin mismatch')
    if r.get('status')!='SYNTHETIC_PRIVATE_REVIEW_CANDIDATE' or r.get('caption_basis')!='synthetic_fixture' or r.get('publication_authorized') is not False or r.get('timeline_sha256')!=timeline_sha or r.get('raw_source_sha256')!=t.get('video_sha256') or r['audit']['frames']!=t['frames']:raise ValueError('source chain mismatch')
    if b.q.sha(Path(video))!=b.pin(r['audit']['video_sha256']):raise ValueError('video pin mismatch')
    shots=t['shots'];cursor=0
    if len(shots)!=24:raise ValueError('24 shots required')
    for i,s in enumerate(shots):
        n=s['samples'];f=(n+1599)//1600
        if type(n) is not int or not 48000<=n<=4320000 or (s['chapter'],s['beat'],s['start_frame'],s['end_frame'],s['padding_samples'])!=(f'{i//3+1:02}',i%3,cursor,cursor+f,f*1600-n):raise ValueError('timeline mismatch')
        cursor+=f
    if cursor!=t['frames'] or not 720<=shots[2]['end_frame']<=2700:raise ValueError('duration bound')
    return r,[s['end_frame'] for s in shots[:3]]

def frame(shot,p,fonts):
    if type(shot) is not int or not 0<=shot<3 or not math.isfinite(p) or not 0<=p<=1:raise ValueError('invalid animation phase')
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im);large,medium,small=fonts
    def text(x,y,s,f=medium,c=WHITE):d.text((x,y),s,font=f,fill=c)
    def box(x,y,w,h,c=PANEL):d.rounded_rectangle((x,y,x+w,y+h),radius=12,fill=c)
    text(40,22,'SHA-256  /  CHAPTER 01',small,TEAL)
    if shot==0:
        text(40,62,'Would you notice one changed byte?',large)
        for i,label in enumerate(('download A','download B')):
            x=40+i*460;box(x,150,420,254);text(x+24,170,label,medium,MUTED)
            for j in range(5):
                changed=i==1 and j==0 and p>=.35
                color=GOLD if changed else TEAL
                box(x+24+j*73,252,64,76,'#29455b');text(x+42+j*73,271,'H' if changed else 'hello'[j],large,color)
            text(x+24,350,'5 bytes',small,MUTED)
        if p>=.35:text(40,424,'Same length. Different contents.',medium,GOLD)
        else:text(40,424,'Two downloads can look identical.',medium,MUTED)
    elif shot==1:
        text(40,62,'Compare the exact five input bytes',large)
        for i,value in enumerate((b'hello',b'Hello')):
            y=150+i*130; text(42,y+15,value.decode(),medium)
            for j,v in enumerate(value):
                x=240+j*130;box(x,y,110,90,'#29455b')
                text(x+30,y+15,f'{v:02X}',large,GOLD if i==1 and j==0 else TEAL)
                text(x+38,y+58,chr(v),small,MUTED)
                if j==min(4,int(p*5)):d.rounded_rectangle((x,y,x+110,y+90),radius=12,outline=WHITE,width=3)
        text(40,424,'0x68 → 0x48   |   exactly one byte differs',medium,GOLD)
    else:
        text(40,62,'One byte in. A different fingerprint out.',large)
        a,bits_b,bits=experiment();n=min(256,int(p*320)); count=sum(bits[:n]);text(40,125,'SHA-256 output comparison  •  256 bits',medium,MUTED)
        for j,bit in enumerate(bits):
            x=42+(j%32)*26;y=185+(j//32)*25
            color=GOLD if j<n and bit else TEAL if j<n else '#29455b'
            d.rounded_rectangle((x,y,x+20,y+19),radius=3,fill=color)
        text(42,403,f'{count} / 256 differing bits revealed',medium,GOLD)
        text(42,440,'Illustrative reveal, not internal SHA-256 computation.',small,MUTED)
    text(40,494,'SYNTHETIC NARRATION  •  SHOT-LEVEL TIMING  •  NOT FOR RELEASE',small,GOLD)
    return im

def render(video,receipt,timeline,receipt_sha,timeline_sha,font,output):
    start=time.monotonic();video=Path(video).resolve(strict=True);r,ends=load_chain(video,receipt,timeline,receipt_sha,timeline_sha)
    fonts=[ImageFont.truetype(str(font),s) for s in (32,24,17)]
    out=Path(output).resolve();out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch()
    dest=out/'semantic_chapter.mp4';frames=ends[-1]
    # Raw RGB source is intentionally 960x540, output is explicitly upscaled.
    cmd=['ffmpeg','-nostdin','-v','error','-xerror','-n','-f','rawvideo','-pix_fmt','rgb24','-s','960x540','-r','30','-i','pipe:0','-i',str(video),'-map','0:v:0','-map','1:a:0','-t',f'{frames/30:.9f}','-vf','scale=1920:1080:flags=lanczos','-c:v','libx264','-threads','4','-filter_threads','1','-preset','fast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-ar','48000','-ac','1','-movflags','+faststart',str(dest)]
    with (out/'encode.log').open('xb') as log:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
        try:
            begin=0
            for shot,end in enumerate(ends):
                for i in range(end-begin):proc.stdin.write(frame(shot,i/max(1,end-begin-1),fonts).tobytes())
                begin=end
            proc.stdin.close()
            if proc.wait(timeout=120):raise RuntimeError('encode failed')
        except BaseException:
            proc.kill();proc.wait();raise
    audit=b.audit(dest,frames)
    if b.q.sha(video)!=r['audit']['video_sha256']:raise ValueError('source changed')
    a,h,bits=experiment();report=dict(schema='VIRALOS_SEMANTIC_MOTION_REVIEW_V1',source_video_sha256=r['audit']['video_sha256'],source_receipt_sha256=receipt_sha,timeline_sha256=timeline_sha,shot_end_frames=ends,source_raster=[960,540],hash_hello=a,hash_Hello=h,differing_bits=sum(bits),caption_basis='omitted_no_verified_alignment',audio_reencoded=True,audit=audit,elapsed_seconds=round(time.monotonic()-start,2),acoustic_alignment_verified=False,publication_authorized=False,human_review_required=True)
    b.dump(out/'receipt.json',report);(out/'INCOMPLETE').unlink();return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('video','receipt','timeline','receipt-sha','timeline-sha','font','output'):p.add_argument('--'+n,required=True)
    print(json.dumps(render(**vars(p.parse_args())),indent=2))
