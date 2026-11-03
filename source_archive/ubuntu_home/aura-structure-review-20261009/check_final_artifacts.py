#!/usr/bin/env python3
"""Independently recheck the delivered architecture and source-role review."""
import ast
import hashlib
import json
from pathlib import Path
import re
import runpy
from urllib.parse import unquote, urlparse
import zipfile

TASK = Path(__file__).resolve().parent
BASE = Path('/home/ghmd/aura-submission-framework-20261009/check_final_artifacts.py')


def main():
    # Reuse the previous independent matrix/PDF/archive audit; preserve its old log.
    base = runpy.run_path(str(BASE))
    base['main'].__globals__['TASK'] = TASK
    base['main']()
    root, out, stage = base['ROOT'], base['OUT'], base['STAGE']
    load, read_csv, Page = base['load'], base['read_csv'], base['Page']
    result = load(TASK / 'validation_final.json')
    spec = load(out / 'structure_spec.json')
    validation = load(out / 'structure_review_validation.json')
    basis = load(out / 'structure_basis.json')
    source_rows = read_csv(out / 'current_source_map.csv')
    imports = read_csv(out / 'static_imports.csv')
    source_names = {r['current_path'] for r in source_rows}
    actual_names = {p.relative_to(root).as_posix()
                    for folder in ('board', 'common', 'host', 'tools', 'scripts', 'tests')
                    for p in (root / folder).rglob('*.py') if '__pycache__' not in p.parts}
    assert source_names == actual_names and len(source_rows) == 171
    for row in source_rows:
        raw = (root / row['current_path']).read_bytes()
        assert len(raw) == int(row['bytes'])
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        ast.parse(raw.decode('utf-8-sig'), filename=row['current_path'])
        assert row['relocation_state'] == 'SOURCE_NOT_MOVED'
    assert len(imports) == 420
    for row in imports:
        assert row['consumer'] in source_names and row['provider'] in source_names
        lines = (root / row['consumer']).read_text(encoding='utf-8-sig').splitlines()
        assert 'import' in lines[int(row['line']) - 1]
    assert len(spec['directories']) == 59 and len(spec['basis']) == 22
    for directory in spec['directories']:
        text = (stage / directory['path'] / 'README.md').read_text(encoding='utf-8')
        assert text.count('<!-- aura-structure-details -->') == 1
        assert directory['owner'] in text and directory['purpose'] in text
    for reference in basis['references']:
        p = Path(reference['path'])
        p = p if p.is_absolute() else root / p
        assert p.exists()
        if 'sha256' in reference:
            assert hashlib.sha256(p.read_bytes()).hexdigest() == reference['sha256']
    assert len(basis['code_anchors']) == 14
    for anchor in basis['code_anchors']:
        p = Path(anchor['path'])
        p = p if p.is_absolute() else root / p
        line = p.read_text(encoding='utf-8-sig').splitlines()[anchor['line'] - 1].strip()
        assert line == anchor['excerpt']
    contracts = load(out / 'contract_registry.json')['entries']
    assert [c['id'] for c in contracts] == ['I%02d' % i for i in range(1, 8)]
    with zipfile.ZipFile('/home/ghmd/下载/项目.zip') as z:
        manager = z.read('项目/方案/AURA_三人执行总包_2026-10-02/00_总负责人_系统集成与交付总包.md').decode('utf-8-sig')
    for contract in contracts:
        row = re.search(r'^\| ' + contract['id'] + r' \|.*$', manager, re.M).group(0)
        assert contract['original_name'] in row
        assert contract['frozen_final_contract'] is False
    corrections = spec['plan_path_corrections']
    for correction in corrections:
        assert not (stage / correction['before'] / 'interface.json').exists()
        assert load(stage / correction['after'] / 'interface.json')['module_id'] == correction['module']
    html_checks = []
    for path in (out / 'structure_detail.html', stage / 'report/structure_detail.html'):
        text = path.read_text(encoding='utf-8')
        page = Page()
        page.feed(text)
        assert len(page.ids) == len(set(page.ids))
        assert page.external_scripts == 0
        assert len(re.findall(r'<details class="folder"', text)) == 59
        count = 0
        for href in page.links:
            url = urlparse(href)
            if url.scheme or url.netloc:
                continue
            if url.path:
                assert (path.parent / unquote(url.path)).exists(), (str(path), href)
            else:
                assert url.fragment in page.ids, href
            count += 1
        html_checks.append({'path': str(path), 'local_links_checked': count,
                            'folder_cards': 59, 'unique_ids': True})
    for name in ('structure_detail.md', 'directory_catalog.csv', 'current_source_map.csv',
                 'static_imports.csv', 'resource_owners.csv', 'contract_registry.json',
                 'structure_basis.json', 'structure_review_validation.json'):
        assert (out / name).read_bytes() == (stage / 'report' / name).read_bytes()
    assert validation['passed'] and not validation['active_source_relocated']
    assert not validation['runtime_tests_rerun'] and not validation['hardware_or_model_execution']
    result['structure_review'] = {
        'directory_responsibilities_verified': 59,
        'original_contract_ids_and_filenames_verified': [c['id'] for c in contracts],
        'python_source_hashes_and_ast_verified': 171,
        'local_static_import_records_verified': len(imports),
        'basis_entries': 22,
        'basis_file_hash_references_verified': sum('sha256' in r for r in basis['references']),
        'code_anchors_exactly_match': 14,
        'old_module_descriptors_removed_and_new_verified': len(corrections),
        'structure_html_checks': html_checks,
        'source_roles_are_design_mapping_not_migrated_packages': True,
        'runtime_tests_rerun': False, 'hardware_or_model_execution': False,
    }
    result['scope'] = 'ARCHITECTURE_AND_STRUCTURE_ARTIFACT_AUDIT_ONLY'
    result['base_audit_script_sha256'] = hashlib.sha256(BASE.read_bytes()).hexdigest()
    (TASK / 'validation_final.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['structure_review'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
