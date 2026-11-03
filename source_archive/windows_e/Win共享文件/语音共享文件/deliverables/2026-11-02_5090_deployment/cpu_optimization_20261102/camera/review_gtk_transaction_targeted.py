"""Local, isolated cross-review probes. Never import the GTK transaction main.

No native Linux/board execution is claimed: the permission check uses an explicit
POSIX open(mode & ~umask) model and the exact AST-extracted replace_target helper.
The closure check exercises the actual closure function with public synthetic
files, while service/selected acquisition is deliberately stubbed.
"""
import ast
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat

HERE = Path(__file__).resolve().parent
GTK = HERE.parent / 'gtk' / 'v2'
SOURCE = (GTK / 'transaction_preview_projection.py').read_bytes()
TREE = ast.parse(SOURCE)


class VPath(PurePosixPath):
    def resolve(self, *args, **kwargs):
        return self


NAMES = {'require', 'sha', 'sha_value', 'json_bytes', 'startup_after',
         'replace_target', 'check_closure', 'validate_rel'}
NODES = [node for node in TREE.body
         if isinstance(node, ast.ClassDef) and node.name == 'Hold'
         or isinstance(node, ast.FunctionDef) and node.name in NAMES
         or isinstance(node, ast.Assign) and any(
             isinstance(target, ast.Name) and target.id in ('TARGETS', 'OLD', 'NEW')
             for target in node.targets)]
SPACE = dict(copy=copy, json=json, hashlib=hashlib, Path=VPath, re=re)
exec(compile(ast.Module(body=NODES, type_ignores=[]), '<GTK-cross-review-functions>', 'exec'), SPACE)


class PosixModel:
    O_RDONLY = 0
    O_NOFOLLOW = 0x20000

    def __init__(self, umask):
        self.umask = umask
        self.files = {}
        self.serial = 0
        self.descriptors = {}

    def put(self, path, data, mode=0o644, uid=0, gid=0):
        self.serial += 1
        self.files[str(path)] = [data, (1, self.serial, len(data), self.serial, mode, uid, gid)]

    def read_file(self, path):
        data, identity = self.files[str(path)]
        return data, identity

    def create(self, path, data, mode=0o600):
        assert str(path) not in self.files
        self.put(path, data, mode & ~self.umask)

    def chown(self, path, uid, gid):
        data, identity = self.files[str(path)]
        # Linux chown can also clear setid bits. Normal source modes below do
        # not use them; preserving mode after chown still needs fchmod.
        self.files[str(path)] = [data, identity[:4] + (identity[4] & ~0o6000, uid, gid)]

    def open(self, path, flags):
        assert str(path) in self.files
        descriptor = len(self.descriptors) + 1
        self.descriptors[descriptor] = str(path)
        return descriptor

    def fchmod(self, descriptor, mode):
        path = self.descriptors[descriptor]
        data, identity = self.files[path]
        self.files[path] = [data, identity[:4] + (mode,) + identity[5:]]

    def fsync(self, descriptor):
        pass

    def close(self, descriptor):
        del self.descriptors[descriptor]

    def replace(self, source, destination):
        self.files[str(destination)] = self.files.pop(str(source))


def setup_model(umask):
    model = PosixModel(umask)
    SPACE.update(os=model, read_file=model.read_file, create=model.create,
                 fsync_dir=lambda path: None)

    def pinned(path, digest):
        raw, identity = model.read_file(path)
        SPACE['require'](SPACE['sha'](raw) == digest, 'HOLD_PIN_MISMATCH:' + str(path))
        return raw, identity

    SPACE['pinned'] = pinned
    return model


