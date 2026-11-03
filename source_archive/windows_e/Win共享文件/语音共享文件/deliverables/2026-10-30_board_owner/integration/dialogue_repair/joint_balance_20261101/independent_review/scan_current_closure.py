"""Hash-match current mapped Python sources locally and check projection extensions."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECT = ROOT.parents[4]


def main():
    index = json.loads((ROOT / 'source_index.json').read_text(encoding='utf-8'))
    manifest_bytes = Path(index['manifest_path']).read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == index['manifest_sha256']
    manifest = json.loads(manifest_bytes)
    older = json.loads((ROOT.parent / 'jpeg_demand_review_v20/SOURCE_AUDIT.json').read_text(encoding='utf-8'))
    old_paths = {row['component']: row['path'] for row in older['files']}
    records, missing, projection_definitions, subclass_overrides, replacement_sites = [], [], [], [], []
    for component, expected in manifest['component_pins'].items():
        if not component.endswith('.py'):
            continue
        candidates = [ROOT / 'baseline' / component]
        if component in index['files']:
            candidates.append(Path(index['files'][component]['source']))
        if component in old_paths:
            candidates.append(Path(old_paths[component]))
        candidates.append(PROJECT / 'aura' / component)
        found = None
        for path in candidates:
            if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
                found = path
                break
        if found is None:
            result = subprocess.run(['rg', '--files', str(PROJECT), '-g', Path(component).name,
                '-g', '!**/node_modules/**', '-g', '!**/.venv/**'], capture_output=True, text=True, encoding='utf-8', check=False)
            if result.returncode not in (0, 1):
                raise RuntimeError('Local source inventory failed')
            for name in result.stdout.splitlines():
                path = Path(name)
                if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
                    found = path
                    break
        if found is None:
            missing.append(component)
            continue
        text = found.read_text(encoding='utf-8-sig')
        tree = ast.parse(text)
        records.append(dict(component=component, path=str(found), sha256=expected))
        aliases = {'PresentationLifecycle'}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith('production_memory_presentation'):
                aliases.update(alias.asname or alias.name for alias in node.names if alias.name == 'PresentationLifecycle')
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if any((isinstance(base, ast.Name) and base.id in aliases) or
                       (isinstance(base, ast.Attribute) and base.attr == 'PresentationLifecycle') for base in node.bases):
                    subclass_overrides.append(dict(component=component, line=node.lineno, name=node.name))
                for member in node.body:
                    if isinstance(member, ast.FunctionDef) and member.name == '_projection':
                        projection_definitions.append(dict(component=component, line=member.lineno, class_name=node.name))
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any((isinstance(target, ast.Attribute) and target.attr == '_projection') or
                       (isinstance(target, ast.Name) and target.id in aliases) for target in targets):
                    replacement_sites.append(dict(component=component, line=node.lineno, kind='assignment'))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'setattr':
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and node.args[1].value in ('_projection', 'PresentationLifecycle'):
                    replacement_sites.append(dict(component=component, line=node.lineno, kind='setattr'))
        # Record any direct access not represented by the AST checks above for manual review.
        if re.search(r'production_presentation\.__class__|__dict__\[[\'"]_projection[\'"]\]', text):
            replacement_sites.append(dict(component=component, kind='dynamic_access_requires_review'))
    result = dict(schema='aura.current-presentation-extension-scan.v1',
        startup_sha256=index['startup_sha256'], manifest_sha256=index['manifest_sha256'],
        current_python_components_matched=len(records), missing_python_components=missing,
        projection_method_definitions=projection_definitions, lifecycle_subclasses=subclass_overrides,
        projection_replacement_sites=replacement_sites, files=records,
        scope='Direct static Python source patterns in hash-matched mapped components; not a claim about arbitrary external monkeypatching',
        device_model_service_or_database_access=False)
    (HERE / 'CLOSURE_SCAN.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'files'}))
    if missing or subclass_overrides or replacement_sites:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
