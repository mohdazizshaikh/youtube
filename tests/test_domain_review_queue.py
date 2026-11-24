import copy
import json
import sqlite3
import pytest
from app import domain_review_queue as q
from app import domain_draft_review as r


@pytest.fixture
def queue(tmp_path,monkeypatch):
    packet={'manifest_sha256':'a'*64,'video_sha256':'b'*64,'domain':'sports','format':'SHORT','synthetic_demo':False,
            'scenes':[{'scene':1,'scene_sha256':'c'*64},{'scene':2,'scene_sha256':'d'*64}]}
    monkeypatch.setattr(q,'review_packet',lambda *args:packet)
    monkeypatch.setattr(r,'review_packet',lambda *args:packet)
    db=tmp_path/'queue.sqlite';q.initialize(db)
    return db,packet


def review(packet):
    result=r.template(packet);result['reviewer']='private reviewer'
    for s in result['scenes']:s['checks']=dict.fromkeys(r.CHECKS,'PASS')
    return result


def register(db,p):return q.register(db,None,None,p['manifest_sha256'])
def submit(db,p,rev,body):return q.submit(db,None,None,p['manifest_sha256'],rev,body)


def test_durable_revision_and_privacy(queue):
    db,p=queue;register(db,p);assert register(db,p)['revision']==0
    body=review(p);body['scenes'][0]['checks']['asset_rights']='REVISE';body['scenes'][0]['notes']='private note'
    assert submit(db,p,0,body)['state']=='NEEDS_REVISION'
    body=review(p);assert submit(db,p,1,body)['state']=='SELF_ATTESTED'
    result=q.status(db)
    assert result['counts']['SELF_ATTESTED']==1 and len(result['history'])==2
    assert not result['publication_eligible'] and not result['reviewer_identity_verified']
    assert 'private reviewer' not in json.dumps(result) and b'private note' not in db.read_bytes()


def test_demo_never_passes(queue):
    db,p=queue;p['synthetic_demo']=True;register(db,p)
    assert submit(db,p,0,review(p))['state']=='DEMO_BLOCKED'
    assert q.status(db)['counts']['SELF_ATTESTED']==0


def test_stale_revision_and_replay(queue):
    db,p=queue;register(db,p);body=review(p);submit(db,p,0,body)
    with pytest.raises(ValueError,match='stale'):submit(db,p,0,body)
    with pytest.raises(ValueError,match='already'):submit(db,p,1,body)
    assert len(q.status(db)['history'])==1


def test_incomplete(queue):
    db,p=queue;register(db,p);out=submit(db,p,0,r.template(p))
    assert out['state']=='INCOMPLETE' and out['blocker_count']>0


def test_register_changed_packet(queue):
    db,p=queue;register(db,p);p['video_sha256']='e'*64
    with pytest.raises(ValueError,match='identity'):register(db,p)
    with pytest.raises(ValueError,match='mismatch'):submit(db,p,0,review(p))
    assert not q.status(db)['history']


def test_wrong_db_and_exclusive_init(tmp_path):
    p=tmp_path/'foreign.sqlite'
    with sqlite3.connect(p) as db: db.execute('CREATE TABLE foreign_data(x)')
    before=p.read_bytes()
    with pytest.raises(FileExistsError):q.initialize(p)
    with pytest.raises(ValueError,match='not a supported'):q.status(p)
    assert p.read_bytes()==before


@pytest.mark.parametrize('rev',[True,-1,'0'])
def test_bad_revision(queue,rev):
    db,p=queue;register(db,p)
    with pytest.raises(ValueError,match='integer'):submit(db,p,rev,review(p))


def test_unregistered(queue):
    db,p=queue
    with pytest.raises(ValueError,match='not registered'):submit(db,p,0,review(p))
    assert q.status(db)['draft_count']==0


def test_invalid_pin(queue):
    db,p=queue
    with pytest.raises(ValueError,match='SHA-256'):q.register(db,None,None,'bad')


def test_simultaneous_submissions(queue):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    db,p=queue;register(db,p);barrier=Barrier(2)
    def run(i):
        body=review(p);body['reviewer']=f'fixture {i}'
        barrier.wait(timeout=5)
        try:return submit(db,p,0,body)['state']
        except ValueError as e:return str(e)
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(run,range(2)))
    assert results.count('SELF_ATTESTED')==1
    assert sum('stale queue revision' in x for x in results)==1
    assert len(q.status(db)['history'])==1


def test_real_media_reaudit(tmp_path):
    import shutil
    from app.domain_draft_video import DraftPlan, compose, digest
    from test_domain_draft_video import sample
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('local FFmpeg required')
    assets=tmp_path/'assets';assets.mkdir();draft=tmp_path/'draft'
    compose(DraftPlan.model_validate(sample(assets)),assets,draft)
    pin=digest((draft/'manifest.json').read_bytes())
    packet=r.review_packet(draft,assets,pin)
    db=tmp_path/'ledger.sqlite';q.initialize(db);q.register(db,draft,assets,pin)
    assert q.submit(db,draft,assets,pin,0,review(packet))['state']=='DEMO_BLOCKED'
    (draft/'captions.vtt').write_text('tampered',encoding='utf8')
    with pytest.raises(ValueError,match='file hash mismatch'):
        q.submit(db,draft,assets,pin,1,r.template(packet))
    assert q.status(db)['drafts'][0]['revision']==1
