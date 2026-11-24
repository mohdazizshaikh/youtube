"""Private review proxies and exact-frame reassembly of verified Phase 14S shots."""
import argparse, hashlib, html, json, math, subprocess, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
try:
    from . import phase14_shot_batch as b, phase14_media_run as m, phase14_scene_review as s
except ImportError:
    import phase14_shot_batch as b, phase14_media_run as m, phase14_scene_review as s


def digest(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file():raise ValueError('regular file required')
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def load(config, expected, batch, batch_sha, root):
    inputs,task_pin=b.load_inputs(config,expected)
    report=json.loads(m.raw(batch,batch_sha,128000));root=Path(root)
    if root.is_symlink() or (root/'RUNNING').exists():raise ValueError('active source batch')
    ids={t['id'] for x in inputs.values() for t in x[3]}
    rows=report['shots']
    if (report.get('schema'),report.get('config_sha256'),report.get('shot_count'),report.get('operation_count'),report.get('publication_authorized'),report.get('production_accepted'))!=('VIRALOS_SHOT_BATCH_RESULT_V1',expected,48,192,False,False) or len(rows)!=48 or {x['id'] for x in rows}!=ids:raise ValueError('batch identity')
    by={x['id']:x for x in rows};result={}
    for l,(video,vp,frames,tasks) in inputs.items():
        shots=[]
        for t in tasks:
            d=root/t['id'];row=by[t['id']];n=t['end_frame']-t['start_frame']
            if d.is_symlink() or (d/'INCOMPLETE').exists():raise ValueError('incomplete input shot')
            r=json.loads(m.raw(d/'receipt.json',row['receipt_sha256'],100000))
            if (r.get('schema'),r.get('task'),r.get('frames'),r.get('tasks_sha256'),r.get('source_video_sha256'),r.get('decoded_pixels_match'),r.get('silent'),r.get('production_accepted'),r.get('publication_authorized'))!=('VIRALOS_SHOT_REVIEW_V1',t,n,task_pin,vp,True,True,False,False) or row['frames']!=n:raise ValueError('shot identity')
            m.raw(d/'shot.mp4',r['clip_sha256']);m.raw(d/'midpoint.png',r['midpoint_sha256'],10_000_000)
            m.pin(r['decoded_frame_sequence_sha256']);shots.append((d,r,row['receipt_sha256']))
        result[l]=(video,vp,frames,shots)
    return result


def proxy_probe(path,n):
    data=json.loads(b.ff(['ffprobe','-v','error','-show_streams','-of','json',str(path)],20))['streams']
    if len(data)!=1:raise ValueError('proxy must be silent')
    v=data[0]
    if (v['codec_name'],v['width'],v['height'],v['pix_fmt'],v['avg_frame_rate'],v.get('nb_frames'),v.get('profile'))!=('h264',640,360,'yuv420p','30/1',str(n),'Constrained Baseline'):raise ValueError('proxy format')
    if float(v.get('start_time','nan'))!=0 or not math.isfinite(float(v.get('duration','nan'))) or abs(float(v['duration'])-n/30)>0.001:raise ValueError('proxy timing')
    # Count actual decoded frames, not merely container metadata.
    out=b.ff(['ffmpeg','-v','error','-xerror','-nostdin','-threads','2','-i',str(path),'-map','0:v:0','-an','-c:v','rawvideo','-threads','1','-pix_fmt','yuv420p','-fps_mode','passthrough','-f','framehash','-hash','sha256','-'],90).decode('ascii')
    lines=[x for x in out.splitlines() if not x.startswith('#')]
    if len(lines)!=n or any(int(x.split(',')[2])!=i for i,x in enumerate(lines)):raise ValueError('proxy decoded frame count/timing')


def proxy(output,d,r,receipt_pin):
    target=Path(output);fresh=not target.exists()
    if target.is_symlink():raise ValueError('unsafe output')
    if fresh:
        target.mkdir();(target/'INCOMPLETE').touch()
        b.ff(['ffmpeg','-v','error','-xerror','-nostdin','-n','-threads','2','-i',str(d/'shot.mp4'),'-map','0:v:0','-an','-vf','scale=640:360:flags=lanczos','-c:v','libx264','-profile:v','baseline','-level:v','3.0','-preset','veryfast','-crf','20','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(target/'proxy.mp4')],90)
    elif (target/'INCOMPLETE').exists():raise ValueError('partial proxy; rebuild elsewhere')
    proxy_probe(target/'proxy.mp4',r['frames'])
    m.raw(d/'shot.mp4',r['clip_sha256'])
    rec=dict(schema='VIRALOS_SHOT_PROXY_V1',task=r['task'],source_receipt_sha256=receipt_pin,source_clip_sha256=r['clip_sha256'],proxy_sha256=digest(target/'proxy.mp4'),frames=r['frames'],width=640,height=360,decode_pass=True,silent=True,lossless=False,browser_playback_verified=False,production_accepted=False,publication_authorized=False)
    if fresh:
        m.write_new(target/'receipt.json',s.encoded(rec));(target/'INCOMPLETE').unlink()
    elif m.raw(target/'receipt.json',limit=100000)!=s.encoded(rec):raise ValueError('proxy receipt mismatch')
    return rec



def frame_hashes_fast(path,count):
    """Exact CFR frame timestamps, followed by streaming SHA256 of decoded YUV bytes.

    Avoid FFmpeg's software framehash throughput bottleneck and large rawvideo files.
    The subprocess timer covers blocked pipe reads; keep only one frame in memory.
    """
    from threading import Timer
    import tempfile
    b.probe(path,count)
    meta=json.loads(b.ff(['ffprobe','-v','error','-select_streams','v:0','-show_streams','-show_frames','-show_entries','stream=time_base:frame=best_effort_timestamp,width,height,pix_fmt','-of','json',str(path)],120))
    from fractions import Fraction
    tb=Fraction(meta['streams'][0]['time_base']);frames=meta['frames']
    if len(frames)!=count or any(type(x.get('best_effort_timestamp')) is not int or x['best_effort_timestamp']*tb!=Fraction(i,30) or (x.get('width'),x.get('height'),x.get('pix_fmt'))!=(1920,1080,'yuv420p') for i,x in enumerate(frames)):raise ValueError('decoded timestamps/format')
    size=3110400;buf=bytearray(size);view=memoryview(buf);hashes=[]
    with tempfile.TemporaryFile() as err:
        proc=subprocess.Popen(['ffmpeg','-v','error','-xerror','-nostdin','-threads','2','-i',str(path),'-map','0:v:0','-an','-c:v','rawvideo','-threads','1','-pix_fmt','yuv420p','-fps_mode','passthrough','-f','rawvideo','-'],stdout=subprocess.PIPE,stderr=err)
        timer=Timer(300,lambda:proc.kill() if proc.poll() is None else None);timer.daemon=True;timer.start()
        try:
            for _ in range(count):
                n=0
                while n<size:
                    k=proc.stdout.readinto(view[n:])
                    if not k:raise ValueError('truncated raw frame stream')
                    n+=k
                hashes.append(hashlib.sha256(view).hexdigest())
            if proc.stdout.read(1) or proc.wait(timeout=10)!=0:raise ValueError('extra frames or decode failure')
        finally:
            timer.cancel()
            if proc.poll() is None:proc.kill();proc.wait()
            proc.stdout.close()
    return hashes


def reassemble(output,video,vp,frames,shots):
    out=Path(output);out.mkdir();(out/'INCOMPLETE').touch()
    # Fixed relative names avoid concat manifest path injection. Hardlinks preserve input bytes.
    import os
    for i,(d,r,_) in enumerate(shots):os.link(d/'shot.mp4',out/f'part{i:02}.mp4')
    manifest=out/'shots.ffconcat';manifest.write_text('ffconcat version 1.0\n'+''.join(f'file part{i:02}.mp4\n' for i in range(len(shots))),encoding='ascii')
    # All Phase 14S shots are no-B-frame H264. Explicit packet timestamps restore exact CFR.
    b.ff(['ffmpeg','-v','error','-xerror','-nostdin','-n','-f','concat','-safe','1','-i',str(manifest),'-map','0:v:0','-an','-c:v','copy','-bsf:v','setts=pts=N*512:dts=N*512:duration=512:time_base=1/15360','-video_track_timescale','15360',str(out/'silent.mp4')],180)
    final=out/'reassembled.mp4'
    b.ff(['ffmpeg','-v','error','-xerror','-nostdin','-n','-i',str(out/'silent.mp4'),'-i',str(video),'-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',str(final)],180)
    actual=frame_hashes_fast(final,frames)
    for d,r,_ in shots:
        t=r['task'];part=actual[t['start_frame']:t['end_frame']]
        if s.sha(s.encoded(part))!=r['decoded_frame_sequence_sha256'] or digest(d/'shot.mp4')!=r['clip_sha256']:raise ValueError('reassembled frame/shot mismatch')
    if digest(video)!=vp:raise ValueError('source changed')
    source_audio=m.packet_signature(video);output_audio=m.packet_signature(final)
    if source_audio!=output_audio:raise ValueError('audio packets changed')
    rec=dict(schema='VIRALOS_REASSEMBLY_V1',source_video_sha256=vp,video_sha256=digest(final),frames=frames,shot_count=len(shots),decoded_frame_sequence_sha256=s.sha(s.encoded(actual)),all_shot_sequences_match=True,audio_packet_signature=source_audio,exact_audio_packets_match=True,production_accepted=False,publication_authorized=False)
    m.write_new(out/'receipt.json',s.encoded(rec));(out/'INCOMPLETE').unlink()
    for i in range(len(shots)):(out/f'part{i:02}.mp4').unlink()
    return rec


def run(config,expected,batch,batch_sha,root,output,stage='all'):
    inputs=load(config,expected,batch,batch_sha,root);out=Path(output);out.mkdir(exist_ok=True)
    if out.is_symlink():raise ValueError('unsafe output')
    lock=out/'RUNNING'
    with lock.open('xb') as f:f.write(expected.encode('ascii'))
    start=time.monotonic()
    try:
        m.exact(out/'run.json',s.encoded(dict(config_sha256=expected,batch_sha256=batch_sha,renderer_sha256=digest(__file__),publication_authorized=False)))
        def one(l):
            video,vp,n,shots=inputs[l];records=[]
            for d,r,pin in shots:
                rec=proxy(out/r['task']['id'],d,r,pin);records.append(rec)
            return records
        if stage=='proxies' or stage=='all':
            with ThreadPoolExecutor(max_workers=2) as pool:rows=[x for group in pool.map(one,('en','hi')) for x in group]
            result=dict(schema='VIRALOS_PROXY_BATCH_V1',config_sha256=expected,batch_sha256=batch_sha,shots=rows,shot_count=len(rows),operation_count=3*len(rows),human_review_required=True,production_accepted=False,publication_authorized=False)
            m.exact(out/'proxy_batch.json',s.encoded(result))
        if stage=='assembly' or stage=='all':
            def assemble(l):return reassemble(out/('film-'+l),*inputs[l])
            with ThreadPoolExecutor(max_workers=2) as pool:films=dict(zip(('en','hi'),pool.map(assemble,('en','hi'))))
            m.write_new(out/'films.json',s.encoded(films))
        return dict(stage=stage,elapsed_s=round(time.monotonic()-start,2),production_accepted=False,publication_authorized=False)
    finally:lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('config','expected','batch','batch-sha','root','output'):p.add_argument('--'+k,required=True)
    p.add_argument('--stage',choices=('all','proxies','assembly'),default='all');print(json.dumps(run(**vars(p.parse_args())),indent=2))
