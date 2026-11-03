"""Create new root-only GUI start and metadata readers from reviewed originals."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]
precheck = (HERE/'collect_gui_binding_precheck25.py').read_text(encoding='utf-8')
tree = ast.parse(precheck)
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'platform')
platform_source = ast.get_source_segment(precheck, node) + '\n\n'
dry = json.loads((HERE/'TRANSACTION25_DRYRUN.json').read_text(encoding='utf-8'))['board_result']
assert dry['new_selected_sha256'] == '9ab2533d2c3000d61095f54de2e8199f53461ac085e2f58230ab36149be6af1f'

start_original = OUT/'identity_dialogue_review/restart_v2_review/start_gui_after_identity_query_v2.py'
start = start_original.read_text(encoding='utf-8')
assert hashlib.sha256(start_original.read_bytes()).hexdigest() == '06c03cb4d0cd880d5da9641a814f148674395506f7d8636f325d39ac7d52030c'
replacements = {
    "STARTUP_SHA='0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'": "STARTUP_SHA='" + dry['startup_after_sha256'] + "'",
    "SELECTED_SHA='4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'": "SELECTED_SHA='" + dry['new_selected_sha256'] + "'",
    '1333': '79866',
    '2359': '2265436',
    "len(binding['source_sha256'])==24": "len(binding['source_sha256'])==25",
    "'selected_sources_verified':24": "'selected_sources_verified':25",
    "'benchmark_fdt_verified':True": "'wide_platform_verified':True",
}
for before, after in replacements.items():
    assert before in start, before
    start = start.replace(before, after)
anchor = 'def guard():\n'
assert start.count(anchor) == 1
start = start.replace(anchor, platform_source + anchor)
inline = """    assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\\0')==b'kv260-benchmark-b4096.bit.bin'
    assert hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest()=='d68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca'
    assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
"""
assert start.count(inline) == 1
start = start.replace(inline, '    platform()\n')
ui_anchor = "    ui=json.loads(raw(aura/'config/board_avatar_gtk.json'))\n"
assert start.count(ui_anchor) == 1
start = start.replace(ui_anchor, "    assert digest(aura/'config/board_avatar_gtk.json')=='" + dry['ui_after_sha256'] + "'\n    assert digest(aura/'config/face_gallery_readback.local.json')=='e203e6ffe973397464791eb07f12e0bd0c24658988c119e9d7d75685c4e41986'\n" + ui_anchor)
start = start.replace("'schema':'aura-gui-normal-start-request-1'", "'schema':'aura-gui-restored-camera-normal-start-request-2'")

observer_original = OUT/'parallel_platform/gui_startup_review/collect_gui_post_start_metadata.py'
observer = observer_original.read_text(encoding='utf-8')
replacements = {
    "STARTUP_SHA='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'": "STARTUP_SHA='" + dry['startup_after_sha256'] + "'",
    "UI_SHA='fc21e6f2ef831442b08966957fa7aeb744a9b74124ee8778edc40397285626cd'": "UI_SHA='" + dry['ui_after_sha256'] + "'",
    'gui-selected-1333-24pins-v1': 'gui-selected-79866-25pins-v1',
    "SELECTED_SHA='4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'": "SELECTED_SHA='" + dry['new_selected_sha256'] + "'",
    '1333': '79866',
    '2359': '2265436',
    "len(binding['source_sha256'])==24": "len(binding['source_sha256'])==25",
    "'selected_source_files_verified':24": "'selected_source_files_verified':25",
    'kv260-benchmark-b4096.bit.bin': 'aura-visual-servo-b4096-wide-v1.bit.bin',
    'mechanical_guard_keeps_connection_unavailable': 'old_axis_context_guard_keeps_connection_unavailable',
    'GUI_SOFTWARE_READY_PAUSED_PLATFORM_LOCKED': 'GUI_SOFTWARE_READY_PAUSED_OLD_AXIS_CONTEXT_LOCKED',
    'aura-gui-post-start-filtered-metadata-1': 'aura-gui-restored-camera-post-start-filtered-metadata-2',
}
for before, after in replacements.items():
    assert before in observer, before
    observer = observer.replace(before, after)
anchor = "assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\n"
assert observer.count(anchor) == 1
observer = observer.replace(anchor, platform_source + 'platform()\n' + anchor)

manifest = {'schema': 'aura-restored-gui-start-observer-local-review-1',
            'board_or_service_actions_executed': False, 'startup_sha256': dry['startup_after_sha256'],
            'ui_sha256': dry['ui_after_sha256'], 'selected_binding_sha256': dry['new_selected_sha256'],
            'camera_owner': {'pid': 79866, 'birth_ticks': '2265436', 'command_sha256': 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'},
            'old_axis_configs_preserved_and_expected_fail_closed': True, 'files': {}}
for name, source in (('start_gui_after_restored_binding25.py', start), ('collect_gui_after_restored_binding25.py', observer)):
    tree = ast.parse(source)
    starts = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'run'
              and any(isinstance(k, ast.Constant) and k.value == 'start' for arg in n.args for k in ast.walk(arg))]
    assert len(starts) == (1 if name.startswith('start_') else 0)
    target = HERE/name
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(source)
    manifest['files'][name] = {'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'normal_gui_start_calls': len(starts)}
wait = OUT/'identity_dialogue_review/restart_v2_review/wait_for_gui_ready_90.py'
assert hashlib.sha256(wait.read_bytes()).hexdigest() == '1876cd91c638ef8c0115861d86061ab0bfd90bfce7049c55619ef5cbdd95fa28'
manifest['unchanged_wait_90_seconds'] = {'path': str(wait), 'sha256': hashlib.sha256(wait.read_bytes()).hexdigest()}
with (HERE/'START_OBSERVER_REVIEW.json').open('x', encoding='utf-8') as stream:
    json.dump(manifest, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(manifest, ensure_ascii=True))