def probe_permission_case(umask, original_mode):
    model = setup_model(umask)
    target = VPath('/synthetic/runtime/aura/board/interaction/ui_services.py')
    before, after = b'public before\n', b'public after\n'
    model.put(target, before, original_mode)
    context = {'identities': {str(target): model.read_file(target)[1]}}
    SPACE['replace_target'](context, target, before, after, 'isolated')
    raw, actual_identity = model.read_file(target)
    assert raw == after and context['identities'][str(target)] == actual_identity
    return dict(umask=oct(umask), original_mode=oct(original_mode),
                resulting_mode=oct(actual_identity[4]),
                helper_returned_success=True,
                context_accepts_new_identity=True,
                mode_preserved=actual_identity[4] == original_mode)


def probe_known_partial_closure():
    model = setup_model(0o022)
    aura = VPath('/synthetic/current-runtime/aura')
    startup_path = VPath('/synthetic/current-startup/config.json')
    payload = json.loads((GTK / 'transaction_payload.json').read_bytes())
    targets = SPACE['TARGETS']
    old_bytes = {name: (GTK / 'original' / name).read_bytes() for name in targets}
    new_bytes = {name: base64.b64decode(payload['components'][name]['new_bytes_base64'], validate=True)
                 for name in targets}
    for name in targets:
        assert SPACE['sha'](old_bytes[name]) == SPACE['OLD'][name]
        assert SPACE['sha'](new_bytes[name]) == SPACE['NEW'][name]
    pins = {}
    for index in range(376):
        name = 'public/component-%03d.txt' % index
        raw = ('public synthetic component %s\n' % index).encode()
        model.put(aura / name, raw)
        pins[name] = SPACE['sha'](raw)
    later_identity_name = 'tools/unified_identity_binding.py'
    later_identity_raw = b'public synthetic later identity module\n'
    contract_name = 'board/interaction/ui_contract.py'
    contract_raw = (GTK / 'original' / contract_name).read_bytes()
    for name, raw in ((later_identity_name, later_identity_raw), (contract_name, contract_raw)):
        model.put(aura / name, raw)
        pins[name] = SPACE['sha'](raw)
    for name in targets:
        pins[name] = SPACE['OLD'][name]
        model.put(aura / name, new_bytes[name] if name == targets[0] else old_bytes[name])
    assert len(pins) == 380
    startup = {'runtime': '/synthetic/current-runtime', 'component_sha256': pins,
               'later_identity_metadata': {'revision': 'public-later-current'}}
    raw = SPACE['json_bytes'](startup)
    model.put(startup_path, raw)
    camera = {'pid': 7707, 'birth_ticks': '424242', 'command_sha256': 'e' * 64}
    expected = {'boot_id': 'c7cf9664-c657-4e6a-bf03-115ff53db402', 'owners': {'camera': camera},
                'pan_external_sha256': {}, 'selected_readback_sha256': 'f' * 64,
                'selected_readback_source_count': 26}
    binding = {'sha256': expected['selected_readback_sha256'], 'source_count': 26,
               'ids': {}, 'binding': {'board_boot_id': expected['boot_id'],
                   'camera_pid': camera['pid'], 'camera_start_ticks': int(camera['birth_ticks']),
                   'camera_cmdline_sha256': camera['command_sha256']}}
    SPACE['guards'] = lambda value: None
    SPACE['selected_readback'] = lambda *args: binding
    context = {'expected': expected, 'aura': aura, 'startup_path': startup_path,
               'startup_raw': raw, 'startup': startup, 'pins': pins,
               'identities': {str(startup_path): model.read_file(startup_path)[1]}}
    active = dict(SPACE['OLD'])
    active[targets[0]] = SPACE['NEW'][targets[0]]
    SPACE['check_closure'](context, overrides=active, first=True)
    SPACE['replace_target'](context, aura / targets[0], new_bytes[targets[0]], old_bytes[targets[0]], 'rollback-isolated')
    active[targets[0]] = SPACE['OLD'][targets[0]]
    SPACE['check_closure'](context, overrides=active)
    final_raw = SPACE['startup_after'](startup, SPACE['OLD'])
    SPACE['replace_target'](context, startup_path, raw, final_raw, 'rollback-isolated')
    SPACE['check_closure'](context, overrides=active, startup_bytes=final_raw)
    result = json.loads(final_raw)
    assert result['component_sha256'][later_identity_name] == SPACE['sha'](later_identity_raw)
    assert result['later_identity_metadata'] == startup['later_identity_metadata']
    return {'pass': True, 'closure_component_count': 380, 'selected_source_count': 26,
            'first_target_new_second_target_old_startup_both_old': True,
            'known_partial_rollback_closure_accepted': True,
            'later_identity_source_and_metadata_preserved': True,
            'real_guards_and_selected_acquisition_stubbed': True,
            'preflight_main_or_live_linux_not_executed': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode-fix-only', action='store_true')
    args = parser.parse_args()
    if args.mode_fix_only:
        archive = HERE.parent / 'transaction_root_hardening' / 'transaction_preview_projection.py.before.bin'
        prior_source = archive.read_bytes()
        before_tree = ast.parse(prior_source)
        remaining = lambda tree: [ast.dump(node, include_attributes=False) for node in tree.body
                                  if not (isinstance(node, ast.FunctionDef) and node.name == 'replace_target')]
        assert remaining(before_tree) == remaining(TREE), 'Unexpected AST change outside replace_target'
        cases = [probe_permission_case(0o077, 0o644), probe_permission_case(0o077, 0o755)]
        assert all(case['mode_preserved'] for case in cases)
        output = {'script_sha256': hashlib.sha256(SOURCE).hexdigest(),
                  'prior_script_sha256': hashlib.sha256(prior_source).hexdigest(),
                  'only_replace_target_ast_changed': True,
                  'probe_kind': 'exact patched helper with explicit POSIX permission model',
                  'permission_cases': cases, 'mode_fix_verified_in_model': True,
                  'prior_partial_closure_not_rerun': True,
                  'previous_probe_evidence': 'GTK_TRANSACTION_TARGETED_PROBES.before_mode_fix.json',
                  'existing_tests_rerun': False, 'transaction_main_imported_or_run': False,
                  'board_network_or_services_contacted': False,
                  'gtk_files_modified_by_reviewer': False, 'native_linux_execution': False}
        (HERE / 'GTK_TRANSACTION_TARGETED_PROBES.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return
    permission_cases = [probe_permission_case(0o077, 0o644), probe_permission_case(0o022, 0o755)]
    assert permission_cases[0]['mode_preserved'] is False
    assert permission_cases[1]['mode_preserved'] is True
    binding_path = HERE.parent.parent / 'other_components_20261102' / 'live_enrollment_20261102' / 'new_boot_binding_review_a6d4' / 'face_gallery_readback.26pin.candidate.json'
    binding_raw = binding_path.read_bytes()
    binding = json.loads(binding_raw)
    sources = binding['source_sha256']
    # Historical snapshot only, not a substitute for fresh actual startup/config.
    target_suffixes = tuple('/' + name for name in SPACE['TARGETS'])
    source_overlap = [name for name in sources if name.endswith(target_suffixes)]
    startup_overlap = [name for name in sources if name.endswith('/startup/config.json')]
    output = {'script_sha256': hashlib.sha256(SOURCE).hexdigest(),
              'probe_kind': 'AST-extracted helpers with explicit POSIX mode model and public synthetic files',
              'permission_cases': permission_cases,
              'partial_closure_probe': probe_known_partial_closure(),
              'public_binding_snapshot': {'path': str(binding_path),
                  'sha256': hashlib.sha256(binding_raw).hexdigest(),
                  'source_count': len(sources), 'two_source_overlap': source_overlap,
                  'startup_suffix_overlap': startup_overlap,
                  'historical_snapshot_only_fresh_check_required': True},
              'existing_tests_rerun': False, 'transaction_main_imported_or_run': False,
              'board_network_or_services_contacted': False,
              'gtk_files_modified': False, 'native_linux_execution': False}
    (HERE / 'GTK_TRANSACTION_TARGETED_PROBES.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
