"""Noncausal, scene-aware retention mapping for explicitly supplied observations.

No external YouTube Analytics API is called and no observation is invented.
An "AUTHORIZED_API" label in caller-supplied JSON is only a *claim* of source,
not a verified OAuth receipt. No income or virality predictions are made.
"""
from __future__ import annotations
from statistics import mean
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class SceneRange(Strict):
    scene_id: str=Field(min_length=1,max_length=100)
    start_ms: int=Field(ge=0)
    end_ms: int=Field(ge=1)

class RetentionPoint(Strict):
    at_ms: int=Field(ge=0)
    audience_watch_ratio: float=Field(ge=0,le=5,allow_inf_nan=False)

class RetentionInput(Strict):
    video_duration_ms: int=Field(ge=1000,le=21_600_000)
    views_observed: int=Field(ge=0,le=2_000_000_000)
    source_label: Literal['OWNER_ENTERED_NOT_VERIFIED','AUTHORIZED_API_AS_DECLARED_BY_OWNER']
    scenes: list[SceneRange]=Field(min_length=1,max_length=120)
    observations: list[RetentionPoint]=Field(min_length=2,max_length=1000)


def audit_retention(b:RetentionInput)->dict:
    scenes=b.scenes;points=b.observations
    ids=[s.scene_id for s in scenes]
    if len(ids)!=len(set(ids)):
        raise ValueError('Scene IDs must be unique')
    if any(s.start_ms>=s.end_ms or s.end_ms>b.video_duration_ms for s in scenes):
        raise ValueError('Invalid scene boundaries')
    sorted_scenes=sorted(scenes,key=lambda s:s.start_ms)
    if any(a.end_ms>b.start_ms for a,b in zip(sorted_scenes,sorted_scenes[1:])):
        raise ValueError('Scene ranges must not overlap')
    times=[p.at_ms for p in points]
    if times!=sorted(set(times)) or any(t>b.video_duration_ms for t in times):
        raise ValueError('Retention observation timestamps must be ordered, unique, within video duration')
    output=[]
    for scene in sorted_scenes:
        sample=[point.audience_watch_ratio for point in points if scene.start_ms<=point.at_ms<scene.end_ms]
        if not sample:
            output.append({'scene_id':scene.scene_id,'status':'NO_SAMPLES_FOR_SCENE','mean_audience_watch_ratio':None})
            continue
        output.append({'scene_id':scene.scene_id,'status':'OBSERVED_NOT_CAUSAL',
                       'mean_audience_watch_ratio':round(mean(sample),5),'observation_count':len(sample),
                       'relative_change_first_to_last':round(sample[-1]-sample[0],5) if len(sample)>1 else None})
    adequate=b.views_observed>=1000 and all(r.get('observation_count',0)>=2 for r in output)
    return {'status':'OBSERVATIONAL_SCENE_MAP','scenes':output,
            'views_observed_as_declared':b.views_observed,'source_label_unverified':b.source_label,
            'sufficient_for_causal_inference':False,'sample_size_warning':not adequate,
            'authentic_youtube_data_verified_by_this_endpoint':False,
            'hypothesis_testing_requires_controlled_experiment':True,
            'recommendations_published_automatically':False,'revenue_forecast_generated':False}


def register_audience_scene_audit(app):
    @app.post('/api/audience/retention/scene-map')
    def scene_map(payload:RetentionInput):
        try:return audit_retention(payload)
        except ValueError as e:raise HTTPException(422,str(e)) from e
