"""Local two-file candidate from exact v20 source and GUI configuration bytes."""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[1]
V20 = REPAIR/'release_v20_identity_history_candidate'
GTK = REPAIR/'release_v19_stability_candidate/payload/tools/board_avatar_gtk.py'
GTK_SHA = '7ed7a72fb16e92ed548d524cbd06c1b6b1b2d74798d0212e9be12efa6bd109b9'
CONFIG_SHA = '5518b6705083eb9e2fae7e19a47c003182995fe8660cbc6031860c9905da9786'
PUBLISHER_SHA = '03726f874bccf9a9176257c0cd7de6412cab4fa02e5da17da7c91a17d1c0fa0b'
MAP_SHA = 'a7141992428e47d49ef80828ce9a0b33df6bffe32b613343ba01f937f68fdafc'
SPEC_SHA = 'cd67e77691b415d8133015911806c98aaf328feed44945e492c8b0cd421099c7'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')


def write_json(name, value):
    (HERE/name).write_bytes(encoded(value))


mapping_raw = (V20/'identity_history_evidence/source_mapping.json').read_bytes()
spec_raw = (V20/'identity_history_evidence/spec.json').read_bytes()
assert sha(mapping_raw) == MAP_SHA and sha(spec_raw) == SPEC_SHA
mapping, spec = json.loads(mapping_raw), json.loads(spec_raw)
assert mapping['component_pins'] == spec['component_sha256']
assert len(mapping['component_pins']) == 380
assert spec['expected_final_listening_enabled'] is False
before_gtk = GTK.read_bytes()
assert sha(before_gtk) == GTK_SHA == mapping['component_pins']['tools/board_avatar_gtk.py']
publisher_raw = (V20/'FROZEN_PUBLISH_STABILITY_REMOTE.py').read_bytes()
assert sha(publisher_raw) == PUBLISHER_SHA
tree = ast.parse(publisher_raw)
gui_node = next(node for node in tree.body if isinstance(node,ast.Assign)
                and any(isinstance(target,ast.Name) and target.id=='EXPECTED_GUI' for target in node.targets))
gui = ast.literal_eval(gui_node.value)
before_config = encoded(gui)
assert sha(before_config) == CONFIG_SHA == mapping['component_pins']['config/board_avatar_gtk.json']
assert gui['board_business']['asr_threads'] == 3
assert before_config.count(b'"asr_threads": 3') == 1
after_config = before_config.replace(b'"asr_threads": 3',b'"asr_threads": 2')
after_gui = json.loads(after_config)
expected_gui = copy.deepcopy(gui)
expected_gui['board_business']['asr_threads'] = 2
assert after_gui == expected_gui
assert after_config.replace(b'"asr_threads": 2',b'"asr_threads": 3') == before_config
assert sum(a != b for a,b in zip(before_config,after_config)) == 1

old = """        self.display_activity.tick(bool(handsfree.get('enabled')
                                       or automatic.get('enabled') or state.get('playing')))
"""
new = """        board_owned = (getattr(self,'board_business',None) is not None
                       and self.board_business.runtime.config.data_origin == 'board')
        self.display_activity.tick(bool(board_owned or handsfree.get('enabled')
                                       or automatic.get('enabled') or state.get('playing')))
"""
text = before_gtk.decode('utf-8')
newline = '\r\n' if '\r\n' in text else '\n'
old, new = old.replace('\n',newline), new.replace('\n',newline)
assert text.count(old) == 1
updated = text.replace(old,new)
assert updated.replace(new,old).encode('utf-8') == before_gtk
ast.parse(updated,feature_version=(3,9))
after_gtk = updated.encode('utf-8')
files = {'tools/board_avatar_gtk.py':(before_gtk,after_gtk),
         'config/board_avatar_gtk.json':(before_config,after_config)}
manifest = dict(schema='aura.v20-paused-display-asr2.candidate.v1',
    status='LOCAL_ONLY_NOT_DEPLOYED',baseline_startup_sha256=spec['startup_sha256'],
    baseline_spec_sha256=SPEC_SHA,baseline_mapping_sha256=MAP_SHA,
    baseline_component_count=380,expected_component_count=380,
    expected_listening_enabled=False,files={})
diffs = []
for relative,(before,after) in files.items():
    for folder,raw in [('before',before),('after',after)]:
        path = HERE/folder/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
    manifest['files'][relative] = dict(before_sha256=sha(before),sha256=sha(after),bytes=len(after),
                                     source=str(HERE/'after'/relative))
    diffs.extend(difflib.unified_diff(before.decode('utf-8').splitlines(True),after.decode('utf-8').splitlines(True),
        fromfile='before/'+relative,tofile='after/'+relative))
(HERE/'CANDIDATE.diff').write_text(''.join(diffs),encoding='utf-8')
write_json('SOURCE_MANIFEST.json',manifest)
comparison = REPAIR/'performance_review_newboot/asr_threads_v20_r2/ACTUAL_COMPARISON_01.json'
evidence = json.loads(comparison.read_bytes())
assert evidence['all_normalized_results_equal'] is True
assert evidence['aggregates']['2']['mean_decode_wall_ms'] < evidence['aggregates']['3']['mean_decode_wall_ms']
write_json('REVERSIBLE_PROOF.json',dict(
    gtk_only_existing_refresh_predicate_changed=True,gtk_reverse_bytes_match=True,
    original_DisplayActivity_sha256=mapping['component_pins']['tools/x11_display_activity.py'],
    existing_wake_interval_seconds=5,new_threads=0,new_timers=0,
    configuration_reconstructed_from_exact_frozen_publisher_sha256=PUBLISHER_SHA,
    baseline_configuration_sha256=CONFIG_SHA,configuration_single_byte_change=True,
    configuration_only_leaf_change='board_business.asr_threads',before_threads=3,after_threads=2,
    configuration_reverse_bytes_match=True,unchanged_component_count=378,
    runtime_resources_model_paths_and_persona_config_preserved=True,
    asr_public_evidence_path=str(comparison),asr_public_evidence_sha256=sha(comparison.read_bytes()),
    background_counter_changed=evidence['background_counter_changed'],causal_whole_system_gain_claimed=False))
write_json('HANDOFF.json',dict(schema='aura.v20-paused-display-asr2.handoff.v1',
    status='LOCAL_CANDIDATE_PENDING_TESTS',files=manifest['files'],
    baseline_startup_sha256=spec['startup_sha256'],baseline_configuration_sha256=CONFIG_SHA,
    expected_listening_enabled=False,
    release_order='root finishes frontend probe bound to v20/config5518 before any publication',
    publication_required='normal guarded close/apply/start/ready/seal, with GUI configuration closure',
    configuration_closure_required=['runtime/aura/config/board_avatar_gtk.json',
        'production_source_manifest.configuration_path and configuration_sha256',
        'production_source_manifest.files and component_pins',
        'startup/config.json configuration_sha256 and component_sha256',
        'publication spec configuration_sha256 and component map',
        'EXPECTED_GUI and EXPECTED_STARTUP before source()/ready() checks'],
    frozen_v20_source_only_publisher_cannot_apply_configuration_directly=True,
    real_device_model_or_private_database_access=False))
print(json.dumps(dict(status='TWO_FILE_LOCAL_CANDIDATE',files=manifest['files'],
                      manifest_sha256=sha((HERE/'SOURCE_MANIFEST.json').read_bytes()))))
