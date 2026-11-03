"""Install reviewed launcher support and a clearly provisional fit experiment."""
import hashlib,json,os,runpy,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];G=H.parent/'2026-10-29_gpu_coordination'
name='deliverables/2026-10-18_board_dialogue/project_ollama.py';path=P/name
raw=(G/'extras/candidate'/name).read_bytes();expected=json.loads((G/'extras/SOURCE_MANIFEST.json').read_text())[name]['sha256']
assert hashlib.sha256(raw).hexdigest()==expected
assert hashlib.sha256(path.read_bytes()).hexdigest()=='af3468333d92694525d9994934087d50932440ac3f4b755c26e19715a9a61ee9'
config=P/'aura/config/ollama_runtime.local.json';assert not config.exists()
backup=H/'layout_source_before'/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(path.read_bytes())
temporary=path.with_name(path.name+'.layout-'+uuid.uuid4().hex);temporary.write_bytes(raw);os.replace(temporary,path)
policy=dict(schema_version=1,fit_target_mib=2048,calibration_id='provisional-layout-probe-20261029-2g',
 gpu_uuid='GPU-fd752a2e-1923-22d0-63af-4e3d8e6f17b8',ollama_version='0.40.13')
config.write_text(json.dumps(policy,indent=2),encoding='utf-8')
report=dict(status='PREPARED_NOT_APPLIED',phase='PROVISIONAL_LAYOUT_EXPERIMENT',policy=policy,
 reason='Observed only 250MiB physical free with project27B and residentTTS; steady peak calibration is still in progress',
 original_launcher_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),candidate_launcher_sha256=expected,
 initial_cold_peak_bytes=4972347392,short_steady_extra_reserved_bytes=153092096,
 other_model_processes_to_change=[],target_daemon='127.0.0.1:11435',production_gpu_calibration_complete=False)
(H/'layout_plan.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
module=runpy.run_path(str(path));result=module['ensure']()
assert result['status']=='REUSED' and result['needs_controlled_restart']
(H/'layout_preflight.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'status':'PREPARED_NOT_APPLIED','fit_target_mib':2048,'only_project_child_environment':True,'needs_controlled_restart':True}))
