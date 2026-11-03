"""Complete the existing read-only final/archive checks after the normal stop."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

HERE=Path(__file__).resolve().parent;OUT=HERE.parent;REVIEW=HERE/'checkpoint_review'
stop=json.loads((HERE/'camera_stop_receipt.json').read_text(encoding='utf-8'))
assert stop['status']=='CAMERA_STOPPED_NEW_FINAL_PRESENT'
source=REVIEW/'validate_archives_only_readonly.py'
data=source.read_bytes();assert hashlib.sha256(data).hexdigest()=='aff6b789f4b5d7a1ed03a70a3041835662c5aeb6e95e70a2365108d3ae9a6109'
normalized=data.decode('utf-8').replace('\r\n','\n')
assert hashlib.sha256(normalized.encode('utf-8')).hexdigest()=='3bde1b6229899cb71b97d7bb7bac51231c53942ac56b88bc16af6421762c4d20'
text=normalized.split("if __name__ == '__main__':",1)[0]
pre=json.loads((REVIEW/'prestop_current_01.json').read_text(encoding='utf-8'))['board_result']['prestop_counter_lower_bounds']
bounds={'sface':pre['sface_seven_counters'],'optional':pre['native_public_counter_recovery_tree']['optional']}
extra="""
    for key, minimum in PRESTOP_BOUNDS['sface'].items():
        require(aux['sface_counters'][key] >= minimum, 'SFace counter regressed: ' + key)
    for index, task in enumerate(('yunet', 'sface'), 1):
        prior = PRESTOP_BOUNDS['optional'][task]
        current = aux['inherited_optional'][task]
        for key in ('native_failures', 'not_submitted', 'overruns'):
            require(current[key] >= prior[key], 'Optional history regressed: ' + task + '.' + key)
            require(seed[key][index] >= prior[key], 'Native task counter regressed: ' + task + '.' + key)
        recovery = seed['recovery'][index-1]
        for key in ('faults', 'attempts', 'recoveries', 'probe_successes'):
            require(recovery[key] >= prior['recovery'][key], 'Recovery history regressed: ' + task + '.' + key)
        require(recovery['history_opaque'] == int(prior['recovery']['history_opaque']), 'Opaque recovery history changed')
"""
needle='    records = chain(document, binding, protection, boot_module)'
assert text.count(needle)==1
text=text.replace(needle,extra+'\n'+needle)
text='PRESTOP_BOUNDS = '+repr(bounds)+'\n'+text+"\nif __name__ == '__main__':\n    main()\n"
compiled=REVIEW/'validate_current_final_complete_readonly.py'
with compiled.open('x',encoding='utf-8') as stream:stream.write(text)
transport=OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('complete_final_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
intent=stop['intent']
argv=['/usr/bin/python3','-B','-I','-S','-', '--checkpoint-sha256',stop['checkpoint_sha256'],
    '--stop-intent-mono-ns',str(intent['stop_intent_mono_ns']),
    '--minimum-primary-calls',str(intent['primary_calls_lower_bound']),
    '--minimum-primary-overruns',str(intent['primary_period_overruns_lower_bound']),
    '--minimum-sface-completed',str(intent['sface_completed_lower_bound'])]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
value=json.loads(module.ssh(shlex.join(argv),text,timeout=45))
output=REVIEW/'FINAL_CHECKPOINT_VALIDATION.json';assert not output.exists()
output.write_text(json.dumps({'host_start_utc':started,'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'script_sha256':hashlib.sha256(text.encode()).hexdigest(),'all_observed_sface_optional_recovery_lower_bounds_checked':True,
    'board_result':value},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert value['original_python_validator_passed'] and value['full_previous_kernel_archive_chain_verified'] and value['archive_count']==18
print(json.dumps({'status':'ORIGINAL_FINAL_AND_ALL_18_ARCHIVES_VALIDATED',
    'checkpoint_sha256':value['checkpoint_pin']['sha256'],'archive_count':value['archive_count'],
    'all_observed_counter_lower_bounds_checked':True,'checkpoint_consumed':value['checkpoint_consumed'],
    'output':str(output)}))
