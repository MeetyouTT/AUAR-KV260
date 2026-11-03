"""Seal current metadata without inventing a link to later human submissions."""
import copy
import json
from pathlib import Path
import update_core as u

HERE=u.HERE; R=u.REPAIR


def current_only(raw,name,replace):
    start=('<!-- '+name+' -->').encode();end=('<!-- /'+name+' -->').encode()
    if raw.count(start)!=1 or raw.count(end)!=1:raise ValueError('current_marker_changed')
    left=raw.index(start);right=raw.index(end,left)+len(end)
    body=raw[left:right]
    for old,new in replace:body=body.replace(old.encode('utf-8'),new.encode('utf-8'))
    return raw[:left]+body+raw[right:]


def main():
    observation_path=R/'current_observation_v15.json'
    original=observation_path.read_bytes(); observation=json.loads(original)
    if observation['startup_sha256']!=u.STARTUP:raise ValueError('unexpected_current_revision')
    old_sha=u.sha(original)
    inputs={
        'observation':observation_path,'status':R/'STATUS.json','implementation':u.OWNER/'IMPLEMENTATION_STATE.json',
        'agents':u.PROJECT/'AGENTS.md','analysis_index':u.ANALYSIS/'README.md',
        'owner_note':u.OWNER/'板端业务正式接管与实测接续_20261030.txt',
        'note':R/'idle_cpu_integration/v15_current_note.txt',
        'analysis_note':u.ANALYSIS/'板端空闲CPU减负与v15当前观测_20261031.txt'}
    raw={name:path.read_bytes() for name,path in inputs.items()}
    archives={name:u.exact_archive(HERE/'before_seal'/path.name,raw[name]) for name,path in inputs.items()}
    #Names may overlap only if contents are identical (the two public notes).
    feedback=observation['user_feedback']
    feedback['precise_turn_timing_association']='not_obtained; later submissions/recording continued, no reliable match to the user feedback'
    feedback['human_feedback_turn_stage_timings_available']=False
    observation['documentation_sealed_without_waiting_for_more_human_sampling']=True
    observation['later_activity_note']='Root saw later submissions3/4; their timing/recording duration/oldACK must not be assigned to the original continuity feedback.'
    observation['future_candidate_notice']='Any later online Paraformer work is isolated candidate work, outside v15 measured/deployed claims.'
    followup=R/'v15_feedback_followup.json'
    if followup.exists():
        followup_raw=followup.read_bytes()
        observation['evidence']['later_feedback_followup_unlinked']=u.exact_archive(HERE/'evidence/feedback_followup_unlinked.json',followup_raw)
    output=u.encoded(observation);new_sha=u.sha(output)
    def replace_ref(value):
        if isinstance(value,dict):
            if (value.get('revision')=='v15' and isinstance(value.get('path'),str)
                    and value['path'].endswith('current_observation_v15.json')):
                if value.get('sha256')!=old_sha:raise ValueError('current_reference_changed')
                value['sha256']=new_sha
            for item in value.values():replace_ref(item)
        elif isinstance(value,list):
            for item in value:replace_ref(item)
    status=json.loads(raw['status']);implementation=json.loads(raw['implementation'])
    for value in (status,implementation):replace_ref(value)
    status['latest_human_feedback']=copy.deepcopy(feedback)
    status['audio_continuity_user_confirmed']=True;status['waiting_improvement']=False
    status['feedback_turn_timing_association']='not_obtained'
    status['verification_scope_notice']='v15 continuous/control/priority passed. User confirms continuous sound; waiting not improved. Exact feedback-round timing not obtained; no later stage duration or oldACK assigned. Audible-first-sound and multi-hour acceptance remain unverified.'
    implementation['verification_scope_notice']=status['verification_scope_notice']
    implementation['response_latency']['feedback_turn_timing_association']='not_obtained'
    implementation['production']['audio_played']=True
    implementation['production']['audio_played_evidence_scope']='Root-relayed v15 user continuity feedback; not a matched stage-timing/complete instrumented acceptance.'
    outputs={'observation':output,'status':u.encoded(status),'implementation':u.encoded(implementation)}
    changes=[('具体真人轮次/阶段计时关联待核','该次真人反馈的精确轮次耗时未取得可靠关联'),
             ('接续以integration/dialogue_repair/current_observation_v15.json和idle_cpu_integration/v15_current_note.txt为准',
              '接续按语音项目根目录相对路径deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v15.json及idle_cpu_integration/v15_current_note.txt读取')]
    outputs['agents']=current_only(raw['agents'],'board-business-live-20261030',changes)
    outputs['analysis_index']=current_only(raw['analysis_index'],'board-business-live-20261030',changes)
    #Only this newv15 prefix changes; the following completev14 original stays exact.
    marker='以下完整原文为v14及更早历史'.encode('utf-8')
    boundary=raw['owner_note'].index(marker)
    prefix=raw['owner_note'][:boundary]
    for old,new in changes:prefix=prefix.replace(old.encode('utf-8'),new.encode('utf-8'))
    outputs['owner_note']=prefix+raw['owner_note'][boundary:]
    for name in ('note','analysis_note'):
        text=raw[name]
        for old,new in changes:text=text.replace(old.encode('utf-8'),new.encode('utf-8'))
        text=text.replace(old_sha.encode(),new_sha.encode())
        text+=('\n该次用户反馈的精确轮次耗时未取得可靠关联，按当前证据封档；后续第3/4次提交、持续更新的录音时长和旧ACK均不归于它。后续online Paraformer仍只是独立候选，不属于v15已测/已部署。\n').encode('utf-8')
        outputs[name]=text
    for name,path in inputs.items():
        if path.read_bytes()!=raw[name]:raise ValueError('document_changed_concurrently')
    for name,path in inputs.items():u.atomic(path,outputs[name])
    receipt=dict(status='V15_CORE_DOCUMENTATION_SEALED_NO_TIMING_ATTRIBUTION',
        observation=u.record(observation_path),files={name:u.record(path) for name,path in inputs.items()},
        before_seal=archives,audio_continuity_user_confirmed=True,waiting_improvement=False,
        feedback_turn_link_pending=False,exact_feedback_turn_timing_obtained=False,
        owner_acceptance_modified=False,production_source_or_hardware_or_private_db_actions=[])
    u.atomic(HERE/'sealed_receipt.json',u.encoded(receipt))
    print(json.dumps(dict(status=receipt['status'],current_observation=receipt['observation'])))


if __name__=='__main__':main()
