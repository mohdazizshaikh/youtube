"""Native 1080p chapter-three/four digest comparisons; resumable shot checkpoints, review only."""
import argparse, hashlib, json, math, os, subprocess, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, features
try:
    from . import phase14_semantic_film as film, phase14_bilingual as b, phase14_media_run as media, phase14_scene_review as s
except ImportError:
    import phase14_semantic_film as film, phase14_bilingual as b, phase14_media_run as media, phase14_scene_review as s

A,B=(f'{int(hashlib.sha256(x).hexdigest(),16):0256b}' for x in (b'hello',b'Hello'))
X=tuple(int(a!=b) for a,b in zip(A,B)); TOTAL=sum(X)
TEXT={
'en':('Compare corresponding output bits','Amber: different • Teal: equal','This experiment, not a security score','Bits compared','Different','Equal','The count cannot identify the changed input.'),
'hi':('समान स्थान वाले आउटपुट बिट मिलाएँ','पीला: अलग • हरा: समान','यह प्रयोग है, सुरक्षा स्कोर नहीं','जाँचे गए बिट','अलग','समान','बिट की संख्या से बदला हुआ अक्षर पता नहीं चलता।')}
BG='#0b1829'; PANEL='#17334a'; GOLD='#ffd36a'; TEAL='#65e0cf'; WHITE='#f1f5f9'; MUTED='#a8c0d1'

def cmd(args,timeout=180):
    return subprocess.run(args,check=True,capture_output=True,timeout=timeout)

