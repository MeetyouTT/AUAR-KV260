"""Run an inspected metadata-only board script with a unique local receipt."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')
script_path, receipt_prefix, timeout_text = sys.argv[1:]
source = Path(script_path).read_bytes()
compile(source, script_path, 'exec')
prefix = Path(receipt_prefix)
intent_path = prefix.with_name(prefix.name + '_HOST_INTENT.json')
result_path = prefix.with_name(prefix.name + '_RESULT.json')
assert not intent_path.exists() and not result_path.exists(), 'Reconcile prior request before repeating'
helper = Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-10-18_board_dialogue\board_ssh.py')
assert hashlib.sha256(helper.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('aura_board_ssh', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
intent = dict(host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              script_sha256=hashlib.sha256(source).hexdigest(), script_path=str(Path(script_path).absolute()),
              single_submission=True)
with intent_path.open('x', encoding='utf-8') as stream:
    json.dump(intent, stream, indent=2)
    stream.write('\n')
try:
    raw_result = module.ssh('python3 -B -', script=source.decode('utf-8'), timeout=float(timeout_text))
    result = dict(host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  board_result=json.loads(raw_result))
except BaseException as exc:
    result = dict(host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  status='REQUEST_RESULT_UNCONFIRMED_RECONCILE_BEFORE_ACTION', error_class=type(exc).__name__)
    with result_path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))
    raise SystemExit(2)
with result_path.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
samples = result['board_result'].get('samples')
if type(samples) is list and len(samples) > 5:
    generations = {}
    for row in samples:
        route = row.get('route_trace') or {}
        handler = row.get('handler_trace') or {}
        generations[row.get('route_generation')] = dict(
            elapsed=row.get('elapsed'), mode=row.get('entry_mode'),
            awaiting_name=row.get('entry_name_pending'), speaker_active=row.get('speaker_active'),
            asr_characters=route.get('asr_characters'),
            keywords=[k for k,v in route.items() if k.startswith('has_') and v is True],
            kind=handler.get('binding_kind'), business_turn=handler.get('business_turn_result'),
            speaker_present_after=handler.get('speaker_present_after'),
            error=handler.get('error_class'), reset=handler.get('reset_since_trace'))
    print(json.dumps(dict(host_utc=result['host_utc'], sample_count=len(samples),
                         final=samples[-1], generation_summaries=list(generations.values())[-12:])))
else:
    print(json.dumps(result))
