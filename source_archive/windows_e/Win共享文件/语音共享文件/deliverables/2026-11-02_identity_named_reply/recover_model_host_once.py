from datetime import datetime,timezone
import hashlib,importlib.util,json,os,socket,sys
from pathlib import Path
TASK=Path(__file__).resolve().parent
ROOT='01a1994e-f547-74e1-903d-3591021d67c8'
phase=json.loads((TASK/'DEVICE_MAINTENANCE.json').read_bytes())
c=json.loads((TASK.parent/'2026-11-02_5090_deployment'/'CHAT_COORDINATION.json').read_bytes())
assert phase['permission_active'] and phase['operator_thread_id']==ROOT
assert c['board_maintenance_owner']['permission_active'] and c['board_maintenance_owner']['thread_id']==ROOT
host=TASK.parent/'2026-10-30_board_owner'/'integration'/'production_model_host'
sys.path.insert(0,str(host));import manage
before=manage.status();assert before['status']=='OWNER_EXITED' and not before['owner_alive']
settings,config_sha=manage.config()
assert settings['host']=='192.168.50.1' and settings['port']==8797
s=socket.socket();s.settimeout(1)
try:assert s.connect_ex((settings['host'],settings['port']))!=0
finally:s.close()
intent=dict(schema='aura-original-model-host-recovery-intent-1',issued_utc=datetime.now(timezone.utc).isoformat(),
 reason='Windows reboot at 2026-11-03T07:18:48Z interrupted the GUI startup after its model-health check.',
 status_before=before,normal_start_submissions=1,configuration_sha256=config_sha,
 source_sha256={k:hashlib.sha256((host/k).read_bytes()).hexdigest() for k in ('manage.py','production_runtime.py')},
 no_model_or_endpoint_configuration_change=True)
with (TASK/'model_recovery_1_HOST_INTENT.json').open('x',encoding='utf-8') as f:json.dump(intent,f,ensure_ascii=False,indent=2)
try:
 after=manage.start(wait_seconds=320)
 assert after['status']=='STARTED' and after['owner_alive'] and after['health']['ok']
 assert after['health']['backend']['model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
 assert after['health']['backend']['num_step']==16 and after['health']['backend']['tts_ready']
 assert manage.config()[1]==config_sha
 result=dict(status='ORIGINAL_MODEL_HOST_RESTORED_AFTER_WINDOWS_REBOOT',completed_utc=datetime.now(timezone.utc).isoformat(),result=after,
  configuration_unchanged=True,normal_start_submissions=1,forced_actions=0,pending_calls=0)
except Exception as error:
 result=dict(status='RECOVERY_NOT_CONFIRMED',error_class=type(error).__name__,error=str(error)[:160])
with (TASK/'model_recovery_1_RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='result'},ensure_ascii=False))
if result['status']!='ORIGINAL_MODEL_HOST_RESTORED_AFTER_WINDOWS_REBOOT':raise SystemExit(2)
