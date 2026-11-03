"""Publish filtered deployment metadata only; preserve images/raw UART privately."""
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path

job=Path('/home/ghmd/aura-identity-dpu-check-20261018')
delivery=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-18_identity_dpu_runtime')
phases=['final-idle-precheck','runtime-activate-final-start','runtime-activate-final-progress',
        'runtime-activate-final-result','runtime-activate-final-result2',
        'runtime-activate-after-rollback-window','uart-output-resume',
        'reboot-screen-diagnose','reboot-screen-capture','screen-retrain',
        'restore-baseline-start','restore-baseline-precheck-detail','restore-baseline-start2',
        'reboot-cause-evidence','restore-baseline-progress','restore-baseline-result',
        'restored-baseline-health','restore-baseline-final']
new=[]
for phase in phases:
 candidates=sorted((job/'evidence').glob('*-'+phase))
 assert len(candidates)==1,(phase,candidates)
 origin=candidates[0];target=delivery/'evidence'/phase;target.mkdir(exist_ok=True)
 for name in ('source.py','response.json','status.json'):
  path=origin/name
  if not path.is_file():continue
  raw=path.read_bytes();dest=target/name
  if dest.exists():assert dest.read_bytes()==raw
  else:
   with dest.open('xb') as stream:stream.write(raw)
  new.append({'path':str(dest.relative_to(delivery)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})

p=delivery/'verification.json';data=json.loads(p.read_text())
records={x['path']:x for x in data['evidence_files']}
for record in new:records[record['path']]=record
restore=json.loads((delivery/'evidence/restore-baseline-final/response.json').read_text())
assert restore['status']=='PASS_ORIGINAL_SERVICES_RESTORED_DISPLAY_PHYSICAL_PENDING'
data.update(status='PASS_ORIGINAL_BASELINE_RESTORED_DISPLAY_PHYSICAL_CHECK_PENDING_DPU_ACCEPTANCE_FAILED',
 updated_at_utc=datetime.now(timezone.utc).isoformat(),formal_live_service_switched=False,
 candidate_units_observed_installed=True,candidate_services_active_after_new_boot=True,
 live_identity_ready=False,live_identity_disabled_by_budget=True,live_identity_maximum_ms=20.11,
 live_activation_result_written=False,automatic_rollback_confirmed=False,
 board_reboot_observed=True,reboot_initiated_by_agent=False,reboot_cause='UNKNOWN',
 last_observed_boot_id=restore['boot_id_current'],idle_question_pending=False,
 original_services_restored=True,restore_result=restore['status'],reboots_observed=2,
 current_service_baseline='ORIGINAL_CONTINUOUS_DIALOGUE_WITHOUT_IDENTITY',
 user_confirmed_dialogue_ended=True,physical_panel_report='GARBLED',
 x11_screenshot_layout_intact=True,display_edid_bytes=0,display_output_reinitialized=True,
 physical_panel_verified=False,windows_script_executed=False,voice_identity_enabled=False,
 frozen_source_note='source/ and runtime ZIP retain the earlier candidate; live documentation has newer deployment evidence')
data['evidence_files']=list(records.values());data['evidence_files_verified']=len(records)
for record in data['source_files']:
 raw=(delivery/'source'/record['path']).read_bytes()
 assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256'],record['path']
for record in data['evidence_files']:
 raw=(delivery/record['path']).read_bytes()
 assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256'],record['path']
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'frozen_sources_verified':len(data['source_files']),'filtered_evidence_verified':len(records),'new_filtered_files':len(new),'status':data['status']},ensure_ascii=False))
