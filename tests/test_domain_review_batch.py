import hashlib,json
import pytest
from app.domain_adapters import POLICIES
from tools.domain_review_batch import prepare


def make_index(root):
    records=[]
    for d in POLICIES:
        for f in ('short','long'):
            name=f'{d}_{f}';(root/name).mkdir();records.append({'folder':name,'manifest_sha256':'a'*64,'video_sha256':'b'*64})
    return {'synthetic_demo':True,'records':records}


def write(root,index):
    raw=json.dumps(index).encode();(root/'index.json').write_bytes(raw);return hashlib.sha256(raw).hexdigest()


def fake(draft,assets,pin):
    domain,fmt=draft.parent.name.rsplit('_',1)
    return {'domain':domain,'format':fmt.upper(),'video_sha256':'b'*64,'manifest_sha256':pin,'synthetic_demo':True,'scenes':[]}


def test_batch(tmp_path,monkeypatch):
    import tools.domain_review_batch as m
    monkeypatch.setattr(m,'review_packet',fake)
    root=tmp_path/'in';root.mkdir();pin=write(root,make_index(root));out=tmp_path/'out'
    result=prepare(root,pin,out)
    assert result['packets_created']==24 and result['human_reviews_completed']==0 and not result['publication_eligible']
    assert len(list(out.glob('*.json')))==25
    with pytest.raises(FileExistsError):prepare(root,pin,out)


@pytest.mark.parametrize('case',['pin','duplicate','traversal','mismatch','nested'])
def test_batch_fail_closed(tmp_path,monkeypatch,case):
    import tools.domain_review_batch as m
    monkeypatch.setattr(m,'review_packet',fake)
    root=tmp_path/'in';root.mkdir();index=make_index(root)
    if case=='duplicate':index['records'][1]=index['records'][0]
    if case=='traversal':index['records'][0]['folder']='../unsafe'
    if case=='mismatch':index['records'][0]['video_sha256']='c'*64
    pin=write(root,index);out=tmp_path/'out'
    if case=='nested':out=root/'out'
    if case=='pin':pin='0'*64
    with pytest.raises(ValueError):prepare(root,pin,out)
    assert not out.exists()


def test_declared_real_review_never_grants_publish(monkeypatch):
    from app import domain_draft_review as m
    packet={'manifest_sha256':'a'*64,'video_sha256':'b'*64,'domain':'sports','format':'SHORT','synthetic_demo':False,
            'scenes':[{'scene':1,'scene_sha256':'c'*64},{'scene':2,'scene_sha256':'d'*64}]}
    monkeypatch.setattr(m,'review_packet',lambda *args:packet)
    review=m.template(packet);review['reviewer']='Synthetic test fixture reviewer'
    for s in review['scenes']:s['checks']=dict.fromkeys(m.CHECKS,'PASS')
    result=m.evaluate(None,None,'a'*64,review)
    assert result['self_attested_editorial_checklist_complete']
    assert not result['publication_eligible'] and not result['reviewer_identity_verified'] and not result['rights_legally_certified']
