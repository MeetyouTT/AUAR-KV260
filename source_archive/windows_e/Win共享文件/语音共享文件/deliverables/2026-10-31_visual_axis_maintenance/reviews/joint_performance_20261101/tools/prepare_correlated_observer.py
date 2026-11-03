"""Keep first-request correlation when the UI clears its current slot before publishing ACK."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
BASE=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/live_observer_remote.py'

def completed_target(observed,target,metrics):
    current=observed.get('request_token');latency=observed.get('latency',{})
    return bool(target and observed.get('ack_committed') is True
                and observed.get('ack_request_token')==target and latency.get('complete') is True
                and observed.get('playing') is False
                and (current==target or current is None and metrics is not None and latency==metrics))

def main():
    before=BASE.read_text('utf-8');assert hashlib.sha256(before.encode()).hexdigest()=='49fdf19b66b4e4319b7f5794f2dbf67fb24ef2191aa99c78588a5798e77ee805'
    old="initial_request=None;first=True;ready=False;completed=set();last_probe=None"
    new=old+';target_request=None;target_complete_latency=None'
    assert before.count(old)==1;after=before.replace(old,new,1)
    old=" token=observed['request_token']\n if (ready and token and token!=initial_request and observed['ack_committed']\n     and observed['ack_matches_current_request'] and observed['latency'].get('complete') is True):\n  completed.add(token)\n  print(json.dumps(dict(kind='complete',status='ONE_NEW_TURN_COMPLETE',request_token=token,"
    new=""" token=observed['request_token']
 if ready and target_request is None and token and token!=initial_request:
  target_request=token
 if token==target_request and observed['latency'].get('complete') is True:
  target_complete_latency=dict(observed['latency'])
 if (ready and target_request and observed['ack_committed']
     and observed['ack_request_token']==target_request and observed['latency'].get('complete') is True
     and observed['playing'] is False
     and (token==target_request or token is None and target_complete_latency is not None
          and observed['latency']==target_complete_latency)):
  completed.add(target_request)
  print(json.dumps(dict(kind='complete',status='ONE_NEW_TURN_COMPLETE',request_token=target_request,"""
    assert after.count(old)==1;after=after.replace(old,new,1)
    target=HERE/'remote/live_observer_correlated.py'
    with target.open('x',encoding='utf-8',newline='\n') as f:f.write(after)
    good=dict(request_token=None,ack_request_token='public-target',ack_committed=True,playing=False,latency=dict(complete=True,asr_ms=717.8))
    cases=[completed_target(good,'public-target',good['latency']),
           not completed_target(dict(good,ack_request_token='other'),'public-target',good['latency']),
           not completed_target(dict(good,request_token='other'),'public-target',good['latency']),
           not completed_target(dict(good,playing=True),'public-target',good['latency']),
           not completed_target(good,'public-target',None),
           not completed_target(good,'public-target',dict(complete=True,asr_ms=1)),
           completed_target(dict(good,request_token='public-target'),'public-target',None)]
    assert all(cases)
    folder=HERE/'evidence/live_trial_1793534789636233900';rows=[json.loads(x) for x in (folder/'metadata.jsonl').read_text('utf-8').splitlines() if x.strip()]
    samples=[r for r in rows if r.get('kind')=='sample'];initial=samples[0].get('request_token')
    target_token=next(r['request_token'] for r in samples if r.get('request_token') and r['request_token']!=initial)
    latency=None;matched=None
    for row in samples:
        if row.get('request_token')==target_token and row.get('latency',{}).get('complete') is True:latency=dict(row['latency'])
        if completed_target(row,target_token,latency):matched=row;break
    assert matched
    proof=dict(schema='aura-observer-first-target-ack-correlation-1',base_sha256=hashlib.sha256(before.encode()).hexdigest(),
               source_sha256=hashlib.sha256(after.encode()).hexdigest(),source_path=str(target),public_cases_passed=len(cases),
               real_metadata_replay_first_target=target_token,matched_ack_observed_mono=matched['observed_mono'],
               matched_current_request_slot=matched['request_token'],exact_complete_latency_equal=True,
               matched_latency=matched['latency'],matched_prepare_latency=matched['prepare_latency'],
               request_match_weakened=False,raw_text_or_devices_accessed=False,
               scope='Only first newly observed request; a cleared slot requires identical completed metrics observed while that same request was current.')
    out=HERE/'evidence/correlated_observer_public_and_saved_metadata_check.json'
    with out.open('x',encoding='utf-8') as f:json.dump(proof,f,indent=2);f.write('\n')
    print(json.dumps(proof))

if __name__=='__main__':main()
