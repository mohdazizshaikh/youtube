import pytest
from fastapi.testclient import TestClient
from app.audience_scene_audit import RetentionInput,audit_retention
from app.main import app


def payload():
    return {'video_duration_ms':60000,'views_observed':80,'source_label':'OWNER_ENTERED_NOT_VERIFIED',
            'scenes':[{'scene_id':'hook','start_ms':0,'end_ms':30000},
                      {'scene_id':'payoff','start_ms':30000,'end_ms':60000}],
            'observations':[{'at_ms':0,'audience_watch_ratio':1.1}, {'at_ms':5000,'audience_watch_ratio':1.0},
                            {'at_ms':30000,'audience_watch_ratio':0.7}, {'at_ms':58000,'audience_watch_ratio':0.68}]}

def test_scene_mapping_reports_observation_not_causation():
    r=audit_retention(RetentionInput(**payload()))
    assert r['scenes'][0]['mean_audience_watch_ratio']==1.05
    assert r['scenes'][1]['mean_audience_watch_ratio']==0.69
    assert r['sample_size_warning']
    assert r['sufficient_for_causal_inference'] is False
    assert r['authentic_youtube_data_verified_by_this_endpoint'] is False

def test_bad_time_overlap_nans_and_unknown_youtube_claims_fail():
    base=payload()
    with pytest.raises(ValueError,match='overlap'):
        audit_retention(RetentionInput(**{**base,'scenes':[{'scene_id':'x','start_ms':0,'end_ms':40000},
                                                       {'scene_id':'y','start_ms':30000,'end_ms':60000}]}))
    with pytest.raises(ValueError,match='ordered'):
        audit_retention(RetentionInput(**{**base,'observations':list(reversed(base['observations']))}))
    with TestClient(app) as c:
        x=c.post('/api/audience/retention/scene-map',json=base)
        assert x.status_code==200
        assert not x.json()['revenue_forecast_generated']
        assert c.post('/api/audience/retention/scene-map',json={**base,'source_label':'verified magically'}).status_code==422