def progress(frame,count):
    if type(frame) is not int or type(count) is not int or not 30<=count<=2700 or not 0<=frame<count:raise ValueError('frame range')
    # Scan all corresponding positions, reaching the exact final result at the last frame.
    return min(256,1+frame*255//(count-1))

def layout(locale,beat,font):
    if locale not in TEXT or type(beat) is not int or not 0<=beat<3 or not features.check('raqm'):raise ValueError('locale/beat/RAQM')
    fs={n:ImageFont.truetype(str(font),n,layout_engine=ImageFont.Layout.RAQM) for n in (28,34,40,52,66)}
    im=Image.new('RGB',(1920,1080),BG);d=ImageDraw.Draw(im);t=TEXT[locale]
    def text(x,y,value,n,color=WHITE,maxw=1780):
        if fs[n].getlength(value)>maxw:raise ValueError('unsafe text width')
        d.text((x,y),value,font=fs[n],fill=color)
    text(70,38,'SHA-256  /  04  /  '+str(beat+1),34,TEAL)
    text(70,95,t[beat],52)
    text(70,175,'hello  ↔  Hello',40,GOLD)
    # Each cell represents the XOR of corresponding digest bits, never the algorithm's internal state.
    for j in range(256):
        x=74+(j%32)*54;y=260+(j//32)*59
        d.rounded_rectangle((x,y,x+46,y+49),radius=5,fill='#29455b')
    d.rounded_rectangle((70,762,1850,917),radius=16,fill=PANEL)
    text(100,783,t[3],34,MUTED,maxw=470);text(700,783,t[4],34,GOLD,maxw=480);text(1300,783,t[5],34,TEAL,maxw=450)
    text(70,942,t[6],34,MUTED)
    text(70,1000,'SYNTHETIC NARRATION  /  SHOT-LEVEL REVIEW  /  NOT FOR RELEASE',28,GOLD)
    return im,fs

def image_at(base,fonts,frame,count):
    n=progress(frame,count);im=base.copy();d=ImageDraw.Draw(im)
    for j in range(n):
        x=74+(j%32)*54;y=260+(j//32)*59
        d.rounded_rectangle((x,y,x+46,y+49),radius=5,fill=GOLD if X[j] else TEAL)
    # The active cell shows which actual bit pair is being compared.
    j=n-1;x=74+(j%32)*54;y=260+(j//32)*59
    d.rounded_rectangle((x-3,y-3,x+49,y+52),radius=6,outline=WHITE,width=3)
    for x,v,c in ((100,f'{n} / 256',WHITE),(700,str(sum(X[:n])),GOLD),(1300,str(n-sum(X[:n])),TEAL)):
        d.text((x,828),v,font=fonts[52],fill=c)
    return im

HEX=(hashlib.sha256(b'hello').hexdigest(),hashlib.sha256(b'Hello').hexdigest())
CODE_TEXT={'en':('Compute the first digest','Repeat with capital H','Compare the complete hexadecimal results','64 hexadecimal digits per digest'),
'hi':('पहला डाइजेस्ट निकालें','बड़े H के साथ दोहराएँ','पूरे हेक्स परिणामों की तुलना','हर डाइजेस्ट में 64 हेक्स अंक')}

def code_layout(locale,beat,font):
    if locale not in CODE_TEXT or type(beat) is not int or not 0<=beat<3 or not features.check('raqm'):raise ValueError('locale/beat/RAQM')
    fs={n:ImageFont.truetype(str(font),n,layout_engine=ImageFont.Layout.RAQM) for n in (28,32,40,48,54)}
    im=Image.new('RGB',(1920,1080),BG);d=ImageDraw.Draw(im)
    def text(x,y,v,n,c=WHITE,maxw=1780):
        if fs[n].getlength(v)>maxw:raise ValueError('unsafe text width')
        d.text((x,y),v,font=fs[n],fill=c)
    text(70,35,'SHA-256  /  03  /  '+str(beat+1),32,TEAL);text(70,91,CODE_TEXT[locale][beat],54)
    text(70,170,'import hashlib',40,TEAL)
    for k,value in enumerate(('hello','Hello')):
        y=240+k*310;d.rounded_rectangle((70,y,1850,y+285),radius=16,fill=PANEL)
        text(98,y+15,f"hashlib.sha256(b'{value}').hexdigest()",40,GOLD if k==beat else WHITE)
        for j in range(64):
            x=98+j%32*54;yy=y+89+j//32*86
            d.rounded_rectangle((x,yy,x+47,yy+72),radius=5,fill='#29455b')
    text(70,890,CODE_TEXT[locale][3],40,TEAL)
    text(70,1000,'SYNTHETIC NARRATION  /  SHOT-LEVEL REVIEW  /  NOT FOR RELEASE',28,GOLD)
    return im,fs

def code_image_at(base,fonts,frame,count,beat):
    n=min(64,1+(progress(frame,count)-1)*63//255);im=base.copy();d=ImageDraw.Draw(im)
    for k,digest in enumerate(HEX):
        upto=n if k==beat and beat<2 else 64 if k<beat or beat==2 else 0
        for j in range(upto):
            x=98+j%32*54;y=329+k*310+j//32*86
            color=GOLD if beat==2 and j<n and HEX[0][j]!=HEX[1][j] else TEAL if beat==2 and j<n else WHITE
            d.rounded_rectangle((x,y,x+47,y+72),radius=5,fill='#38546b' if color==WHITE else '#284450')
            d.text((x+10,y+6),digest[j],font=fonts[48],fill=color)
            if j==n-1 and (k==beat or beat==2):d.rounded_rectangle((x-2,y-2,x+49,y+74),radius=6,outline=GOLD,width=3)
    d.text((1420,890),f'{n} / 64',font=fonts[40],fill=WHITE)
    return im

def verify_clip(path,count):
    info=json.loads(cmd(['ffprobe','-v','error','-show_streams','-of','json',str(path)]).stdout)['streams']
    if len(info)!=1:raise ValueError('silent shot required')
    v=info[0]
    if (v.get('codec_name'),v.get('width'),v.get('height'),v.get('pix_fmt'),v.get('avg_frame_rate'),int(v.get('nb_frames',0)))!=('h264',1920,1080,'yuv420p','30/1',count) or abs(float(v['duration'])-count/30)>.001:raise ValueError('shot stream mismatch')
    cmd(['ffmpeg','-v','error','-xerror','-nostdin','-i',str(path),'-f','null','-'])
    return media.s.sha(media.raw(path))

def shot(root,identity,locale,beat,count,font,chapter=4):
    video=root/f'shot{beat}.mp4';receipt=root/f'shot{beat}.json'
    if video.exists() or receipt.exists() or video.is_symlink() or receipt.is_symlink():
        data=json.loads(media.raw(receipt,limit=50000));expected=dict(run_sha256=identity,beat=beat,frames=count,video_sha256=verify_clip(video,count),publication_authorized=False)
        if data!=expected:raise ValueError('checkpoint mismatch; preserve and rebuild in new folder')
        return 'reused',expected
    base,fonts=(layout if chapter==4 else code_layout)(locale,beat,font);tmp=root/f'shot{beat}.partial.mp4'
    if tmp.exists() or tmp.is_symlink():raise ValueError('partial shot exists; rebuild in new folder')
    # Native-resolution raw RGB frames; no image rescaling or interpolated text.
    proc=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-xerror','-n','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','30','-i','-','-an','-c:v','libx264','-threads','2','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',str(tmp)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for f in range(count):proc.stdin.write((image_at(base,fonts,f,count) if chapter==4 else code_image_at(base,fonts,f,count,beat)).tobytes())
        proc.stdin.close();err=proc.stderr.read();rc=proc.wait(timeout=180)
        if rc:raise RuntimeError(err.decode(errors='replace'))
    except BaseException:
        proc.kill();proc.wait();raise
    pin=verify_clip(tmp,count);os.link(tmp,video);tmp.unlink()
    data=dict(run_sha256=identity,beat=beat,frames=count,video_sha256=pin,publication_authorized=False)
    media.write_new(receipt,s.encoded(data));return 'created',data

def run(locale,video,receipt,expected,font,output,stage='all',chapter=4):
    if locale not in TEXT or stage not in ('first','all') or type(chapter) is not int or chapter not in (3,4):raise ValueError('stage/locale')
    r=json.loads(media.raw(receipt,expected,2_000_000));vpin=media.pin(r['audit']['video_sha256'])
    media.raw(video,vpin);media.validate_receipt(r,locale,vpin,r['source_video_sha256'])
    fontpin=s.sha(media.raw(font,limit=30_000_000));codepin=s.sha(Path(__file__).read_bytes())
    rows=r['shots'][(chapter-1)*3:chapter*3];counts=[x['end_frame']-x['start_frame'] for x in rows];total=sum(counts)
    runinfo=dict(schema='VIRALOS_NATIVE_CHAPTER_RUN_V1',locale=locale,chapter=chapter,source_sha256=vpin,receipt_sha256=expected,font_sha256=fontpin,renderer_sha256=codepin,counts=counts,publication_authorized=False)
    identity=s.sha(s.encoded(runinfo));root=Path(output)
    if root.is_symlink():raise ValueError('unsafe output')
    root.mkdir(exist_ok=True);lock=root/'RUNNING'
    with lock.open('xb') as f:f.write(identity.encode('ascii'))
    try:
        media.exact(root/'run.json',s.encoded(runinfo));states=[];start=time.monotonic()
        for beat,count in enumerate(counts[:1] if stage=='first' else counts):
            state,data=shot(root,identity,locale,beat,count,font,chapter);states.append(dict(state=state,**data))
        if stage=='first':return dict(run_sha256=identity,shots=states,publication_authorized=False)
        dest=root/'native_chapter.mp4'
        if dest.exists() or dest.is_symlink():raise ValueError('final exists; inspect existing receipt')
        media.write_new(root/'shots.ffconcat',('ffconcat version 1.0\n'+''.join(f"file 'shot{i}.mp4'\n" for i in range(3))).encode('ascii'))
        # Cut actual chapter PCM by decoded sample index, re-encode excerpt only. No claim of packet preservation.
        a=rows[0]['start_frame']*1600;z=rows[-1]['end_frame']*1600
        cmd(['ffmpeg','-v','error','-nostdin','-xerror','-n','-f','concat','-safe','1','-i',str(root/'shots.ffconcat'),'-i',str(video),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af',f'atrim=start_sample={a}:end_sample={z},asetpts=PTS-STARTPTS','-c:a','aac','-b:a','160k','-movflags','+faststart',str(dest)],300)
        audit=b.audit(dest,total);media.raw(video,vpin)
        if s.sha(media.raw(font,limit=30_000_000))!=fontpin:raise ValueError('font changed')
        report=dict(schema='VIRALOS_NATIVE_CHAPTER_REVIEW_V1',run_sha256=identity,locale=locale,chapter=chapter,source_sha256=vpin,source_start_frame=rows[0]['start_frame'],source_end_frame=rows[-1]['end_frame'],shots=states,frames=total,source_raster=[1920,1080],differing_bits=TOTAL,audit=audit,elapsed_seconds=round(time.monotonic()-start,2),audio_reencoded=True,caption_basis='omitted_no_verified_alignment',human_review_required=True,publication_authorized=False)
        media.write_new(root/'receipt.json',s.encoded(report));return report
    finally:lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('locale','video','receipt','expected','font','output'):p.add_argument('--'+x,required=True)
    p.add_argument('--stage',choices=('first','all'),default='all');p.add_argument('--chapter',type=int,choices=(3,4),default=4);print(json.dumps(run(**vars(p.parse_args())),indent=2,ensure_ascii=False))
