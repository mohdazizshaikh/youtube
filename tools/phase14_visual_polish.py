"""Collision-safe synthetic film recomposition. No publication authorization."""
import argparse, json, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
try:
    from . import phase14_assembly as a, phase14_quality as q, phase14_review_render as r
except ImportError:
    import phase14_assembly as a, phase14_quality as q, phase14_review_render as r

BOARD=(144,0,1632,918)
LANE=(144,930,1632,32)
CAPTION=(0,972,1920,108)


def layout_ok():
    boxes=(BOARD,LANE,CAPTION)
    return all(x>=0 and y>=0 and x+w<=1920 and y+h<=1080 for x,y,w,h in boxes) and all(y+h<=yy for (_,y,_,h),(_,yy,_,_) in zip(boxes,boxes[1:]))


def build(plan, timeline, review, receipt, ass, output, font):
    start=time.monotonic(); plan,timeline,review,receipt,ass,output,font=map(lambda p:Path(p).resolve(),(plan,timeline,review,receipt,ass,output,font))
    t=json.loads(timeline.read_text(encoding='utf8')); v=json.loads(receipt.read_text(encoding='utf8'))
    a.check_timeline(t['shots'])
    if not layout_ok() or q.sha(plan)!=a.PLAN_SHA or t.get('plan_sha256')!=a.PLAN_SHA or v.get('timeline_sha256')!=q.sha(timeline) or v.get('status')!='SYNTHETIC_PRIVATE_REVIEW_CANDIDATE' or v.get('publication_authorized') is not False or v.get('caption_basis')!='synthetic_fixture' or v.get('acoustic_alignment_verified') is not False or v.get('audit',{}).get('video_sha256')!=q.sha(review) or v.get('review_ass_sha256')!=q.sha(ass):
        raise ValueError('invalid review source chain')
    ah=r.audio_hash(review)
    if ah!=v.get('audio_packet_sha256'): raise ValueError('audio payload mismatch')
    shots=a.segments(json.loads(plan.read_text(encoding='utf8')))
    output.mkdir(exist_ok=False); (output/'INCOMPLETE').touch(); work=output/'work';work.mkdir()
    from PIL import Image,ImageDraw
    dot=Image.new('RGBA',(24,24)); ImageDraw.Draw(dot).ellipse((1,1,22,22),fill='#70e1d1');dot.save(work/'marker.png')
    (work/'review.ass').write_bytes(ass.read_bytes())
    def shot(i):
        s,rec=shots[i],t['shots'][i]; n=rec['end_frame']-rec['start_frame']; scene=s['scene']; b=s['beat']
        board=a.motion.board(a.motion.VISUALS[b],font) if scene['id']=='01' else a.film.board(scene,b,8,font)
        board.save(work/f'{i:02}.png')
        f=f"[0:v]scale=1632:918:flags=lanczos,pad=1920:1080:144:0:color=0x0b1829,drawbox=x=144:y=930:w=1632:h=32:color=0x25435a:t=fill[bg];[bg][1:v]overlay=x='144+1608*min(1,n/{max(n-1,1)})':y=934:eval=frame,format=yuv420p"
        a.film.run('ffmpeg','-v','error','-nostdin','-loop','1','-framerate','30','-i',str(work/f'{i:02}.png'),'-loop','1','-framerate','30','-i',str(work/'marker.png'),'-filter_complex_threads','1','-filter_complex',f,'-frames:v',str(n),'-an','-c:v','libx264','-preset','ultrafast','-crf','23','-threads','2',str(work/f'{i:02}.mp4'),timeout=180)
    with ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(shot,range(24)))
    (work/'concat.txt').write_text(''.join(f"file '{i:02}.mp4'\n" for i in range(24)),encoding='utf8')
    dest=output/'polished_review.mp4'
    r.run('ffmpeg','-v','error','-xerror','-nostdin','-f','concat','-safe','1','-i','concat.txt','-i',str(review),'-map','0:v:0','-map','1:a:0','-filter_threads','2','-vf','ass=review.ass','-c:v','libx264','-preset','ultrafast','-crf','23','-threads','4','-c:a','copy','-movflags','+faststart',str(dest),cwd=work,timeout=600)
    audit=a.audit(dest,q.sha(dest),t['shots'],True)
    if r.audio_hash(dest)!=ah or q.sha(review)!=v['audit']['video_sha256']: raise ValueError('audio or source changed')
    result=dict(status='SYNTHETIC_PRIVATE_REVIEW_CANDIDATE',source_sha256=q.sha(review),raw_source_sha256=t['video_sha256'],timeline_sha256=q.sha(timeline),review_ass_sha256=q.sha(ass),audio_packet_sha256=ah,audio_packet_hash_match=True,words=v['words'],shots=24,caption_basis='synthetic_fixture',caption_strip_px=108,visual_layout={'board':BOARD,'motion_lane':LANE,'caption':CAPTION},acoustic_alignment_verified=False,editorial_review_required=True,publication_authorized=False,queue_enqueued=False,elapsed_s=round(time.monotonic()-start,2),audit=audit)
    (output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8'); (output/'INCOMPLETE').unlink();return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','timeline','review','receipt','ass','output','font'):p.add_argument('--'+name,type=Path,required=True)
    print(json.dumps(build(**vars(p.parse_args())),indent=2))
