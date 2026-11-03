"""Pure local reproduction using the exact original methods and synthetic snapshots."""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import threading
import time
import uuid

OUT = Path(__file__).resolve().parents[3]
BASE = OUT / 'identity_dialogue_collaboration/baseline'
SOURCE = BASE / 'board/identity/voice_enrollment.py'
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '83796dd78c57555ea66eeb2b745a89f8b3670945a4406176cb3486111d9466b8'
space = {'copy':copy, 'math':math, 'threading':threading, 'time':time, 'uuid':uuid, 'millis':lambda:1000}
contract = ast.parse((BASE/'board/interaction/ui_contract.py').read_text(encoding='utf-8'))
for node in contract.body:
    if (isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
            and node.targets[0].id in ('PROTOCOL','MODULE_STATES','ACTIONS')):
        space[node.targets[0].id] = ast.literal_eval(node.value)
functions = [copy.deepcopy(n) for n in contract.body if isinstance(n,ast.FunctionDef)
    and n.name in ('integer','text','require','target_key','validate_snapshot')]
exec(compile(ast.Module(body=functions,type_ignores=[]),'<original-pure-snapshot-validator>','exec'),space)
fixture = ast.parse((BASE/'tests/framework/test_simple_enrollment.py').read_text(encoding='utf-8'))
snapshot = copy.deepcopy(next(n for n in fixture.body if isinstance(n,ast.FunctionDef) and n.name=='snapshot'))
exec(compile(ast.Module(body=[snapshot],type_ignores=[]),'<public-synthetic-snapshot>','exec'),space)
klass = copy.deepcopy(next(n for n in ast.parse(raw.decode('utf-8')).body
    if isinstance(n,ast.ClassDef) and n.name=='VoiceEnrollment'))
methods = {'__init__','reset','_send','_cancel_sample','_start_simple','selected_target','single_target','owner_of'}
klass.body = [n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name in methods]

class Speech:
    @staticmethod
    def result(code,name=''):
        return {'code':code,'name':name}

space['speech'] = Speech
exec(compile(ast.Module(body=[klass],type_ignores=[]),'<exact-original-voice-start-methods>','exec'),space)
Voice = space['VoiceEnrollment']
result = {}
for delayed in (False,True):
    current = space['snapshot']()
    backend = copy.deepcopy(current)
    commands = []
    def command(value):
        commands.append(value['action'])
        if value['action']=='identity_sample_start':
            backend['modules']['identity']['enrollment_sampling'].update(
                stage='collect',session_id='synthetic-new-session',bound_target=copy.deepcopy(value['params']['target']))
        return {'accepted':True,'command_id':value['command_id']}
    def snapshot_provider():
        return copy.deepcopy(current if delayed else backend)
    voice = Voice('boot',snapshot_provider,command,simple=True,clock=lambda:0.,now_ms=lambda:1000)
    voice.name='合成称呼'
    voice.owner=voice.owner_of(current)
    voice.stage='authorize'
    voice.until=120
    decision=voice._start_simple(current)
    result['delayed_valid_cached_snapshot' if delayed else 'immediate_published_snapshot'] = {
        'reply_code':decision['code'],'face_fsm_stage':voice.stage,
        'local_sampling_session_bound':bool(voice.sampling_id),
        'camera_sampling_stage':backend['modules']['identity']['enrollment_sampling']['stage'],
        'sent_action_sequence':commands,'cancel_was_sent':'identity_sample_cancel' in commands}
assert result['immediate_published_snapshot']['reply_code']=='sample_auto'
assert result['delayed_valid_cached_snapshot'] == {
    'reply_code':'sample_failed','face_fsm_stage':'idle','local_sampling_session_bound':False,
    'camera_sampling_stage':'collect','sent_action_sequence':['identity_sample_start'],'cancel_was_sent':False}
print(json.dumps({'schema':'aura-original-start-cached-snapshot-race-reproduction-1',
    'original_source_sha256':hashlib.sha256(raw).hexdigest(),
    'exact_original_methods_and_original_snapshot_validation_used':True,'two_cases':result,
    'deterministic_code_race_reproduced':True,'unique_live_cause_proved':False,
    'services_devices_models_real_databases_or_network_accessed':False,
    'production_or_candidate_code_changed':False}))
