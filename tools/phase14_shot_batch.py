"""Lossless silent review-shot extraction, exact decoded frame validation and editorial handoff.
No creative acceptance, real speech, upload, or release authorization.
"""
import argparse, json, math, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
try:
    from . import phase14_media_run as m, phase14_scene_review as s
except ImportError:
    import phase14_media_run as m, phase14_scene_review as s

MAX_FRAMES=27000

def ff(args, timeout=180):
    return subprocess.run(args, check=True, capture_output=True, timeout=timeout).stdout

def frame_hashes(path, expected_count):
    # Hash decoded YUV420p frame bytes, not compressed packets or perceptual scores.
    data=ff(['ffmpeg','-v','error','-xerror','-nostdin','-threads','2','-i',str(path),'-map','0:v:0','-an','-c:v','rawvideo','-threads','2','-pix_fmt','yuv420p','-fps_mode','passthrough','-f','framehash','-hash','sha256','-'],240).decode('ascii')
    if '#tb 0: 1/30' not in data or '#dimensions 0: 1920x1080' not in data:raise ValueError('framehash format')
    rows=[]
    for line in data.splitlines():
        if line.startswith('#'):continue
        fields=[x.strip() for x in line.split(',')]
        if len(fields)!=6 or fields[0]!='0' or int(fields[1])!=len(rows) or int(fields[2])!=len(rows) or int(fields[3])!=1 or int(fields[4])!=3110400 or not re.fullmatch('[0-9a-f]{64}',fields[5]):raise ValueError('noncontiguous decoded frame or pixel format')
        rows.append(fields[5])
    if type(expected_count) is not int or not 1<=expected_count<=MAX_FRAMES or len(rows)!=expected_count:raise ValueError('decoded frame count')
    return rows

def probe(path, count, silent=False):
    d=json.loads(ff(['ffprobe','-v','error','-show_streams','-of','json',str(path)],20));streams=d['streams'];v=[x for x in streams if x['codec_type']=='video']
    if len(v)!=1 or len(streams)!=(1 if silent else 2) or (not silent and len([x for x in streams if x['codec_type']=='audio'])!=1):raise ValueError('stream count')
    x=v[0]
    if (x['codec_name'],x['width'],x['height'],x['pix_fmt'],x['avg_frame_rate'],x.get('nb_frames'))!=('h264',1920,1080,'yuv420p','30/1',str(count)):raise ValueError('video format')
    if float(x.get('start_time','nan'))!=0 or not math.isfinite(float(x.get('duration','nan'))) or abs(float(x.get('duration','nan'))-count/30)>0.001:raise ValueError('video timing')

