"""Pinned bilingual semantic review handoff, resumable media QC; never grants release."""
import argparse, hashlib, json, os, re, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
try:
    from . import phase14_integrated_qc as q, phase14_recovery_qc as r, phase14_scene_review as s
except ImportError:
    import phase14_integrated_qc as q, phase14_recovery_qc as r, phase14_scene_review as s

LIMIT=128*1024*1024
LANGS=('en','hi')

def pin(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('SHA256 required')
    return value

def raw(path,expected=None,limit=LIMIT):
    p=Path(path)
    if p.is_symlink() or not p.is_file():raise ValueError('regular file required')
    with p.open('rb') as f:b=f.read(limit+1)
    if not b or len(b)>limit or (expected is not None and s.sha(b)!=pin(expected)):raise ValueError('asset size/hash')
    return b

def envelope(item,limit=LIMIT):
    if not isinstance(item,dict) or set(item)!={'path','sha256'}:raise ValueError('pin envelope')
    return raw(item['path'],item['sha256'],limit)

def obj(item):
    x=json.loads(envelope(item,2_000_000))
    if not isinstance(x,dict):raise ValueError('object required')
    return x

def write_new(path,data):
    # Atomic create without overwriting an existing file, under a trusted owner directory.
    p=Path(path)
    if p.exists() or p.is_symlink():raise ValueError('existing output')
    with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as f:
        tmp=Path(f.name);f.write(data);f.flush();os.fsync(f.fileno())
    try:os.link(tmp,p)
    finally:tmp.unlink()

def exact(path,data):
    p=Path(path)
    if p.exists() or p.is_symlink():
        if raw(p,limit=max(1,len(data)))!=data:raise ValueError('cached bytes differ; recover into fresh folder')
        return 'reused'
    write_new(p,data);return 'created'

def packet_signature(path):
    # Compare exact compressed packet hashes and integer stream timestamps, including priming side data.
    cmd=['ffprobe','-v','error','-select_streams','a:0','-show_streams','-show_packets','-show_data_hash','sha256','-show_entries','stream=time_base,codec_name,sample_rate,channels:packet=pts,dts,duration,size,data_hash,side_data_list','-of','json',str(path)]
    p=subprocess.run(cmd,check=True,capture_output=True,timeout=90)
    if len(p.stdout)>20_000_000:raise ValueError('packet evidence limit')
    d=json.loads(p.stdout);streams=d['streams'];packets=d['packets']
    if len(streams)!=1 or streams[0].get('codec_name')!='aac' or streams[0].get('sample_rate')!='48000' or streams[0].get('channels')!=1 or streams[0].get('time_base')!='1/48000' or not 1<=len(packets)<=45000:raise ValueError('audio packet contract')
    for packet in packets:
        if any(type(packet.get(k)) is not int for k in ('pts','dts','duration')) or packet['duration']<=0 or not re.fullmatch('SHA256:[0-9a-f]{64}',packet.get('data_hash','')):raise ValueError('packet timestamp/hash missing')
    return dict(count=len(packets),sha256=s.sha(s.encoded(dict(stream=streams[0],packets=packets))))

def validate_receipt(receipt,locale,video_pin,source_pin):
    if receipt.get('schema')!='VIRALOS_SEMANTIC_FILM_REVIEW_V1' or receipt.get('locale')!=locale or receipt.get('publication_authorized') is not False or receipt.get('acoustic_alignment_verified') is not False or receipt.get('caption_basis')!='omitted_no_verified_alignment' or receipt.get('audio_payload_match') is not True or receipt.get('source_video_sha256')!=source_pin:raise ValueError('semantic receipt identity')
    audit=receipt['audit'];frames=receipt['frames'];rows=receipt['shots']
    if type(frames) is not int or not 720<=frames<=27000 or audit.get('frames')!=frames or audit.get('video_sha256')!=video_pin or audit.get('decode_pass') is not True or audit.get('numeric_audio_gate_pass') is not True or not isinstance(rows,list) or len(rows)!=24:raise ValueError('video receipt mismatch')
    cursor=0
    for i,x in enumerate(rows):
        n=x['samples']
        if type(n) is not int or not 48000<=n<=4320000:raise ValueError('sample count')
        f=(n+1599)//1600
        if (x['chapter'],x['beat'],x['start_frame'],x['end_frame'],x['padding_samples'])!=(f'{i//3+1:02}',i%3,cursor,cursor+f,f*1600-n):raise ValueError('shot continuity')
        cursor+=f
    if cursor!=frames:raise ValueError('frame count')
    return frames

def read_config(config,expected):
    c=s.read(config,expected)
    if set(c)!={'schema','locales','metadata'} or c['schema']!='VIRALOS_MEDIA_REVIEW_RUN_V1' or set(c['locales'])!=set(LANGS):raise ValueError('config schema')
    meta=obj(c['metadata'])
    if meta.get('schema')!='VIRALOS_PACKAGING_DRAFT_V2' or meta.get('publication_authorized') is not False or meta.get('human_review_required') is not True:raise ValueError('metadata schema')
    for l in LANGS:
        if set(c['locales'][l])!={'video','source','receipt','thumbnail'}:raise ValueError('locale inventory')
    return c,meta

def build_handoff(l,receipt,metadata,thumb_pin,scene,qc,packet,config_pin):
    m=metadata['english' if l=='en' else 'hindi'];source=metadata['english_video_sha256'] if l=='en' else m['video_sha256']
    if source!=receipt['source_video_sha256'] or metadata['thumbnail_sha256']['thumbnail_'+l+'.png']!=thumb_pin or len(m['chapters'])!=8:raise ValueError('inherited packaging mismatch')
    chapters=[]
    for i,ch in enumerate(m['chapters']):
        f=receipt['shots'][3*i]['start_frame']
        if ch['start_seconds']!=f//30 or not isinstance(ch['title'],str) or not ch['title'].strip():raise ValueError('chapter metadata mismatch')
        chapters.append(dict(title=ch['title'],start_frame=f,start_seconds=f//30))
    return dict(schema='VIRALOS_SEMANTIC_HANDOFF_V1',locale=l,config_sha256=config_pin,video_sha256=qc['audit']['video_sha256'],source_video_sha256=source,thumbnail_sha256=thumb_pin,title=m['title'],description=m['description'],chapters=chapters,frames=receipt['frames'],audio_packet_evidence=packet,freeze_fraction=scene['freeze_fraction'],unexpected_freeze_shots=scene['unexpected_freeze_shots'],review_flags=scene['original_review_flags'],caption_basis='omitted_no_verified_alignment',human_review_required=True,production_accepted=False,publication_authorized=False)

def run(config,expected,output,stage='all'):
    if stage not in ('stage','all'):raise ValueError('unknown stage')
    c,meta=read_config(config,expected);root=Path(output)
    if root.is_symlink():raise ValueError('unsafe output')
    root.mkdir(exist_ok=True);lock=root/'RUNNING'
    with lock.open('xb') as f:f.write(expected.encode('ascii'))
    try:
        exact(root/'run.json',s.encoded(dict(schema='VIRALOS_MEDIA_RUN_ID_V1',config_sha256=expected,publication_authorized=False)))
        def one(l):
            x=c['locales'][l];vp=pin(x['video']['sha256']);sp=pin(x['source']['sha256']);receipt=obj(x['receipt']);frames=validate_receipt(receipt,l,vp,sp)
            folder=root/l
            if folder.is_symlink():raise ValueError('unsafe locale folder')
            folder.mkdir(exist_ok=True)
            result={}
            for name,entry,limit in [('video.mp4',x['video'],LIMIT),('receipt.json',x['receipt'],2_000_000),('thumbnail.png',x['thumbnail'],2_000_000)]:result[name]=exact(folder/name,envelope(entry,limit))
            # Verify source even on resume. Do not copy private source into output.
            envelope(x['source']);a=packet_signature(x['source']['path']);b=packet_signature(folder/'video.mp4')
            if a!=b or q.audio_hash(folder/'video.mp4')!=receipt['audio_payload_sha256'] or q.audio_hash(x['source']['path'])!=receipt['audio_payload_sha256']:raise ValueError('audio packet or payload mismatch')
            envelope(x['source']);raw(folder/'video.mp4',vp)
            packet=dict(source=a,output=b,exact_packet_signature_match=True,acoustic_alignment_verified=False)
            result['packets.json']=exact(folder/'packets.json',s.encoded(packet))
            if stage=='stage':return l,result
            # Scan on each all-stage invocation, compare report bytes; no trust in cached QC alone.
            qc=q.scan(folder/'video.mp4',vp,frames);timeline=dict(video_sha256=vp,frames=frames,shots=receipt['shots'],publication_authorized=False)
            scene=r.variable(qc,timeline,['semantic_motion_expected']*24)
            result['qc.json']=exact(folder/'qc.json',s.encoded(qc));result['scene.json']=exact(folder/'scene.json',s.encoded(scene))
            handoff=build_handoff(l,receipt,meta,x['thumbnail']['sha256'],scene,qc,packet,expected)
            result['handoff.json']=exact(folder/'handoff.json',s.encoded(handoff));return l,result
        with ThreadPoolExecutor(max_workers=2) as pool:results=dict(pool.map(one,LANGS))
        return dict(schema='VIRALOS_MEDIA_RUN_RESULT_V1',config_sha256=expected,stage=stage,locales=results,production_accepted=False,publication_authorized=False)
    finally:lock.unlink()

def recover(config,expected,source,output):
    """Re-stage pinned media in a fresh folder without clearing interrupted locks."""
    old=Path(source);new=Path(output)
    if old.is_symlink() or not old.is_dir() or new.exists() or new.is_symlink() or new.resolve().is_relative_to(old.resolve()) or old.resolve().is_relative_to(new.resolve()):raise ValueError('separate fresh folder required')
    identity=s.encoded(dict(schema='VIRALOS_MEDIA_RUN_ID_V1',config_sha256=expected,publication_authorized=False))
    if raw(old/'run.json',limit=4096)!=identity:raise ValueError('interrupted run identity')
    lock=old/'RUNNING'
    if lock.is_symlink() or (lock.exists() and raw(lock,limit=64)!=expected.encode('ascii')):raise ValueError('interrupted lock identity')
    result=run(config,expected,new,'stage');report={}
    for l in LANGS:
        if (old/l).is_symlink():raise ValueError('unsafe source locale')
        for n in ('video.mp4','receipt.json','thumbnail.png','packets.json'):
            p=old/l/n;fresh=new/l/n
            if p.is_symlink() or (p.exists() and not p.is_file()):raise ValueError('unsafe source artifact')
            state='missing' if not p.exists() else 'exact' if p.stat().st_size==fresh.stat().st_size and raw(p)==raw(fresh) else 'mismatch'
            report[l+'/'+n]=dict(prior_state=state,restaged_sha256=s.sha(raw(fresh)))
    result.update(recovery=report,old_run_modified=False,human_review_required=True)
    write_new(new/'recovery.json',s.encoded(result));return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('config','expected','output'):p.add_argument('--'+k,required=True)
    p.add_argument('--stage',choices=('stage','all'),default='all');p.add_argument('--recover-from');a=vars(p.parse_args());old=a.pop('recover_from');
    if old is not None:a.pop('stage');report=recover(source=old,**a)
    else:report=run(**a)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
