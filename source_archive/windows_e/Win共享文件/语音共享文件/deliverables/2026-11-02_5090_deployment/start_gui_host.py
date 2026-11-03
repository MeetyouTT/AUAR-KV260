"""Root-owned one-shot GUI start, gated by actual LAN and public board receipts."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TRANSACTION=HERE/'parallel_lan/transactions/2524d38f24674cdca495ed726f38b41d'
SESSION='2f3a707efa62401d81fc20ef22a379cb'
intent_path=HERE/'gui_start_intent.json'
result_path=HERE/'gui_start_request.json'
assert not intent_path.exists() and not result_path.exists(), 'Reconcile the existing start request before any retry'
transaction=json.loads((TRANSACTION/'transaction.json').read_text(encoding='utf-8'))
assert transaction['phase']=='LAN_PUBLIC_BOARD_MODEL_PROBE_PASS_PHYSICAL_ACCEPTANCE_PENDING'
assert transaction['candidate_record']['session_id']==SESSION
probe=json.loads((TRANSACTION/'board_public_probe.json').read_text(encoding='utf-8'))
assert probe['status']=='PUBLIC_BOARD_LLM_AND_TTS_RAM_ONLY_PASS' and probe['host_session_id']==SESSION
assert probe['local_tts_same_owner'] and probe['protected_ollama_same_owner']
firewall=json.loads((HERE/'parallel_lan/firewall_result.json').read_text(encoding='utf-8'))
assert firewall['status'] in ('CREATED_EXACT_RULE','REUSED_EXACT_RULE','CHECKED_EXACT_RULE')
assert firewall['guard']['session_id']==firewall['guard_after']['session_id']==SESSION
assert firewall['other_rules_modified'] is False
source=HERE/'start_gui_guarded.py'
data=source.read_bytes()
assert hashlib.sha256(data).hexdigest()=='addc657c29cc92053071b5de03362a0e0a493d897a456a466412af256a48ca90'
transport=HERE.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('root_start_gui_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
intent={'schema':'aura-gui-start-intent-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'session':SESSION,'source_sha256':hashlib.sha256(data).hexdigest(),
    'command':'systemctl start --no-block aura-avatar-ui.service',
    'status':'REQUEST_ABOUT_TO_SEND_OBSERVE_BEFORE_RETRY'}
with intent_path.open('x',encoding='utf-8') as stream:
    json.dump(intent,stream,indent=2);stream.write('\n');stream.flush()
raw=module.ssh('python3 -B -',data.decode('utf-8'),timeout=45)
receipt=json.loads(raw)
with result_path.open('x',encoding='utf-8') as stream:
    json.dump({'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'board_result':receipt},stream,indent=2);stream.write('\n')
assert receipt['exit_code']==0 and receipt['start_requested'] is True
print(json.dumps({'output':str(result_path),'start_requested':True,'software_ready':False}))
