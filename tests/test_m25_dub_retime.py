"""Scene retiming is based on owner-confirmed cues, not fabricated word timing."""
import copy
import pytest
from app.m25_dub_retime import retime_reviewed_plan
from app.studio_contracts import StudioPlanIn


def original():
    return {
        'locale':'en-IN','locale_reviewed':True,'captions_provenance':'OWNER_TIMED',
        'shots':[
            {'role':'HOOK','duration_ms':1800,'headline':'Original voice introduction',
             'visual':{'kind':'ORIGINAL_DIAGRAM'},'overlays':[{'text':'First','start_ms':200,'end_ms':900,'anchor':'TOP'}]},
            {'role':'PAYOFF','duration_ms':1800,'headline':'Original factual conclusion',
             'visual':{'kind':'ORIGINAL_DIAGRAM'},'overlays':[]}],
        'captions':[{'start_ms':0,'end_ms':1580,'text':'Original voice introduction'},
                    {'start_ms':1600,'end_ms':3780,'text':'Original factual conclusion'}]}


def test_actual_voice_cues_change_scene_lengths_but_never_caption_times():
    source=original();copy_before=copy.deepcopy(source)
    retimed,report=retime_reviewed_plan(source,[1600,3800],3800)
    assert source==copy_before
    assert [s['duration_ms'] for s in retimed['shots']]==[1600,2200]
    assert retimed['shots'][0]['overlays'][0]['start_ms']==177
    assert retimed['captions']==source['captions']
    assert report['caption_timestamps_guessed'] is False
    StudioPlanIn.model_validate(retimed)


def test_untimed_or_crossed_caption_refused():
    p=original()
    p['captions'][0]['end_ms']=1700
    with pytest.raises(ValueError,match='crosses'):
        retime_reviewed_plan(p,[1600,3800],3800)
    p=original();p['captions_provenance']='NOT_PROVIDED'
    with pytest.raises(ValueError,match='Owner-timed'):
        retime_reviewed_plan(p,[1600,3800],3800)


@pytest.mark.parametrize('cues,actual,problem',[
    ([1600,3000],3800,'disagrees'),
    ([1200,1100],1100,'outside'),
    ([1100,2800],2800,'outside'),
    ([3000,3800],3800,'outside'),
    ([1600,3800.0],3800,'integer'),
    ([1600,3800],95000,'cap'),
])
def test_unsafe_timing_is_blocked(cues,actual,problem):
    with pytest.raises(ValueError,match=problem):
        retime_reviewed_plan(original(),cues,actual)


def test_incorrect_overlays_and_excess_stretch_refused():
    p=original();p['shots'][0]['overlays'][0]['end_ms']=9999
    with pytest.raises(ValueError,match='overlay'):
        retime_reviewed_plan(p,[1600,3800],3800)
    p=original();p['shots'][0]['duration_ms']=1200
    with pytest.raises(ValueError,match='Severe'):
        retime_reviewed_plan(p,[3100,4600],4600)
