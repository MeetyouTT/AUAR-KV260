import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
result_path=HERE/'gui_stop_receipt.json';intent_path=HERE/'gui_stop_intent.json'
assert not result_path.exists() and not intent_path.exists()
latency=json.loads((OUT/'dialogue_latency_20261101/TWO_TURN_LATENCY.json').read_text(encoding='utf-8'))
assert latency['completed_turns']==2 and latency['both_full_playback_receipts_committed']
review=json.loads((OUT/'identity_dialogue_review/REVIEW_VERDICT.json').read_text(encoding='utf-8'))
assert review.get('status',review.get('verdict'))=='PASS_NO_REMAINING_CODE_REVIEW_BLOCKERS'
transport=OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('maintenance_strict_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
data=(HERE/'pause_and_stop_gui.py').read_bytes()
intent={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':hashlib.sha256(data).hexdigest(),
    'action':'pause if needed; normal GUI stop once','outcome':'observe before retry'}
intent_path.write_text(json.dumps(intent,indent=2)+'\n',encoding='utf-8')
result=json.loads(module.ssh('python3 -B -',data.decode('utf-8'),timeout=48))
result_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
