import copy,json
from pathlib import Path
import pytest
try:
    from tools import phase14_film as f
except ImportError:
    import phase14_film as f

@pytest.fixture
def plan():
    return json.loads(Path(f.__file__).with_name('phase14_film_plan.json').read_text(encoding='utf-8'))

def test_plan(plan):
    assert f.validate(plan)==932
    assert len(plan['scenes'])==8

def test_experiment():
    assert len(f.BITS)==256 and sum(f.BITS)==125
    assert f.DIGESTS[0]=='2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'

def test_stamp():
    assert f.stamp(372345)=='00:06:12.345'

@pytest.mark.parametrize('mutate', [
    lambda p:p.update(status='APPROVED'),
    lambda p:p.update(locale='hi-IN'),
    lambda p:p['scenes'][0].update(sources=['missing']),
    lambda p:p['scenes'][0].update(id='02'),
    lambda p:p['scenes'][0].update(beats=['one']),
    lambda p:p['scenes'][0].update(narration='too short'),
    lambda p:p['sources'].update(nist='file:///private'),
    lambda p:p['scenes'][0].update(layout='unrecognized'),
])
def test_reject(plan,mutate):
    mutate(plan)
    with pytest.raises(ValueError):f.validate(plan)

def test_no_overwrite(tmp_path,plan):
    path=tmp_path/'plan.json';path.write_text(json.dumps(plan),encoding='utf-8')
    dest=tmp_path/'existing';dest.mkdir(); sentinel=dest/'sentinel';sentinel.write_text('preserve')
    with pytest.raises(FileExistsError):f.prepare(path,dest,Path('missing.ttf'))
    assert sentinel.read_text()=='preserve'
