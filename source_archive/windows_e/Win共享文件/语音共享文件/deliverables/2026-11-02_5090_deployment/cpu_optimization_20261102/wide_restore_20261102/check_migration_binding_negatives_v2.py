"""Local semantic rejection probes; no original reader, OS, model or Native run."""
import ast
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
candidate = HERE / 'validate_fresh_final_history_original_migration_v2.py'
tree = ast.parse(candidate.read_text(encoding='utf-8'))
helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_original_operator_migration')
require_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'require')
scope = dict(Path=Path, SOURCE_UNIT='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32')
exec(compile(ast.Module(body=[require_node, helper], type_ignores=[]), '<candidate-input-binding-only>', 'exec'), scope)
function = scope['validate_original_operator_migration']
actual = json.loads((HERE / 'ORIGINAL_MIGRATION_EVIDENCE_RESULT.json').read_bytes())['board_result']['observation']
expected = dict(boot_id=actual['boot_id'], camera_owner=actual['source_owner'],
                owner_run_config_pin=actual['owner_run_config_pin'],
                original_operator_migration_pin={'path':'/public/synthetic-migration.json','sha256':'1'*64})
native = dict(source_unit_sha256='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512',
              library_sha256='c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656')
# This is an in-memory unit fixture, never a real or saved stop intent.
synthetic_intent = dict(stop_intent_mono_ns=actual['observed_mono_ns']+10000)
class TrustedSnapshotFixture:
    """Assume the unchanged Snapshot pin layer; test the new semantic binding."""
    def __init__(self, observation): self.observation=observation; self.calls=0
    def pinned(self, entry): self.calls+=1; return copy.deepcopy(self.observation)
    def read(self, path): raise AssertionError('Rejected cases must not reach source-file reads')
results=[]
def reject(name, mutate):
    e,n,o,i=copy.deepcopy(expected),copy.deepcopy(native),copy.deepcopy(actual),copy.deepcopy(synthetic_intent)
    mutate(e,n,o,i); fixture=TrustedSnapshotFixture(o)
    try: function(e,fixture,n,i)
    except (ValueError,KeyError) as error:
        results.append(dict(case=name,result='HOLD',error_type=type(error).__name__));return
    raise AssertionError(name+' was accepted')
reject('missing_migration_evidence',lambda e,n,o,i:e.pop('original_operator_migration_pin'))
reject('unknown_config_unit',lambda e,n,o,i:n.update(source_unit_sha256='0'*64))
reject('conflicting_original_owner',lambda e,n,o,i:o['source_owner'].update(pid=o['source_owner']['pid']+1))
reject('conflicting_run_config_pin',lambda e,n,o,i:o['owner_run_config_pin'].update(sha256='0'*64))
reject('post_intent_observation',lambda e,n,o,i:o.update(observed_mono_ns=i['stop_intent_mono_ns']+1))
reject('forged_operator_manifest_pin',lambda e,n,o,i:o['native_operator_manifest_pin'].update(sha256='0'*64))
reject('wrong_observation_schema',lambda e,n,o,i:o.update(schema='synthetic-approved-boolean'))
fixture=TrustedSnapshotFixture(None)
function(expected,fixture,dict(source_unit_sha256=scope['SOURCE_UNIT']),synthetic_intent)
assert fixture.calls==0
results.append(dict(case='original_current_unit_path_unchanged',result='ACCEPT_ORIGINAL_PATH_NO_MIGRATION_LOOKUP'))
report=dict(schema='aura-migration-input-local-rejection-probes-1',candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
            cases=results,all_expected=True,scope='Only new semantic input binding with trusted Snapshot abstraction. Does not validate fabricated bytes, cryptographic pins, original Native readers, real service lifecycle or physical migration; those remain separately checked on actual sources and genuine stop inputs.',
            original_reader_or_Native_or_model_or_board_executed=False,files_written='this local probe report only')
(HERE/'ORIGINAL_MIGRATION_BINDING_NEGATIVES_V2.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(cases=len(results),all_expected=True,candidate_sha256=report['candidate_sha256'])))
