"""Same-boot GUI configuration binding after the exact completed camera A/B/A.

Local preparation is the default. All remote actions remain root-only.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PREVIOUS = REPAIR / 'release_v21_asr2_display_candidate'
EVIDENCE = PREVIOUS / 'asr2_display_evidence'
CAMERA = REPAIR / 'jpeg_demand_camera_trial_v21'
BASE_SPEC_SHA = '8dcd958d07de22f996d5f406ab399cdf51e252b1cbd209fac9fdbc6cae8d87a7'
BASE_READY_SHA = '2825ff9e0828d6c0a156f0bc0e819d2b850d57d98665ee614801ca94d568cbd0'
BASE_MAPPING_SHA = 'bff1b76381914cfa070c617e21ce091e8b97a8b7062f408c842cbcf03bc5dee2'
BASE_STARTUP_SHA = '94f665cf69e861d4f3d625dd627116218120cdbbef2244aa4cf2b63c39b9f1c7'
BASE_MANIFEST_SHA = '6f3d928489ba163a47d8c844141d23333e348a7bb028c3f997b34f2f86685388'
BASE_CONFIG_SHA = '228abe8f642254c68ad500a15f8d637189343a97753d1c359663744dc2bd06a2'
REMOTE_SHA = '961f6436b97b745e23114cf5e1e7a5c86c14abef61b511293fba74a51871b549'
HELPER_SHA = 'e42df5b355b627ac4a6df21086e8cf07a43b722ffc6b5c5bdd5b93f96b3b8124'
RESTORED_SHA = '1fa36e04faae167aee834f0d25d8fd674bc0094ec4c7b56be52460e074faa26d'
CONFIG_RELATIVE = 'config/board_avatar_gtk.json'
REVISION = 'camera-owner-rebind-v22'
CONTROL = '/home/root/aura-board-business-20261030/control-production-v1'
PAYLOAD_FINALIZED = True


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8')


def need(value, reason):
    if not value:
        raise ValueError(reason)


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None


def pinned(path, expected):
    path = Path(path)
    need(path.resolve() == path and not path.is_symlink(), 'local_source_path_changed')
    raw = path.read_bytes()
    need(valid_sha(expected) and sha(raw) == expected, 'pinned_source_changed')
    return raw


def load_camera_modules():
    modules = []
    for name, expected in [('rebuild_same_boot_readback.py', HELPER_SHA), ('restored_readback.py', RESTORED_SHA)]:
        path = CAMERA / name
        pinned(path, expected)
        spec = importlib.util.spec_from_file_location('_rebind_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


def frozen_remote():
    return pinned(PREVIOUS / 'FROZEN_PUBLISH_CONFIGURATION_REMOTE.py', REMOTE_SHA).decode('utf8')


def literal(name):
    nodes = [node for node in ast.parse(frozen_remote()).body if isinstance(node, ast.Assign)
             and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name]
    need(len(nodes) == 1, 'unique_frozen_literal_required')
    return ast.literal_eval(nodes[0].value)


def baseline():
    value = json.loads(pinned(EVIDENCE / 'spec.json', BASE_SPEC_SHA))
    mapping = json.loads(pinned(EVIDENCE / 'source_mapping.json', BASE_MAPPING_SHA))
    ready = json.loads(pinned(EVIDENCE / 'ready.json', BASE_READY_SHA))
    need(value['startup_sha256'] == BASE_STARTUP_SHA and value['source_manifest_sha256'] == BASE_MANIFEST_SHA
         and value['configuration_sha256'] == BASE_CONFIG_SHA and value['component_pins'] == 380
         and len(value['component_sha256']) == 380 and mapping['component_pins'] == value['component_sha256']
         and mapping['current_publication_committed'] is True, 'actual_v21_380_source_closure_required')
    need(ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY' and ready['guard_removed'] is True
         and ready['listening_enabled'] is False and ready['physical_microphone_opened'] is False
         and value['expected_final_listening_enabled'] is False, 'actual_v21_saved_pause_required')
    need(sha(encoded(literal('EXPECTED_STARTUP'))) == BASE_STARTUP_SHA
         and sha(encoded(literal('EXPECTED_GUI'))) == BASE_CONFIG_SHA, 'frozen_v21_configuration_bytes_required')
    return value


def validate_binding(binding):
    need(set(binding) == {'authority', 'authority_sha256', 'written_proof', 'written_proof_sha256', 'face_path'},
         'exact_rebind_inputs_required')
    helper, restored = load_camera_modules()
    authority = restored.validate_authority(binding['authority'], helper)
    # SHA records refer to the separately reviewed local input files. Their exact
    # bytes are checked by prepare. The canonical authority is bound in the spec.
    need(valid_sha(binding['authority_sha256']) and valid_sha(binding['written_proof_sha256']),
         'reviewed_input_hashes_required')
    proof = binding['written_proof']
    fields = {'ready', 'status', 'owner', 'original_pin_count', 'candidate_pin_count', 'candidate_sha256',
              'observation_sha256', 'journal_sha256', 'executor_sha256', 'latest_consumed_checkpoint_sha256',
              'new_runtime_sha256', 'private_original_config_changed', 'database_opened', 'native_runner_loaded',
              'service_action_sent', 'checkpoint_or_marker_modified', 'new_boot_admission_used', 'written'}
    need(set(proof) == fields and proof['ready'] is True and proof['written'] is True
         and proof['status'] == 'SAME_BOOT_READBACK_CANDIDATE_WRITTEN_NOT_INSTALLED'
         and type(proof['original_pin_count']) is int and proof['original_pin_count'] == 21
         and type(proof['candidate_pin_count']) is int and proof['candidate_pin_count'] == 22,
         'actual_written_22_pin_readback_proof_required')
    owner = proof['owner']
    need(set(owner) == {'board_boot_id', 'camera_pid', 'camera_start_ticks', 'camera_cmdline_sha256'}
         and owner['board_boot_id'] == authority['boot'] and type(owner['camera_pid']) is int
         and owner['camera_pid'] == authority['restored_pid'] and isinstance(owner['camera_start_ticks'], str)
         and re.fullmatch('[1-9][0-9]*', owner['camera_start_ticks']) is not None
         and valid_sha(owner['camera_cmdline_sha256']), 'exact_restored_owner_required')
    for key in ('candidate_sha256', 'observation_sha256', 'journal_sha256', 'executor_sha256',
                'latest_consumed_checkpoint_sha256', 'new_runtime_sha256'):
        need(valid_sha(proof[key]), 'bounded_proof_hash_required')
    need(proof['journal_sha256'] == authority['journal_sha256']
         and proof['executor_sha256'] == authority['executor_sha256']
         and proof['latest_consumed_checkpoint_sha256'] == authority['checkpoint_sha256'],
         'proof_authority_disagrees')
    for key in ('private_original_config_changed', 'database_opened', 'native_runner_loaded',
                'service_action_sent', 'checkpoint_or_marker_modified', 'new_boot_admission_used'):
        need(proof[key] is False, 'read_only_proof_required')
    face = binding['face_path']
    need(isinstance(face, str) and face.startswith('/home/root/aura-board-owner-candidate-20261030/')
         and '..' not in PurePosixPath(face).parts and not any(ord(x) < 32 for x in face)
         and str(PurePosixPath(face)) == face and face.endswith('.json')
         and face not in {authority['baseline_path'], authority['journal_path'], authority['executor_path']},
         'new_private_readback_path_required')
    return copy.deepcopy(binding)


def configuration_for(binding):
    binding = validate_binding(binding)
    value = literal('EXPECTED_GUI')
    value['board_business']['face_readback'] = {'path': binding['face_path'],
                                               'sha256': binding['written_proof']['candidate_sha256']}
    return value


def startup_for(spec):
    value = literal('EXPECTED_STARTUP')
    value['component_sha256'] = spec['component_sha256']
    return json.loads(encoded(value))


def proposed(binding):
    binding = validate_binding(binding)
    value = baseline()
    config_sha = sha(encoded(configuration_for(binding)))
    value['camera_owner'] = copy.deepcopy(binding['written_proof']['owner'])
    value['face_readback'] = {'path': binding['face_path'], 'sha256': binding['written_proof']['candidate_sha256']}
    value['configuration_sha256'] = config_sha
    value['component_sha256'][CONFIG_RELATIVE] = config_sha
    value['release_sources'][CONFIG_RELATIVE] = config_sha
    stage = CONTROL + '/' + REVISION + '-' + binding['written_proof']['observation_sha256'][:16]
    value['minor_prepared_configuration_path'] = stage + '/prepared-gui.json'
    value['startup_sha256'] = sha(encoded(startup_for(value)))
    value['source_manifest_sha256'] = '0' * 64
    value['camera_rebind'] = {'state': 'PROPOSED', 'revision': REVISION, 'stage': stage, 'binding': binding,
                              'previous_spec_sha256': BASE_SPEC_SHA}
    return json.loads(encoded(value))


def validate_spec(spec, *, allow_baseline=False, allow_proposed=False):
    if 'camera_rebind' not in spec:
        need(allow_baseline and spec == baseline(), 'exact_v21_baseline_required')
        return spec
    expected = proposed(spec['camera_rebind']['binding'])
    if spec['camera_rebind']['state'] == 'APPLIED':
        need(valid_sha(spec['source_manifest_sha256']) and spec['source_manifest_sha256'] != '0' * 64,
             'actual_applied_manifest_required')
        expected['source_manifest_sha256'] = spec['source_manifest_sha256']
        expected['camera_rebind']['state'] = 'APPLIED'
    else:
        need(allow_proposed and spec['camera_rebind']['state'] == 'PROPOSED', 'applied_rebind_required')
    need(spec == expected, 'only_exact_same_boot_face_binding_allowed')
    return spec


def replace_node(source, name, replacement, *, function=False):
    tree = ast.parse(source)
    if function:
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    else:
        nodes = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
    need(len(nodes) == 1, 'unique_frozen_source_anchor_required')
    node = nodes[0]
    lines = source.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno] = [replacement.rstrip() + '\n']
    return ''.join(lines)


REVIEWED_FACE = '''def reviewed_face():
 import types
 helper=types.ModuleType('_rebind_sameboot_helper')
 helper.__file__='<pinned-sameboot-helper>'
 exec(compile(SAMEBOOT_HELPER,helper.__file__,'exec'),helper.__dict__)
 wrapper=types.ModuleType('_rebind_restored_readback')
 wrapper.__file__='<pinned-restored-readback>'
 exec(compile(RESTORED_HELPER,wrapper.__file__,'exec'),wrapper.__dict__)
 binding=SPEC['camera_rebind']['binding']
 authority=wrapper.validate_authority(binding['authority'],helper)
 candidate,report=wrapper.prove(helper,authority)
 expected=dict(binding['written_proof'],written=False,status='SAME_BOOT_RESTORED_READBACK_CANDIDATE_READY_NOT_INSTALLED')
 need(report==expected and report['owner']==SPEC['camera_owner'],'fresh_complete_sameboot_readback_proof_changed')
 face=SPEC['face_readback'];path=Path(face['path'])
 need(path.parent.resolve()==path.parent and path.parent.stat().st_mode&0o077==0,'private_readback_directory_required')
 raw=helper.private_read(str(path))
 need(c.sha(raw)==face['sha256'] and raw==helper.encoded(candidate),'written_private_readback_changed')
 return report
'''


def publisher_remote(spec):
    validate_spec(spec, allow_baseline=True, allow_proposed=True)
    source = frozen_remote()
    if 'camera_rebind' not in spec:
        return source
    source = replace_node(source, 'EXPECTED_GUI', 'EXPECTED_GUI=' + repr(configuration_for(spec['camera_rebind']['binding'])))
    source = replace_node(source, 'EXPECTED_STARTUP', 'EXPECTED_STARTUP=' + repr(startup_for(spec)))
    source = replace_node(source, 'reviewed_face', REVIEWED_FACE, function=True)
    prefix = 'SAMEBOOT_HELPER=' + repr(pinned(CAMERA / 'rebuild_same_boot_readback.py', HELPER_SHA).decode()) + '\n'
    prefix += 'RESTORED_HELPER=' + repr(pinned(CAMERA / 'restored_readback.py', RESTORED_SHA).decode()) + '\n'
    source = prefix + source
    anchor = " fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)\n if ACTION=='guard':result=guard()"
    need(source.count(anchor) == 1, 'unique_frozen_locked_dispatch_required')
    guarded_dispatch = """ fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if ACTION in ('start','ready'):
  rebind_j=journal();rebind_marker=rebind_j.get('camera_rebind',{})
  need(rebind_marker.get('state')=='APPLIED' and rebind_marker.get('stage')==SPEC['camera_rebind']['stage']
       and rebind_marker.get('binding_sha256')==c.sha(c.encoded(SPEC['camera_rebind']['binding']))
       and rebind_j.get('target_startup_sha256')==SPEC['startup_sha256'],'completed_rebind_required_before_lifecycle')
  rebind_tx=c.parse(c.read(Path(SPEC['camera_rebind']['stage'])/'transaction.json',rebind_marker['transaction_sha256']))
  need(rebind_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC)),'completed_rebind_spec_changed')
 if ACTION=='guard':result=guard()"""
    source = source.replace(anchor, guarded_dispatch)
    ast.parse(source, feature_version=(3, 9))
    return source


def write_new_json(path, value):
    raw = encoded(value)
    with Path(path).open('xb') as stream:
        stream.write(raw)
    return sha(raw)


def execute_remote(remote, values, *, timeout=225):
    need(PAYLOAD_FINALIZED is True, 'root_reviewed_final_package_required')
    sys.path.insert(0, str(REPAIR / 'release_v18_candidate'))
    from v18_common import publisher_script, ssh_json
    return ssh_json(publisher_script(remote, values), timeout=timeout)
