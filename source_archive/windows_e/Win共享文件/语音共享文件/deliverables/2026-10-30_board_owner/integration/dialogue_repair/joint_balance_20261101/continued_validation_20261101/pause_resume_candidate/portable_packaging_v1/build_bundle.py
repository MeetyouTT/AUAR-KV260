"""Local packaging only; frozen candidate and original evidence remain untouched."""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent
FROZEN_SHA256 = 'dcb2014b328c21234c5214925bc56eba8c440c83dc07b0667428ad7d62daf7ab'
BUNDLE = CANDIDATE / 'portable_arm_v1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')


def main():
    frozen_bytes = (CANDIDATE / 'FROZEN_HANDOFF.json').read_bytes()
    assert digest(frozen_bytes) == FROZEN_SHA256
    frozen = json.loads(frozen_bytes)
    original_files = {}
    for relative, pin in frozen['files'].items():
        data = (CANDIDATE / relative).read_bytes()
        assert len(data) == pin['bytes'] and digest(data) == pin['sha256'], relative
        original_files[relative] = data
    dependencies = {}
    for row in frozen['support_sources']:
        data = Path(row['path']).read_bytes()
        assert digest(data) == row['sha256'], row['component']
        dependencies[row['component']] = (row, data)
    assert len(dependencies) == 7
    BUNDLE.mkdir(exist_ok=False)

    for relative in ('before/tools/voice_first_recording.py', 'after/tools/voice_first_recording.py'):
        destination = BUNDLE / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(original_files[relative])
    for relative, (_, data) in dependencies.items():
        destination = BUNDLE / 'support' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    original = original_files['test_public_methods.py'].decode('utf-8')
    (BUNDLE / 'original_test_public_methods.py').write_bytes(original_files['test_public_methods.py'])
    pins = {relative: row['sha256'] for relative, (row, _) in dependencies.items()}
    replacement = (
        'sys.dont_write_bytecode=True\n'
        'HERE=Path(__file__).resolve().parent\n'
        'SUPPORT_PINS=' + repr(pins) + '\n\n\n'
        'def pinned(relative):\n'
        "    path=HERE/'support'/relative\n"
        "    assert hashlib.sha256(path.read_bytes()).hexdigest()==SUPPORT_PINS[relative]\n"
        '    return path\n\n\n'
    )
    start = original.index('sys.dont_write_bytecode=True\n')
    end = original.index('class PublicCapture:')
    portable = original[:start] + replacement + original[end:]
    assert portable.count("HERE/'PUBLIC_TEST_RESULT.json'") == 1
    portable = portable.replace("HERE/'PUBLIC_TEST_RESULT.json'", "HERE/'PORTABLE_TEST_RESULT.json'")
    original_ast = ast.parse(original)
    portable_ast = ast.parse(portable, feature_version=(3, 9))
    original_definitions = {n.name: ast.dump(n, include_attributes=False)
                            for n in original_ast.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name != 'pinned'}
    portable_definitions = {n.name: ast.dump(n, include_attributes=False)
                            for n in portable_ast.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name != 'pinned'}
    assert original_definitions == portable_definitions
    test_class = next(n for n in portable_ast.body if isinstance(n, ast.ClassDef) and n.name == 'ExplicitResumeMethodsTests')
    test_names = [n.name for n in test_class.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
    assert len(test_names) == 9
    definitions = next(n for n in portable_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'definitions')
    assert "__future__" in ast.dump(definitions) and 'annotations' in ast.dump(definitions)
    (BUNDLE / 'test_public_methods_portable.py').write_text(portable, encoding='utf-8', newline='\n')
    (BUNDLE / 'PORTABLE_ADAPTATION.diff').write_text(
        ''.join(difflib.unified_diff(original.splitlines(True), portable.splitlines(True),
                                    fromfile='original_test_public_methods.py', tofile='test_public_methods_portable.py')),
        encoding='utf-8', newline='\n')
    for relative in ('run_public_validation.py', 'README.md'):
        (BUNDLE / relative).write_bytes((HERE / relative).read_bytes())
    syntax_checked = []
    for source in sorted(BUNDLE.rglob('*.py')):
        ast.parse(source.read_text(encoding='utf-8'), feature_version=(3, 9))
        syntax_checked.append(source.relative_to(BUNDLE).as_posix())
    manifest = {
        'schema': 'aura.explicit-pause-resume-portable-validation.v1',
        'minimum_python': '3.9',
        'source': frozen['source'],
        'baseline_startup_sha256': frozen['baseline_startup_sha256'],
        'baseline_spec_sha256': frozen['baseline_spec_sha256'],
        'original_frozen_handoff_sha256': FROZEN_SHA256,
        'before_sha256': frozen['before_sha256'],
        'after_sha256': frozen['after_sha256'],
        'original_test_sha256': frozen['files']['test_public_methods.py']['sha256'],
        'support_components': pins,
        'tests': 9,
        'test_names': test_names,
        'unchanged_non_loader_definition_names': sorted(original_definitions),
        'adaptations': ['package-relative pinned source loader', 'separate result filename'],
        'python39_syntax_checked': syntax_checked,
        'actual_ARM_or_conversation_acceptance': False,
        'production_or_private_runtime_access': False,
        'deployment_commands_included': False,
        'files': {},
    }
    for path in sorted(BUNDLE.rglob('*')):
        if path.is_file():
            data = path.read_bytes()
            manifest['files'][path.relative_to(BUNDLE).as_posix()] = {'bytes': len(data), 'sha256': digest(data)}
    write_json(BUNDLE / 'PACKAGE_MANIFEST.json', manifest)
    zip_path = CANDIDATE / 'portable_arm_v1.zip'
    with zipfile.ZipFile(zip_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(BUNDLE.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo('portable_arm_v1/' + path.relative_to(BUNDLE).as_posix(), date_time=(2026, 11, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
    receipt = {
        'schema': 'aura.explicit-pause-resume-portable-packaging.v1',
        'zip_file': zip_path.name,
        'zip_bytes': zip_path.stat().st_size,
        'zip_sha256': digest(zip_path.read_bytes()),
        'manifest_sha256': digest((BUNDLE / 'PACKAGE_MANIFEST.json').read_bytes()),
        'pinned_input_files': len(manifest['files']),
        'before_sha256': frozen['before_sha256'],
        'after_sha256': frozen['after_sha256'],
        'tests_unchanged': 9,
        'support_components': 7,
        'python39_syntax_checked_files': len(syntax_checked),
        'original_evidence_unchanged': all((CANDIDATE / name).read_bytes() == data for name, data in original_files.items()),
        'local_or_ARM_tests_executed_by_builder': False,
        'actual_ARM_or_deployment_acceptance': False,
    }
    assert receipt['original_evidence_unchanged']
    write_json(CANDIDATE / 'PORTABLE_ARM_PACKAGING_RECEIPT.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
