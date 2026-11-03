"""Run the independently reviewed original reader only, in a fresh real aarch64 -B -I -S process."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;OUT=HERE.parents[1]
recipe=OUT/'parallel_platform_review/checkpoint_readonly_call_recipe.py'
transport=HERE.parents[2]/'2026-10-18_board_dialogue/board_ssh.py'
checkpoint_sha='c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471'
boot='903cfade-b93c-48fa-804e-379be1967313'
spec=importlib.util.spec_from_file_location('checkpoint_original_reader_strict_ssh',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
command='python3 -B -I -S - --checkpoint-sha256 '+checkpoint_sha+' --boot-id '+boot
result=json.loads(module.ssh(command,recipe.read_text(encoding='utf-8'),timeout=90))
assert result['loaded']['sha256']==checkpoint_sha and result['checkpoint_consumed'] is False
assert result['board_mutations'] is False and result['database_opened'] is False and result['device_opened'] is False
output=HERE/'original_reader_final_01.json'
with output.open('x',encoding='utf-8') as stream:
    json.dump({'host_observed_start_utc':start,'host_observed_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'recipe_source_sha256':hashlib.sha256(recipe.read_bytes()).hexdigest(),
        'transport_source_sha256':hashlib.sha256(transport.read_bytes()).hexdigest(),
        'remote_interpreter_options':['-B','-I','-S'],'board_result':result},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
seed=result['loaded']['seed'];aux=result['loaded']['auxiliary']
print(json.dumps({'output':str(output),'original_reader_passed':True,'checkpoint_sha256':checkpoint_sha,
    'seed':seed,'auxiliary':aux,'previous_kernel_history':result['loaded']['document'].get('previous_kernel_history'),
    'checkpoint_consumed':False,'board_mutations':False},ensure_ascii=False))
