"""Recover a previously verified shot into a fresh folder using its external receipt pin.
Incomplete original media is never edited. Newly generated clip must match decoded frame digest.
"""
import argparse, json, re
from pathlib import Path
try:
    from . import phase14_shot_batch as b, phase14_media_run as m, phase14_scene_review as s
except ImportError:
    import phase14_shot_batch as b, phase14_media_run as m, phase14_scene_review as s


def snapshot(folder):
    p=Path(folder)
    if p.is_symlink() or not p.is_dir() or not (p/'INCOMPLETE').is_file():raise ValueError('incomplete shot folder required')
    allowed={'INCOMPLETE','shot.mp4','midpoint.png','receipt.json'};out={}
    for x in p.iterdir():
        if x.name not in allowed or x.is_symlink() or not x.is_file() or x.stat().st_size>m.LIMIT:raise ValueError('unsafe interrupted inventory')
        out[x.name]=s.sha(x.read_bytes())
    return out


def recover(config,expected,select,receipt,receipt_sha,interrupted,output):
    if not re.fullmatch('(en|hi)-(0[1-9]|1[0-9]|2[0-4])',select):raise ValueError('shot selector')
    inputs,tasks_pin=b.load_inputs(config,expected);video,vp,_,tasks=inputs[select[:2]];task=tasks[int(select[3:])-1]
    original=json.loads(m.raw(receipt,receipt_sha,100000));a,z=task['start_frame'],task['end_frame'];n=z-a
    if original.get('schema')!='VIRALOS_SHOT_REVIEW_V1' or original.get('task')!=task or original.get('source_video_sha256')!=vp or original.get('tasks_sha256')!=tasks_pin or original.get('frames')!=n or original.get('midpoint_source_frame')!=a+n//2 or original.get('decoded_pixels_match') is not True or original.get('silent') is not True or original.get('publication_authorized') is not False or original.get('production_accepted') is not False:raise ValueError('reference receipt identity')
    digest=m.pin(original['decoded_frame_sequence_sha256']);old=Path(interrupted);before=snapshot(old);out=Path(output)
    if old.resolve() in out.resolve().parents or out.resolve()==old.resolve():raise ValueError('new directory outside interrupted shot required')
    out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch();clip=out/'shot.mp4';still=out/'midpoint.png'
    b.ff(['ffmpeg','-v','error','-xerror','-nostdin','-n','-threads','2','-ss',f'{a/30:.12f}','-i',str(video),'-map','0:v:0','-an','-frames:v',str(n),'-c:v','libx264','-preset','ultrafast','-qp','0','-threads','2','-pix_fmt','yuv420p',str(clip)])
    b.probe(clip,n,True);decoded=s.sha(s.encoded(b.frame_hashes(clip,n)))
    if decoded!=digest or s.sha(m.raw(video))!=vp:raise ValueError('recovered frame sequence differs')
    b.ff(['ffmpeg','-v','error','-xerror','-nostdin','-n','-threads','2','-ss',f'{(n//2)/30:.12f}','-i',str(clip),'-map','0:v:0','-frames:v','1','-threads','1','-update','1',str(still)],30)
    from PIL import Image
    with Image.open(still) as im:
        if im.format!='PNG' or im.size!=(1920,1080):raise ValueError('midpoint format')
        im.verify()
    recovered_clip=s.sha(m.raw(clip));recovered_still=s.sha(m.raw(still,limit=10000000))
    if snapshot(old)!=before:raise ValueError('interrupted inventory changed')
    r=dict(schema='VIRALOS_SHOT_RECOVERY_V1',id=select,config_sha256=expected,reference_receipt_sha256=receipt_sha,source_video_sha256=vp,decoded_frame_sequence_sha256=decoded,frames=n,decoded_pixels_match=True,interrupted_inventory=before,interrupted_unchanged=True,clip_sha256=recovered_clip,midpoint_sha256=recovered_still,compressed_clip_bytes_match=original['clip_sha256']==recovered_clip,midpoint_bytes_match=original['midpoint_sha256']==recovered_still,task=task,production_accepted=False,publication_authorized=False)
    m.write_new(out/'recovery.json',s.encoded(r));(out/'INCOMPLETE').unlink();return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('config','expected','select','receipt','receipt-sha','interrupted','output'):p.add_argument('--'+k,required=True)
    print(json.dumps(recover(**vars(p.parse_args())),ensure_ascii=False,indent=2))
