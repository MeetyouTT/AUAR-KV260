"""Local AST and exact-byte evidence indexing; never imports inspected modules."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHORT = HERE/'review_sources'
SHORT.mkdir(exist_ok=True)


def save_source(name, raw):
    path = SHORT/name
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('An evidence snapshot already exists with different bytes: ' + name)
    else:
        path.write_bytes(raw)
    return {'local_path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}


def top_calls(tree):
    result = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            for part in node.decorator_list + node.args.defaults + [v for v in node.args.kw_defaults if v]:
                self.visit(part)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node):
            result.append({'line': node.lineno, 'call': ast.unparse(node.func)})
            self.generic_visit(node)

    Visitor().visit(tree)
    return result


def describe_python(raw):
    tree = ast.parse(raw)
    functions = {}
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append({'line': node.lineno, 'statement': ast.unparse(node)})
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.setdefault(node.name, []).append({'line': node.lineno, 'end_line': node.end_lineno,
                'calls': [{'line': c.lineno, 'target': ast.unparse(c.func)}
                          for c in ast.walk(node) if isinstance(c, ast.Call)]})
    return {'imports': imports, 'top_level_calls_excluding_method_bodies': top_calls(tree),
            'function_definitions': functions}


index = {}
checkpoint = json.loads((HERE/'checkpoint_sources_01.json').read_text(encoding='utf-8'))['board_result']
for remote, record in checkpoint['sources'].items():
    if 'text' not in record:
        continue
    raw = record['text'].encode()
    if hashlib.sha256(raw).hexdigest() != record['sha256']:
        raise ValueError('Public source evidence hash differs')
    name = Path(remote).name
    if name == '__init__.py':
        name = 'board_vision_init.py'
    index[name] = {'remote_path': remote, **save_source(name, raw), **describe_python(raw)}

loader = json.loads((HERE/'loader_sources_01.json').read_text(encoding='utf-8'))['board_result']['sources']
loader_names = {'example/sys/linux/dfx-mgr-client.c': 'dfx_cli.c',
                'example/sys/linux/dfx-mgrd.c': 'dfx_daemon.c',
                'src/daemon_helper.c': 'dfx_daemon_helper.c',
                'src/dfxmgr_client.c': 'dfx_client_transport.c',
                'src/dfxmgr_client.h': 'dfx_client_protocol.h',
                'src/accel.c': 'dfx_accel.c', 'src/sys/linux/accel.c': 'dfx_accel_linux.c'}
source_root = '/home/root/kv260-dfx-state-boardtest-20261004/staging/extracted/source/'
manifest_record = loader['/home/root/kv260-dfx-state-boardtest-20261004/staging/extracted/SOURCE_MANIFEST.json']
manifest = json.loads(manifest_record['text'])
for relative, name in loader_names.items():
    remote = source_root+relative
    record = loader[remote]
    raw = record['text'].encode()
    if hashlib.sha256(raw).hexdigest() != record['sha256'] or manifest[relative] != record['sha256']:
        raise ValueError('Preserved loader source manifest differs')
    index[name] = {'remote_path': remote, **save_source(name, raw), 'preserved_source_manifest_matches': True}

inventory = json.loads((HERE/'loader_inventory_01.json').read_text(encoding='utf-8'))['board_result']
raw = inventory['files']['/usr/bin/xmutil']['text'].encode()
index['xmutil.py'] = {'remote_path': '/usr/bin/xmutil', **save_source('xmutil.py', raw), **describe_python(raw)}
draft = HERE.parent/'parallel_platform/platform_transaction_draft.py'
raw = draft.read_bytes()
index['platform_transaction_draft_reviewed.py'] = {'original_local_path': str(draft),
    **save_source('platform_transaction_draft_reviewed.py', raw), **describe_python(raw)}
recipe_raw = (HERE/'checkpoint_readonly_call_recipe.py').read_bytes()
ast.parse(recipe_raw)
index['checkpoint_readonly_call_recipe.py'] = {'local_path': str(HERE/'checkpoint_readonly_call_recipe.py'),
    'sha256': hashlib.sha256(recipe_raw).hexdigest(), 'size': len(recipe_raw), 'ast_parse_passed': True,
    'executed': False}

result = {'schema': 'aura-platform-independent-static-audit-1',
          'release_status': 'EXECUTION_NOT_READY', 'project_imported': False,
          'validator_called': False, 'checkpoint_consumed': False,
          'loader_load_or_unload_executed': False, 'device_opened': False,
          'database_opened': False, 'board_mutations': False, 'files': index}
with (HERE/'STATIC_AUDIT.json').open('w', encoding='utf-8') as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps({'source_files_indexed': len(index), 'recipe_ast_parse_passed': True,
                  'draft_sha256': index['platform_transaction_draft_reviewed.py']['sha256'],
                  'release_status': result['release_status']}))
