"""One RAM-only interrupted-publication rollback case for root's stable v2."""
import ast
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
PRIMARY = HERE.parent / 'boot_review_inputs/observed_revision2/candidate'
source = (PRIMARY / 'manage_installation.py').read_bytes()
assert hashlib.sha256(source).hexdigest() == 'de31f75b2aac3296861cbdb80a075dd5f3762eff93d885a8c6b9af95462ad975'
rule_source = (PRIMARY / 'recovery_rules.py').read_bytes()
assert hashlib.sha256(rule_source).hexdigest() == '72492c2d50c746b2f26b3292beff189bd76d7d39be04515baab13dbc881c7284'
rules = {}
exec(compile(rule_source, '<pure-recovery-rules>', 'exec'), rules)
files, mutations = {}, []
BOOT = '10000000-0000-4000-8000-000000000001'


class MemoryPath(PurePosixPath):
    def resolve(self):
        return self

    def exists(self):
        return str(self) in files

    def read_text(self):
        return files[str(self)].decode()

    def unlink(self):
        mutations.append(('unlink', str(self)))
        del files[str(self)]


state, package, aura = map(MemoryPath, ('/synthetic/state', '/synthetic/package', '/synthetic/aura'))
directory = state / 'boots' / BOOT / 'binding-700-111'
startup = MemoryPath('/synthetic/startup.json')
ui = aura / 'config/board_avatar_gtk.json'
contract_raw = rules['encoded']({'startup_path': str(startup), 'runtime_aura': str(aura)})
files[str(package / 'contract.json')] = contract_raw
files['/proc/sys/kernel/random/boot_id'] = BOOT.encode()
ui_before, ui_after = b'known UI before', b'known UI after'
startup_before, startup_after = b'known startup before', b'known startup after'
prior_active, published_active = b'null\n', rules['encoded']({'synthetic_after_ledger': True})
intent = dict(contract_sha256=rules['digest'](contract_raw), boot_id=BOOT,
              ui_before_sha256=rules['digest'](ui_before), ui_after_sha256=rules['digest'](ui_after),
              startup_before_sha256=rules['digest'](startup_before), startup_after_sha256=rules['digest'](startup_after),
              active_before_sha256=rules['digest'](prior_active))
for name, raw in (('intent.json', rules['encoded'](intent)), ('ui.before.json', ui_before), ('ui.after.json', ui_after),
                  ('startup.before.json', startup_before), ('startup.after.json', startup_after),
                  ('active-source.before.json', prior_active)):
    files[str(directory / name)] = raw
files[str(ui)] = ui_after
files[str(startup)] = startup_after
files[str(state / 'active-source.json')] = published_active
# Exact on-disk phase after active ledger replacement and before committed creation.
assert not (directory / 'committed.json').exists()


def regular(path, limit=67108864):
    return files[str(path)]


def replace_known(path, before, after):
    assert files[str(path)] == before
    mutations.append(('replace', str(path)))
    files[str(path)] = after


function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'rollback_binding')
scope = dict(Path=MemoryPath, STATE_ROOT=state, PACKAGE_ROOT=package, json=json,
             board_only=lambda: None, lock_state=lambda: None, no_live_helpers_or_loader_jobs=lambda: None,
             regular=regular, unit=lambda name: {'MainPID': '0', 'ActiveState': 'inactive', 'SubState': 'dead', 'Job': '', 'Result': 'success'},
             owner_scan=lambda: {'complete': True, 'owners': [], 'unreadable': []},
             replace_known=replace_known, fsync_directory=lambda path: None,
             **{name: rules[name] for name in ('require', 'require_no_owners', 'digest', 'CAMERA', 'GUI')})
exec(compile(ast.Module(body=[copy.deepcopy(function)], type_ignores=[]), '<exact-rollback-binding>', 'exec'), scope)
before_files = copy.deepcopy(files)
reason = None
try:
    scope['rollback_binding'](directory)
except rules['Hold'] as exc:
    reason = str(exc)
assert reason == 'NEWER_ACTIVE_LEDGER_CONFLICT'
assert files == before_files and not mutations
report = {
    'candidate_sha256': hashlib.sha256(source).hexdigest(),
    'case': 'active_source_written_committed_missing',
    'outcome': reason, 'safe_hold_without_mutation': True,
    'exact_UI_startup_before_after_backups_known': True,
    'active_after_ledger_not_presealed_by_intent': True,
    'limitation': 'Automatic exact rollback does not cover this interrupted publication phase; original operator must reconcile. Rebinding already-current returns before committed creation and does not repair the missing record.',
    'scope': 'One RAM-only exact rollback_binding AST call. The state is the documented interruption point; board/root/owner/service/IO surfaces are explicit synthetic stubs. No Native or production execution.',
    'candidate_modified': False,
}
with (HERE / 'BOOT_BINDING_COMMIT_GAP_CASE.json').open('x', encoding='utf-8') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
print(json.dumps(report))
