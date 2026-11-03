"""Document consistency/byte-preservation checks only; no runtime operations."""
import json
from pathlib import Path
import re
import update_core as u


def main():
    observation_path=u.REPAIR/'current_observation_v15.json'
    observation=json.loads(observation_path.read_bytes())
    before=json.loads((u.HERE/'before_manifest.json').read_bytes())
    sealed=json.loads((u.HERE/'sealed_receipt.json').read_bytes())
    checks={}
    checks['v14_exact_document_archives']=all(u.record(Path(item['path']))['sha256']==item['sha256'] for item in before.values())
    checks['v14_observation_unchanged']=u.record(u.REPAIR/'current_observation_v14.json')['sha256']==observation['previous_observation']['sha256']
    checks['frozen_evidence_hashes']=all(u.record(Path(item['path']))['sha256']==item['sha256'] for item in observation['evidence'].values())
    checks['sealed_current_file_hashes']=all(u.record(Path(item['path']))['sha256']==item['sha256'] for item in sealed['files'].values())
    expected=u.record(observation_path)['sha256']
    for filename,path in (('status',u.REPAIR/'STATUS.json'),('implementation',u.OWNER/'IMPLEMENTATION_STATE.json')):
        value=json.loads(path.read_bytes())
        checks[filename+'_startup']=value['startup_sha256']==u.STARTUP if filename=='status' else value['production']['startup_sha256']==u.STARTUP
        checks[filename+'_observation_reference']=value['current_observation']['sha256']==expected
        old=json.loads(Path(before['dialogue_STATUS.json' if filename=='status' else 'IMPLEMENTATION_STATE.json']['path']).read_bytes())
        checks[filename+'_older_history_preserved']=value['continuation_history'][:len(old.get('continuation_history',[]))]==old.get('continuation_history',[])
        checks[filename+'_historical_fields_preserved']=all(value[k]==v for k,v in old.items() if k.startswith('historical_'))
    for label,path,marker,before_key in (
        ('agents',u.PROJECT/'AGENTS.md','board-business-live-20261030','project_AGENTS.md'),
        ('project_readme',u.PROJECT/'README.md','dialogue-current-20261031','project_README.md'),
        ('analysis_readme',u.ANALYSIS/'README.md','board-business-live-20261030','analysis_README.md')):
        raw=path.read_bytes();old=Path(before[before_key]['path']).read_bytes()
        begin=('<!-- '+marker+' -->').encode();end=('<!-- /'+marker+' -->').encode()
        left=old.index(begin)+len(begin);right=old.index(end,left)
        old_body=old[left:right]
        checks[label+'_old_current_body_preserved']=old_body in raw
        checks[label+'_older_suffix_preserved']=raw.endswith(old[right+len(end):])
        active=raw[raw.index(begin):raw.index(end)+len(end)]
        checks[label+'_v15_current']=b'v15' in active and u.STARTUP.encode() in active if label!='project_readme' else b'v15' in active
    for label,key,path in (
        ('owner_text','owner_continuation.txt',u.OWNER/'板端业务正式接管与实测接续_20261030.txt'),
        ('performance_plan','performance_plan.txt',u.REPAIR/'板端性能分配与优化计划.txt')):
        checks[label+'_entire_old_text_preserved']=path.read_bytes().endswith(Path(before[key]['path']).read_bytes())
    readme=(u.PROJECT/'README.md').read_text(encoding='utf-8')
    active=readme.split('<!-- dialogue-current-20261031 -->',1)[1].split('<!-- /dialogue-current-20261031 -->',1)[0]
    checks['project_current_markdown_links_exist']=all((u.PROJECT/target).is_file() for target in re.findall(r'\]\(([^)]+)\)',active))
    analysis=(u.ANALYSIS/'README.md').read_text(encoding='utf-8')
    active=analysis.split('<!-- idle-cpu-v15-report-20261031 -->',1)[1].split('<!-- /idle-cpu-v15-report-20261031 -->',1)[0]
    checks['analysis_current_report_link_exists']=all((u.ANALYSIS/target).is_file() for target in re.findall(r'\]\(([^)]+)\)',active))
    feedback=observation['user_feedback']
    checks['user_continuity_true_waiting_false']=feedback['audio_continuity_user_confirmed'] is True and feedback['waiting_improvement'] is False
    checks['no_false_round_timing']=feedback['human_feedback_turn_stage_timings_available'] is False
    checks['no_false_cpu_or_fps_acceptance']=observation['resource_observation']['controlled_abba'] is False and observation['resource_observation']['target_16fps_acceptance_passed'] is False
    checks['new_asr_not_deployed']=observation['asr_candidates']['new_streaming_models_deployed'] is False
    result=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,current_observation=u.record(observation_path),
                documentation_only=True,hardware_model_or_db_operations=[])
    u.atomic(u.HERE/'consistency_check.json',u.encoded(result))
    print(json.dumps(result,ensure_ascii=False))
    if not all(checks.values()):raise SystemExit(1)


if __name__=='__main__':main()