def load_inputs(config, expected):
    c=json.loads(m.raw(config,expected,128000))
    if set(c)!={'schema','locales','tasks'} or c['schema']!='VIRALOS_SHOT_BATCH_V1' or set(c['locales'])!={'en','hi'}:raise ValueError('config')
    tasks=m.obj(c['tasks']);rows=tasks['tasks']
    if tasks.get('schema')!='VIRALOS_EDITORIAL_TASKS_V1' or tasks.get('production_accepted') is not False or tasks.get('publication_authorized') is not False or tasks.get('human_review_required') is not True or len(rows)!=48 or tasks['task_count']!=48:raise ValueError('task contract')
    result={}
    for l in ('en','hi'):
        inp=c['locales'][l]
        if set(inp)!={'video','receipt'}:raise ValueError('inventory')
        r=m.obj(inp['receipt']);video=Path(inp['video']['path']).resolve(strict=True);vp=m.pin(inp['video']['sha256']);m.envelope(inp['video']);frames=m.validate_receipt(r,l,vp,r['source_video_sha256']);probe(video,frames)
        if tasks['sources'][l]['video_sha256']!=vp:raise ValueError('task video identity')
        ts=sorted((x for x in rows if x['locale']==l),key=lambda x:x['shot'])
        if len(ts)!=24:raise ValueError('task inventory')
        for i,(t,sh) in enumerate(zip(ts,r['shots'])):
            a,z=sh['start_frame'],sh['end_frame'];n=t['freeze_frames']
            if (t['id'],t['shot'],t['chapter'],t['video_sha256'],t['start_frame'],t['end_frame'],t['status'])!=(f'{l}-{i+1:02}',i,i//3+1,vp,a,z,'OPEN') or type(n) is not int or not 0<=n<=z-a or t['human_review_required'] is not True:raise ValueError('task frame identity')
            if t['priority']!=('P0_MOTION_REVIEW' if n else 'P1_EDITORIAL_REVIEW') or t['detector_status']!=('UNEXPECTED_FREEZE_REVIEW' if n else 'NO_FREEZE_DETECTED') or t['freeze_fraction']!=round(n/(z-a),6):raise ValueError('task flag mismatch')
        result[l]=(video,vp,frames,ts)
    if sum(t['freeze_frames']>0 for x in result.values() for t in x[3])!=tasks['motion_review_count']:raise ValueError('flag aggregate')
    return result,c['tasks']['sha256']

def shot(out, video, vp, task, source_hashes, tasks_pin):
    a,z=task['start_frame'],task['end_frame'];count=z-a;clip=out/'shot.mp4';still=out/'midpoint.png';rec=out/'receipt.json';expected=source_hashes[a:z]
    if len(expected)!=count:raise ValueError('source range')
    fresh=not out.exists()
    if out.is_symlink():raise ValueError('unsafe shot folder')
    if fresh:
        out.mkdir();(out/'INCOMPLETE').touch()
        ff(['ffmpeg','-v','error','-xerror','-nostdin','-n','-threads','2','-ss',f'{a/30:.12f}','-i',str(video),'-map','0:v:0','-an','-frames:v',str(count),'-c:v','libx264','-preset','ultrafast','-qp','0','-threads','2','-pix_fmt','yuv420p',str(clip)])
    elif (out/'INCOMPLETE').exists() or not rec.is_file():raise ValueError('incomplete shot; recover to new folder')
    # Always independently verify actual decoded frame sequence; no cached success shortcut.
    probe(clip,count,True);actual=frame_hashes(clip,count)
    if actual!=expected:raise ValueError('decoded shot differs from source range')
    midpoint=count//2
    if fresh:
        ff(['ffmpeg','-v','error','-xerror','-nostdin','-n','-threads','2','-ss',f'{midpoint/30:.12f}','-i',str(clip),'-map','0:v:0','-frames:v','1','-threads','1','-update','1',str(still)],30)
    from PIL import Image
    with Image.open(still) as im:
        if im.format!='PNG' or im.size!=(1920,1080):raise ValueError('midpoint image')
        im.verify()
    r=dict(schema='VIRALOS_SHOT_REVIEW_V1',task=task,source_video_sha256=vp,tasks_sha256=tasks_pin,clip_sha256=s.sha(m.raw(clip)),midpoint_sha256=s.sha(m.raw(still,limit=10_000_000)),midpoint_source_frame=a+midpoint,frames=count,decoded_frame_sequence_sha256=s.sha(s.encoded(actual)),decoded_pixels_match=True,silent=True,production_accepted=False,publication_authorized=False)
    if fresh:
        m.write_new(rec,s.encoded(r));(out/'INCOMPLETE').unlink()
    else:
        if m.raw(rec,limit=100000)!=s.encoded(r):raise ValueError('cached receipt mismatch')
    return r,'created' if fresh else 'revalidated'

def run(config,expected,output,select=None):
    inputs,tasks_pin=load_inputs(config,expected);root=Path(output);start=time.monotonic()
    if root.is_symlink():raise ValueError('unsafe output')
    root.mkdir(exist_ok=True);lock=root/'RUNNING'
    if select is not None and not re.fullmatch('(en|hi)-(0[1-9]|1[0-9]|2[0-4])',select):raise ValueError('shot selector')
    with lock.open('xb') as f:f.write(expected.encode('ascii'))
    try:
        m.exact(root/'run.json',s.encoded(dict(schema='VIRALOS_SHOT_BATCH_RUN_V1',config_sha256=expected,renderer_sha256=s.sha(Path(__file__).read_bytes()),publication_authorized=False)))
        def locale(l):
            video,vp,frames,ts=inputs[l];hashes=frame_hashes(video,frames)
            result=[]
            for t in ts:
                if select is not None and t['id']!=select:continue
                r,state=shot(root/t['id'],video,vp,t,hashes,tasks_pin);result.append(dict(id=t['id'],state=state,receipt_sha256=s.sha(s.encoded(r)),frames=r['frames'],operations=['shot_clip_materialized','decoded_frame_sequence_verified','midpoint_image_materialized_and_validated','editorial_task_bound']))
            if s.sha(m.raw(video))!=vp:raise ValueError('source changed')
            return result
        langs=('en','hi') if select is None else (select[:2],)
        with ThreadPoolExecutor(max_workers=2) as p:results=[x for group in p.map(locale,langs) for x in group]
        report=dict(schema='VIRALOS_SHOT_BATCH_RESULT_V1',config_sha256=expected,shots=results,shot_count=len(results),operation_count=sum(len(x['operations']) for x in results),decoded_frames=sum(x['frames'] for x in results),created=sum(x['state']=='created' for x in results),revalidated=sum(x['state']=='revalidated' for x in results),elapsed_s=round(time.monotonic()-start,2),human_review_required=True,production_accepted=False,publication_authorized=False)
        return report
    finally:lock.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('config','expected','output'):p.add_argument('--'+k,required=True)
    p.add_argument('--select');print(json.dumps(run(**vars(p.parse_args())),ensure_ascii=False,indent=2))
