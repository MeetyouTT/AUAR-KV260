#!/usr/bin/env python3
"""Check delivered graphs, source provenance, original matrices and archive."""
import csv
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlparse
import zipfile

ROOT = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
OUT = ROOT / 'report/architecture'
STAGE = ROOT / 'submission/aura_junior'
TASK = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_csv(path):
    rows = list(csv.reader(path.open(encoding='utf-8', newline='')))
    assert rows and all(len(row) == len(rows[0]) for row in rows), str(path)
    return [dict(zip(rows[0], row)) for row in rows[1:]]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = [], []
        self.svgs = self.module_rows = self.external_scripts = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'svg':
            self.svgs += 1
        if tag == 'tr' and a.get('class') == 'module-row':
            self.module_rows += 1
        if tag == 'script' and a.get('src'):
            self.external_scripts += 1
        if tag == 'a' and 'href' in a:
            self.links.append(a['href'])


def main():
    data, sources = load(OUT / 'architecture.json'), load(OUT / 'requirement_sources.json')
    modules = {m['id']: m for m in data['modules']}
    assert len(modules) == 64
    for folder in (OUT, STAGE):
        for path in folder.rglob('*.json'):
            load(path)
        for path in folder.rglob('*.csv'):
            read_csv(path)
    wp = read_csv(OUT / 'work_packages.csv')
    tests = read_csv(OUT / 'acceptance_matrix.csv')
    req = read_csv(OUT / 'requirements_matrix.csv')
    with zipfile.ZipFile('/home/ghmd/下载/项目.zip') as z:
        manager = z.read('项目/方案/AURA_三人执行总包_2026-10-02/00_总负责人_系统集成与交付总包.md').decode('utf-8-sig')
        titles = {key: title.split('｜')[0].strip() for key, title in re.findall(r'^### ([ABC]\d\d) (.+)$', manager, re.M)}
        assert len(titles) == 42
        assert {p['id']: p['title'] for p in wp} == titles
        scope = z.read('项目/方案/AURA_KV260_完整实施方案_无声源定位版_2026-09-30.md').decode('utf-8-sig')
        original_tests = {}
        for line in scope.splitlines():
            if re.match(r'^\| T\d\d \|', line):
                cells = [v.strip() for v in line.strip('|').split('|')]
                assert len(cells) == 4
                original_tests[cells[0]] = cells[1:]
        assert len(original_tests) == 30
        for row in tests:
            assert [row['test'], row['internal_target_not_official'], row['required_evidence']] == original_tests[row['id']]
        original_req = list(csv.DictReader(io.StringIO(z.read('项目/aura_fpga/docs/submission_matrix.csv').decode('utf-8-sig'))))
        assert len(req) == len(original_req) == 17
        for original, current in zip(original_req, req):
            assert all(current[key] == value for key, value in original.items() if key != 'status')
        for entry in load(OUT / 'provenance.json')['sources']:
            raw = z.read(entry['zip_entry']) if 'zip_entry' in entry else Path(entry['path']).read_bytes()
            assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256']
    assert {k: sum(p['owner'] == k for p in wp) for k in 'ABC'} == {'A': 14, 'B': 14, 'C': 14}
    assert {p['id'] for p in tests if p['status'] == 'NOT_APPLICABLE_REMOVED'} == {'T13', 'T14'}
    assert all(p['status'] == 'FINAL_UNIFIED_RELEASE_NOT_ACCEPTED' for p in tests if p['id'] not in ('T13', 'T14'))
    for rows, key in ((wp, 'modules'), (tests, 'modules'), (req, 'module_ids')):
        assert all(set(row[key].split()) <= modules.keys() for row in rows)
    metrics = read_csv(STAGE / 'data/metrics/optimization_results.csv')
    assert len(metrics) == 6
    assert all(row['status'] == 'NOT_EXECUTED' and all(row[k] == '' for k in list(row)[4:-1]) for row in metrics)
    refs = load(OUT / 'source_references.json')
    assert len(refs) == 107 and all(r['exists'] for r in refs)
    for m in modules.values():
        assert (STAGE / m['planned_path'] / 'README.md').is_file()
        assert load(STAGE / m['planned_path'] / 'interface.json')['module_id'] == m['id']
    assert all((STAGE / name / 'README.md').is_file() for name in ('src', 'sim', 'build', 'board', 'data', 'skill', 'report'))
    page = Page()
    page.feed((OUT / 'index.html').read_text(encoding='utf-8'))
    assert page.svgs == 8 and page.module_rows == 64 and page.external_scripts == 0
    assert len(page.ids) == len(set(page.ids)), 'Duplicate HTML IDs'
    local_links = 0
    for href in page.links:
        url = urlparse(href)
        if url.scheme or url.netloc:
            continue
        if url.path:
            assert (OUT / unquote(url.path)).exists(), href
            local_links += 1
        else:
            assert url.fragment in page.ids, href
    for path in (STAGE / 'README.md', STAGE / 'report/README.md', STAGE / 'report/design_report.md'):
        for href in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            assert (path.parent / href).exists(), (str(path), href)
    for d in data['diagrams']:
        for fmt in ('dot', 'mmd', 'svg', 'png', 'pdf'):
            assert (OUT / 'figures' / (d['id'] + '.' + fmt)).read_bytes() == (STAGE / 'report/figures' / (d['id'] + '.' + fmt)).read_bytes()
    pdf = OUT / 'framework_diagrams.pdf'
    info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True, check=True).stdout
    assert re.search(r'Pages:\s+8\b', info)
    text = subprocess.run(['pdftotext', str(pdf), '-'], capture_output=True, text=True, check=True).stdout
    compact = re.sub(r'\s+', '', text)
    assert all(re.sub(r'\s+', '', d['title']) in compact for d in data['diagrams'])
    assert pdf.read_bytes() == (STAGE / 'report/framework_diagrams.pdf').read_bytes()
    bundle = load(OUT / 'bundle_result.json')
    archive_path = Path(bundle['path'])
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == bundle['sha256']
    with zipfile.ZipFile(archive_path) as z:
        manifest = json.loads(z.read('aura/architecture_bundle_manifest.json'))
        assert len(z.namelist()) == len(manifest['files']) + 1
        assert len(manifest['files']) == bundle['files_verified']
        assert all(re.fullmatch(r'[A-Za-z0-9_./-]+', name) and '..' not in Path(name).parts for name in z.namelist())
        for entry in manifest['files']:
            raw = z.read('aura/' + entry['path'])
            assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256']
            assert raw == (ROOT / entry['path']).read_bytes(), 'Archive payload differs from final source'
    result = {
        'passed': True, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'modules': 64, 'work_packages_exactly_match_original': 42,
        'owners': {'A': 14, 'B': 14, 'C': 14}, 'acceptance_rows_exactly_match_original': 30,
        'removed_tests': ['T13', 'T14'], 'official_mapping_rows_match_original': 17,
        'provenance_sha256_verified': 12, 'source_references_exist': 107,
        'html_figures': 8, 'html_module_rows': 64, 'html_ids_unique': True,
        'local_html_links_exist': local_links, 'offline_external_script_dependencies': 0,
        'stage_markdown_links_exist': True, 'pdf_pages': 8, 'pdf_all_titles_found': True,
        'figures_identical_in_stage': 40, 'unperformed_experiment_rows_are_blank': 6,
        'bundle_payload_files_verified': bundle['files_verified'], 'bundle': bundle,
        'physical_actuation': False, 'scope': 'ARCHITECTURE_ARTIFACT_AUDIT_ONLY'
    }
    (TASK / 'validation_final.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
