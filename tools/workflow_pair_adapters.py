"""Read-only typed audits for stopped original and mastered bilingual pairs.

Original pair audit is a technical child/media/inventory audit, not independent
recomposition from original narration/board requests. Mastered audit additionally
reruns its original-parent-bound mastering verifier. No publication authority.
"""
from tools import bilingual_review_dashboard as dash, paired_mastered_pilot as pm
from tools import pilot_snapshot as ps,pilot_run_verify as pv
from tools.narration_prepare import sha,pinned
from tools.narration_qc import private_file


def audit(source,job):
    arg=job["input"]
    pair=ps.local_dir(source/arg["run"])
    pin=arg["pair_sha256"]
    runs,duration=dash.select_runs(pair,pin)
    before=dash.snapshot(runs,duration,fresh=True)
    pv.require(before["fresh_media_audit"] is True and before["publication_eligible"] is False,
               "PAIR_MEDIA_AUDIT")
    inventories={l:ps.inventory(ps.local_dir(run[0])) for l,run in runs.items()}
    pv.require(all(inventories[l]["draft/manifest.json"]["sha256"]==run[1] and
                   inventories[l]["draft/draft.mp4"]["sha256"]==run[2] for l,run in runs.items()),
               "PAIR_INVENTORY_BINDING")
    pv.require(dash.select_runs(pair,pin)==(runs,duration) and
               dash.snapshot(runs,duration)=={**before,"fresh_media_audit":False} and
               all(ps.inventory(run[0])==inventories[l] for l,run in runs.items()),
               "PAIR_CHANGED")
    return {"run":arg["run"],"pair_sha256":pin,"duration_ms":duration,
            "languages":{l:{"manifest_sha256":run[1],"video_sha256":run[2],
                       "inventory_sha256":pv.canonical(inventories[l]),
                       "revision":before["languages"][l]["revision"],
                       "state":before["languages"][l]["state"],
                       "synthetic_demo":before["languages"][l]["synthetic_demo"]} for l,run in runs.items()},
            "fresh_media_audit":True,"original_input_recomposition_verified":False,
            "publication_eligible":False}


def mastered(source,job,parent):
    arg=job["input"]
    pair=ps.local_dir(source/parent["run"])
    child=ps.local_dir(source/arg["run"])
    pv.require(pair!=child,"MASTERED_PARENT_OVERLAP")
    req=private_file(source/arg["request"],pm.MAX_REQUEST)
    pin=arg["request_sha256"]
    pinned(req,pin,pm.MAX_REQUEST)
    candidate=arg["mastered_pair_sha256"]
    # Confirm the precise parent inventory including queue state before and
    # after expensive mastering verification.
    parent_job={"input":{"run":parent["run"],"pair_sha256":parent["pair_sha256"]}}
    pv.require(audit(source,parent_job)==parent,"MASTERED_PARENT_CHANGED")
    checked=pm.verify(pair,parent["pair_sha256"],req,pin,child,candidate)
    pv.require(checked["fresh_media_audit"] is True and checked["publication_eligible"] is False
               and checked["mastered_pair_sha256"]==candidate and
               checked["duration_ms"]==parent["duration_ms"],"MASTERED_MEDIA_AUDIT")
    receipt=pv.decode(pinned(pv.read(child/"mastered_pair.json",pv.MAX_JSON),candidate,pv.MAX_JSON))
    inventories={}
    for lang,row in receipt["runs"].items():
        run=ps.local_dir(child/lang)
        records=ps.inventory(run)
        state=pv.verify(run,row["manifest_sha256"])
        pv.require(records["draft/manifest.json"]["sha256"]==row["manifest_sha256"] and
                   records["draft/draft.mp4"]["sha256"]==row["video_sha256"] and
                   checked["review_states"][lang]=={"revision":state["queue_revision"],
                       "state":state["queue_state"]},"MASTERED_INVENTORY_BINDING")
        inventories[lang]=records
    pv.require(set(inventories)==set(pm.LANGS),"MASTERED_LANGUAGES")
    audio_pin=pv.file_hash(child/"pair_dynamics.json",pv.MAX_JSON)
    pv.require(audio_pin==receipt["audio_bundle_sha256"] and
               pv.file_hash(child/"mastered_pair.json",pv.MAX_JSON)==candidate and
               sha(private_file(source/arg["request"],pm.MAX_REQUEST))==pin and
               all(ps.inventory(child/l)==v for l,v in inventories.items()) and
               audit(source,parent_job)==parent,"MASTERED_CHANGED")
    return {"run":arg["run"],"parent_pair_sha256":parent["pair_sha256"],
            "mastered_pair_sha256":candidate,"request_sha256":pin,"duration_ms":checked["duration_ms"],
            "audio_bundle_sha256":audio_pin,"review_states":checked["review_states"],
            "inventory_sha256":{l:pv.canonical(v) for l,v in inventories.items()},
            "fresh_media_audit":True,"parent_bound_mastering_recomposition_verified":True,
            "publication_eligible":False}
