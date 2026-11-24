import copy
import json
import wave
import pytest
try:
    from tools import phase14_motion as m
except ImportError:
    import phase14_motion as m


@pytest.fixture
def inputs(tmp_path):
    s=tmp_path/'script.txt';s.write_text('one two three four five six',encoding='utf-8'); assets=tmp_path/'assets';assets.mkdir();shots=[]
    for i,visual in enumerate(m.VISUALS):
        w=assets/f'{i}.wav'
        with wave.open(str(w),'wb') as f:
            f.setparams((1,2,48000,0,'NONE','not compressed'));f.writeframes(b'\x01\x00'*48001)
        shots.append(dict(visual=visual,word_start=i*2,word_end=i*2+2,text=' '.join(s.read_text().split()[i*2:i*2+2]),wav=w.name,wav_sha256=m.sha(w)))
    return s,assets,dict(schema=1,locale='en-US',basis='synthetic_fixture',script_sha256=m.sha(s),shots=shots)


def test_frame_padding(inputs):
    r=m.validate(*inputs)
    assert [x['start_frame'] for x in r]==[0,31,62]
    assert [x['end_frame'] for x in r]==[31,62,93]
    assert all(x['padding_samples']==1599 for x in r)


@pytest.mark.parametrize('mutation',[
    lambda x:x.update(locale='fr-FR'),
    lambda x:x.update(script_sha256='bad'),
    lambda x:x.update(basis='owner_reviewed_recording'),
    lambda x:x['shots'][0].update(wav='../0.wav'),
    lambda x:x['shots'][0].update(wav_sha256='bad'),
    lambda x:x['shots'][0].update(word_start=True),
    lambda x:x['shots'][1].update(word_start=1),
    lambda x:x['shots'][2].update(word_end=5),
    lambda x:x['shots'][1].update(text='wrong'),
    lambda x:x['shots'][0].update(visual='other'),
    lambda x:x['shots'][1].update(wav=x['shots'][0]['wav']),
])
def test_reject_bad_manifest(inputs,mutation):
    s,a,x=inputs;mutation(x)
    with pytest.raises(ValueError):m.validate(s,a,x)


def test_hindi_contract(inputs):
    s,a,x=inputs;s.write_text('एक दो तीन चार पाँच छह',encoding='utf-8');x.update(locale='hi-IN',basis='owner_reviewed_local_tts',rights_attested=True,listening_attested=True,rights_reference='local license record',script_sha256=m.sha(s));tokens=s.read_text().split()
    for i,shot in enumerate(x['shots']):shot['text']=' '.join(tokens[2*i:2*i+2])
    assert len(m.validate(s,a,x))==3  # contract only; fixture is not actual speech


def test_no_overwrite(inputs,tmp_path):
    s,a,x=inputs;manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(x));out=tmp_path/'existing';out.mkdir();sentinel=out/'keep';sentinel.write_text('keep')
    with pytest.raises(FileExistsError):m.render(s,a,manifest,out,'unused')
    assert sentinel.read_text()=='keep'
