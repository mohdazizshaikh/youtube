"""Render declared owner Hindi narration with freshly measured frame boundaries; no unverified captions."""
import argparse,json,subprocess,time,wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import ImageDraw
try:
    from . import phase14_localize as loc, phase14_bilingual as b, phase14_reviewed_timing as timing
except ImportError:
    import phase14_localize as loc, phase14_bilingual as b, phase14_reviewed_timing as timing

def render(plan,manifest,assets,expected,output,fontpath,latinfont,fixture=False):
    p,rows,texts,pairs=timing.hindi_inputs(plan,manifest,assets,expected)
    out=Path(output).resolve();out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch();work=out/'work';work.mkdir();start=time.monotonic()
    with wave.open(str(work/'narration.wav'),'wb') as w:
        w.setparams((1,2,48000,0,'NONE','not compressed'))
        for pcm,r in pairs:w.writeframes(pcm+b'\0'*(r['padding_samples']*2))
    for i in range(24):
        im=loc.board(p['chapters'][i//3],i%3,fontpath,latinfont)
        d=ImageDraw.Draw(im);d.rectangle((75,965,1845,1080),fill='#101f32');loc.line(d,'ARTIFICIAL PCM TEST / NO SPEECH / NO RELEASE' if fixture else 'DECLARED OWNER AUDIO / ALIGNMENT PENDING / NO RELEASE',(100,990),loc.font(latinfont,33),'#ffdf87',1700);im.save(work/f'{i:02}.png')
    def shot(i):
        f=f'{i:02}';n=rows[i]['end_frame']-rows[i]['start_frame']
        # A shot-index progress line sits in the bottom lane, never over the scaled board.
        vf=f"scale=1632:918,pad=1920:1080:144:0:color=0x101f32,drawbox=x=144:y=945:w=1632:h=12:color=0x365366:t=fill,drawbox=x=144:y=945:w={68*(i+1)}:h=12:color=0x79dfcc:t=fill"
        subprocess.run(['ffmpeg','-v','error','-xerror','-nostdin','-n','-loop','1','-framerate','30','-i',f+'.png','-vf',vf,'-frames:v',str(n),'-an','-c:v','libx264','-threads','2','-filter_threads','1','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',f+'.mp4'],cwd=work,check=True,capture_output=True,timeout=180)
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(shot,range(24)))
    (work/'concat.txt').write_text(''.join(f"file '{i:02}.mp4'\n" for i in range(24)),encoding='ascii');video=out/'owner_hindi_review.mp4'
    loc.run('ffmpeg','-v','error','-xerror','-nostdin','-n','-f','concat','-safe','1','-i',str(work/'concat.txt'),'-i',str(work/'narration.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(video),timeout=300)
    report=b.audit(video,rows[-1]['end_frame']);report.update(schema='VIRALOS_HINDI_OWNER_REVIEW_V1',locale='hi-IN',manifest_sha256=expected,plan_sha256=loc.digest(loc.read(plan,100000)),narration_sha256=loc.digest(loc.read(work/'narration.wav',90_000_000)),shots=rows,caption_basis='omitted_no_verified_alignment',artificial_pcm_fixture=fixture,natural_voice_verified=False,acoustic_alignment_verified=False,human_review_required=True,elapsed_seconds=round(time.monotonic()-start,2));b.dump(out/'receipt.json',report);(out/'INCOMPLETE').unlink();return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','manifest','assets','expected','output','fontpath','latinfont'):p.add_argument('--'+n,required=True)
    p.add_argument('--fixture',action='store_true')
    print(json.dumps(render(**vars(p.parse_args())),indent=2))
