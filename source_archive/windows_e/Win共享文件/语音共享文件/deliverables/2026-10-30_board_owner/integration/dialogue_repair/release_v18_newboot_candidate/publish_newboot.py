"""Pinned recovery publisher for the observed new boot. Default is local dry-run.

The PREPARE spec can only add the no-force guard to an ownerless failed unit.
The APPLIED spec binds every installed source before normal start or WM_DELETE.
No candidate source, private readback or production database is written here.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import time


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
INTEGRATION = REPAIR.parent
PROJECT = INTEGRATION.parents[2]
NEW_BOOT = 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
OLD_BOOT = '8100a7fd-0c6a-46c4-82b8-f874988a1521'
BASE_STARTUP = '12a26c81167ecee7293d0d9be77ec7834894d413f07bab6d8a27e4c8cdfe0392'
BASE_MANIFEST = 'f694dd48a7bcf2cf4fcbfaf8453e421038b5251d209c75490021d03e2f7e373a'
BASE_CONFIG = 'd2511ee2b95f0ae9b2cbb18f16cde90719420d887e858926e8fd07a5c5b60013'
BASE_REMOTE_SHA = '9ee138be727aa6f37d97e57dfdc2bf6a40ec9982642f5e80625b686ce5cf0363'
MAPPING_SHA = '7bdbc34c502a0ea6f6126cc07d4ed0a029b6e5a09c50203cd98a7d18ced79d56'
DIAGNOSTIC_SHA = 'eeef33656e49988413100185c82871386ccd9bc4f9a9a4e727148fc2f05f4558'
HELPER_SHA = '56952b2a5950611a28a6e236180125d2bb18c0acc5ba043e2bf039112670cdcd'
OLD_READBACK = '/home/root/aura-board-owner-candidate-20261030/private-pin-8100a7fd-restored260102-20261030/face_gallery_readback.local.json'
OLD_READBACK_SHA = '8c0d859d22bf723fb2afdf503b1e9c9a7eb858d784e68d85a3c71560bd1e1e6b'
TARGET = '/home/root/aura-board-business-20261030/production-5259eab11e42af13'
STAGE = 'response-latency-v18-memory-recall'
ALLOWED_OVERRIDES = {
    'common/board_production_bootstrap.py',
    'board/runtime/board_business.py',
    'tools/production_board_business_gui.py',
    'tools/board_avatar_gtk.py',
    'tools/x11_display_activity.py',
}
ACTIONS = ('guard-failed', 'guard', 'window-inspect', 'normal-close', 'start', 'ready')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def pinned(path, expected):
    path = Path(path)
    raw = path.read_bytes()
    if path.is_symlink() or path.resolve() != path or sha(raw) != expected:
        raise ValueError('pinned_local_source_changed')
    return raw


def inputs():
    mapping = json.loads(pinned(REPAIR / 'release_v18_candidate/v18_evidence/source_mapping.json', MAPPING_SHA))
    diagnostic = json.loads(pinned(REPAIR / 'progress_followup_20261031/new_boot_diagnostic_1793494742376142600.json', DIAGNOSTIC_SHA))
    old_startup = json.loads(diagnostic['files']['startup/config.json']['content'])
    old_gui = json.loads(diagnostic['files']['runtime/aura/config/board_avatar_gtk.json']['content'])
    assert mapping['startup_sha256'] == BASE_STARTUP
    assert len(mapping['component_pins']) == 379
    assert old_startup['component_sha256'] == mapping['component_pins']
    assert old_gui['board_business']['face_readback'] == {'path': OLD_READBACK, 'sha256': OLD_READBACK_SHA}
    return mapping['component_pins'], old_startup, old_gui


def validate_spec(spec, action):
    pins, old_startup, old_gui = inputs()
    if (spec.get('boot_id') != NEW_BOOT or spec.get('target') != TARGET
            or spec.get('previous_boot_id') != OLD_BOOT or spec.get('component_pins') != 379
            or spec.get('release_stage') != STAGE or spec.get('retention_enabled') is not True
            or spec.get('automatic_listening') is not True or spec.get('wake_word_required') is not False
            or spec.get('conversation_mode') != 'half_duplex'
            or spec.get('expected_final_listening_enabled') is not True
            or spec.get('native_library_sha256') != pins['tools/libaura_yuki.so']
            or spec.get('character_pair_selection_sha256') != pins['config/yuki_pair.formal.json']):
        raise ValueError('exact_new_boot_board_policy_required')
    phase = spec.get('new_boot_state')
    if phase not in ('PREPARE', 'APPLIED') or (action == 'guard-failed') != (phase == 'PREPARE'):
        raise ValueError('prepare_guard_or_applied_publication_required')
    owner = spec.get('camera_owner', {})
    if (set(owner) != {'board_boot_id', 'camera_pid', 'camera_start_ticks', 'camera_cmdline_sha256'}
            or owner.get('board_boot_id') != NEW_BOOT or owner.get('camera_pid') != 1335
            or owner.get('camera_start_ticks') != '2344'
            or not re.fullmatch('[a-f0-9]{64}', str(owner.get('camera_cmdline_sha256', '')))):
        raise ValueError('reviewed_fresh_camera_owner_required')
    face = spec.get('face_readback', {})
    prefix = '/home/root/aura-board-owner-candidate-20261030/'
    if (set(face) != {'path', 'sha256'} or not isinstance(face['path'], str)
            or not face['path'].startswith(prefix) or '..' in face['path'].split('/')
            or not face['path'].endswith('/face_gallery_readback.local.json')
            or face['path'] == OLD_READBACK or not re.fullmatch('[a-f0-9]{64}', str(face['sha256']))):
        raise ValueError('new_private_readback_reference_required')
    changes = spec.get('source_overrides', {})
    if not isinstance(changes, dict) or not set(changes) <= ALLOWED_OVERRIDES:
        raise ValueError('unreviewed_source_override')
    expected_pins = dict(pins)
    for rel, row in changes.items():
        if set(row) != {'before_sha256', 'sha256', 'local_source'} or row['before_sha256'] != pins[rel]:
            raise ValueError('source_override_baseline_changed')
        raw = pinned(row['local_source'], row['sha256'])
        ast.parse(raw, feature_version=(3, 9))
        expected_pins[rel] = row['sha256']
    if phase == 'PREPARE':
        if changes or (spec['startup_sha256'], spec['source_manifest_sha256'], spec['configuration_sha256']) != (BASE_STARTUP, BASE_MANIFEST, BASE_CONFIG):
            raise ValueError('prepare_requires_unmodified_v18_sources')
    else:
        gui = copy.deepcopy(old_gui)
        gui['board_business']['face_readback'] = face
        cfg_sha = sha(encoded(gui))
        expected_pins['config/board_avatar_gtk.json'] = cfg_sha
        startup = copy.deepcopy(old_startup)
        startup['component_sha256'] = expected_pins
        if (spec.get('configuration_sha256') != cfg_sha or spec.get('startup_sha256') != sha(encoded(startup))
                or not re.fullmatch('[a-f0-9]{64}', str(spec.get('source_manifest_sha256', '')))):
            raise ValueError('only_reviewed_face_and_source_changes_allowed')
    if spec.get('component_sha256') != expected_pins:
        raise ValueError('complete_379_component_mapping_required')
    return spec


NEW_HELPERS = r'''
def reviewed_face():
 helper_namespace={'__name__':'_read_only_newboot_helper'}
 exec(compile(READBACK_HELPER,'<pinned-newboot-helper>','exec'),helper_namespace)
 reader=helper_namespace['LiveReader']()
 previous=c.parse(c.read(OLD_FACE_PATH,OLD_FACE_SHA))
 candidate,report=helper_namespace['build_candidate'](previous,reader,
   expected_boot=SPEC['boot_id'],expected_pid=SPEC['camera_owner']['camera_pid'])
 need(report['ready'] is True and report['owner']==SPEC['camera_owner'],'fresh_readback_owner_changed')
 face=SPEC['face_readback'];path=Path(face['path'])
 need(reader.private_metadata(str(path)) and path.parent.stat().st_mode&0o077==0,'private_readback_mode_required')
 need(c.read(path,face['sha256'])==helper_namespace['candidate_bytes'](candidate),'reviewed_readback_changed')
 return report

def source():
 root=Path(SPEC['target'])
 need(root==Path(EXACT_TARGET) and root.resolve()==root,'exact_production_root_required')
 startup=c.parse(c.read(root/'startup/config.json',SPEC['startup_sha256']))
 need(startup['runtime']==str(root/'runtime') and startup['component_sha256']==SPEC['component_sha256'],'complete_source_config_changed')
 for rel,pin in startup['component_sha256'].items():c.read(root/'runtime/aura'/c.relative(rel),pin)
 manifest=c.parse(c.read(root/'production_source_manifest.json',SPEC['source_manifest_sha256']))
 need(manifest['component_pins']==startup['component_sha256'],'manifest_source_closure_changed')
 gui=c.parse(c.read(root/'runtime/aura/config/board_avatar_gtk.json',SPEC['configuration_sha256']))
 need(gui==EXPECTED_GUI,'reviewed_gui_configuration_changed')
 need(startup==EXPECTED_STARTUP,'reviewed_launcher_configuration_changed')
 need(startup['component_sha256']['tools/libaura_yuki.so']==NATIVE_SHA,'reviewed_native_changed')
 need(startup['component_sha256']['config/yuki_pair.formal.json']==PAIR_SHA,'reviewed_pair_changed')
 c.read(root/'startup/launcher.py','5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03')
 reviewed_face()
 return root

def ownerless(u):
 need(u['MainPID']=='0' and u['ActiveState'] in ('failed','inactive') and not u.get('Job'),'ownerless_failed_or_inactive_unit_required')
 for item in Path('/proc').iterdir():
  if not item.name.isdigit():continue
  try:raw=(item/'cmdline').read_bytes()
  except FileNotFoundError:continue
  need(len(raw)<=1048576,'bounded_proc_command_required')
  args=raw.split(b'\0')
  need(not any(a.endswith((b'/board_avatar_pan.py',b'/board_avatar_gtk.py')) for a in args),'another_gtk_owner_exists')
  need(str(Path(EXACT_TARGET)/'startup/launcher.py').encode() not in args,'another_supervisor_exists')
 import socket
 with socket.socket() as sock:
  sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
  sock.bind(('127.0.0.1',8783))

def writer_and_ui_leases_free():
 with open('/run/aura-avatar-ui.lock','a') as ui_lock,open('/home/root/.local/share/aura-board-business/writer.lock','a') as writer_lock:
  fcntl.flock(ui_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  fcntl.flock(writer_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)

def guard_failed():
 boot();source();j=journal();u=c.show();ownerless(u)
 need(j.get('active_root')==EXACT_TARGET,'production_journal_root_changed')
 if j.get('phase')=='NEW_BOOT_OWNERLESS' and j.get('boot_id')==SPEC['boot_id']:
  need(j.get('guard_removed') is False,'newboot_guard_state_changed')
  guarded(j)
  return dict(status='NEW_BOOT_ALREADY_GUARDED_OWNERLESS',boot_id=SPEC['boot_id'])
 need(j.get('phase')=='COMMITTED' and j.get('guard_removed') is True and j.get('boot_id')==PREVIOUS_BOOT,'previous_committed_boot_required')
 need(u['DropInPaths']==j['final_dropins'],'committed_dropins_changed')
 need(c.exec_argv(u['ExecStart'])==' '.join(argv(Path(EXACT_TARGET))),'production_exec_not_selected')
 for key in ('Restart','SendSIGKILL','TimeoutStopUSec'):
  need(u[key]==j['original_properties'][key],'previous_stop_policy_changed')
 for path,pin in j['original_unit_sha256'].items():c.read(path,pin)
 c.read(j['persistent'],j['persistent_sha256'])
 guard_path=Path(j['guard'])
 need(str(guard_path).startswith('/run/systemd/system/aura-avatar-ui.service.d/') and not guard_path.exists(),'new_boot_guard_must_be_absent')
 raw=bytes.fromhex(j['guard_hex']);need(c.sha(raw)==j['guard_sha256'],'guard_bytes_changed')
 private=Path('/home/root/.local/share/aura-board-business')
 with open('/run/aura-avatar-ui.lock','a') as ui_lock,open(private/'writer.lock','a') as writer_lock:
  fcntl.flock(ui_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  fcntl.flock(writer_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  ownerless(c.show());boot()
  backup=CONTROL/('before-newboot-'+SPEC['boot_id']+'.json')
  previous=c.read(STATE)
  if backup.exists():c.read(backup,c.sha(previous))
  else:c.create(backup,previous)
  guard_path.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
  c.create(guard_path,raw)
  j.update(previous_boot_id=PREVIOUS_BOOT,boot_id=SPEC['boot_id'],previous_journal_sha256=c.sha(previous),
    guard_removed=False,phase='NEW_BOOT_OWNERLESS',closing=None)
  save(j);c.command(['/bin/systemctl','daemon-reload']);guarded(j)
 return dict(status='NEW_BOOT_GUARDED_OWNERLESS',boot_id=SPEC['boot_id'],forced_action=False)
'''


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('unique_frozen_anchor_required')
    return source.replace(old, new)


def build_remote(spec=None):
    remote = pinned(REPAIR / 'release_v18_candidate/FROZEN_PUBLISH_REMOTE.py', BASE_REMOTE_SHA).decode()
    remote = replace_once(remote, "assert ACTION in ('guard','window-inspect','normal-close','start','ready')", "assert ACTION in ('guard-failed','guard','window-inspect','normal-close','start','ready')")
    original_tree = ast.parse(remote)
    old_source = next(node for node in original_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'source')
    lines = remote.splitlines(keepends=True)
    lines[old_source.lineno - 1:old_source.end_lineno] = [NEW_HELPERS + '\n']
    remote = ''.join(lines)
    anchor = "p=c.parse(c.read(TOOLS+'/policy.json','b550e2a2307d97b52ba598a9e992f96ecacb53de05babf438d551a942de2996d'))"
    remote = replace_once(remote, anchor, anchor + "\np=dict(p,boot_id=SPEC['boot_id'],camera={'pid':SPEC['camera_owner']['camera_pid'],'birth':SPEC['camera_owner']['camera_start_ticks'],'cmdline_sha256':SPEC['camera_owner']['camera_cmdline_sha256']})")
    remote = replace_once(remote, " need(u['MainPID']=='0' and u['ActiveState']=='inactive','ownerless_unit_required')", " need(u['MainPID']=='0' and u['ActiveState'] in ('inactive','failed'),'ownerless_unit_required')\n ownerless(u);writer_and_ui_leases_free()")
    remote = replace_once(remote, " if ACTION=='guard':result=guard()", " if ACTION=='guard-failed':result=guard_failed()\n elif ACTION=='guard':result=guard()")
    pins, startup, gui = inputs()
    if spec is not None and spec['new_boot_state'] == 'APPLIED':
        startup['component_sha256'] = spec['component_sha256']
        gui['board_business']['face_readback'] = spec['face_readback']
    helper = pinned(INTEGRATION / 'resume_camera_pin/rebuild_face_readback_pin.py', HELPER_SHA).decode()
    constants = dict(PREVIOUS_BOOT=OLD_BOOT, EXACT_TARGET=TARGET, OLD_FACE_PATH=OLD_READBACK,
        OLD_FACE_SHA=OLD_READBACK_SHA, READBACK_HELPER=helper, EXPECTED_STARTUP=startup, EXPECTED_GUI=gui)
    remote = '\n'.join(key + '=' + repr(value) for key, value in constants.items()) + '\n' + remote
    ast.parse(remote, feature_version=(3, 9))
    return remote


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=ACTIONS)
    parser.add_argument('--spec', type=Path)
    parser.add_argument('--spec-sha256')
    parser.add_argument('--window-proof', type=Path)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    spec = None
    if args.spec:
        if not re.fullmatch('[a-f0-9]{64}', args.spec_sha256 or ''):
            parser.error('--spec-sha256 is required with --spec')
        spec = validate_spec(json.loads(pinned(args.spec, args.spec_sha256)), args.action)
    remote = build_remote(spec)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_SOURCE_VALIDATED_NO_SSH',action=args.action,
            remote_sha256=sha(remote.encode()),complete_spec_exists=spec is not None)))
        return
    if spec is None:
        parser.error('--spec and --spec-sha256 are required for execution')
    values = dict(SPEC=spec, ACTION=args.action, TOKEN=None, WINDOW=None)
    if args.action == 'normal-close':
        if args.window_proof is None:
            parser.error('--window-proof is required for normal-close')
        proof = json.loads(args.window_proof.read_bytes())
        assert proof['status'] == 'WINDOW_INSPECTED_NO_CLOSE'
        values.update(TOKEN=proof['review_token'], WINDOW=proof['window']['window_id'])
    # Only this explicit root branch imports the existing SSH transport.
    sys.path.insert(0, str(REPAIR / 'release_v18_candidate'))
    from v18_common import publisher_script, ssh_json
    result = ssh_json(publisher_script(remote, values), timeout=225)
    target = HERE / ('actual_' + args.action + '_' + str(time.time_ns()) + '.json')
    with target.open('xb') as output:
        output.write(encoded(result))
    print(json.dumps(dict(output=str(target),result=result),ensure_ascii=True))


if __name__ == '__main__':
    main()
