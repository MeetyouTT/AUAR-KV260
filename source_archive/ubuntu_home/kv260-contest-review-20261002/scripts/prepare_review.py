#!/usr/bin/env python3
"""Read selected documents from the user ZIP; execute no archived scripts."""
import datetime
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIP = Path('/home/ghmd/下载/项目.zip')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    inputs = ROOT / 'inputs'
    inputs.mkdir(exist_ok=False)
    selected = {
        "项目/参赛资料/全国大学生嵌入式芯片与系统设计竞赛'2026FPGA赛道选题指南-AMD.pdf":
        'official_amd_2026.pdf',
        '项目/aura_fpga/docs/submission_matrix.csv': 'project_submission_matrix.csv',
        '项目/方案/AURA_KV260_完整实施方案_无声源定位版_2026-09-30.md':
        'project_plan.md',
        '项目/方案/reference_round4_20260926/amd_kv260_track_fit_assessment_v1_2.extracted.md':
        'prior_track_fit_analysis.md',
        '项目/README.md': 'project_readme.md'
    }
    before = sha(ZIP)
    extracted = []
    with zipfile.ZipFile(ZIP) as packed:
        entries = [{'name': p.filename, 'bytes': p.file_size,
                    'compressed_bytes': p.compress_size, 'directory': p.is_dir()}
                   for p in packed.infolist()]
        for name, dest in selected.items():
            data = packed.read(name)
            path = inputs / dest
            path.write_bytes(data)
            extracted.append({'zip_member': name, 'path': str(path),
                              'bytes': len(data), 'sha256': sha(path),
                              'role': 'official guide' if path.suffix == '.pdf'
                              else 'project documentation, not normative rules'})
    (ROOT / 'archive_inventory.json').write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + '\n')
    commands = [
        ('pdfinfo', ['/usr/bin/pdfinfo', str(inputs / 'official_amd_2026.pdf')]),
        ('pdftotext', ['/usr/bin/pdftotext', '-layout',
                      str(inputs / 'official_amd_2026.pdf'),
                      str(ROOT / 'official_amd_2026.txt')])
    ]
    records = []
    for name, argv in commands:
        done = subprocess.run(argv, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True)
        (ROOT / (name + '.stdout')).write_text(done.stdout)
        (ROOT / (name + '.stderr')).write_text(done.stderr)
        records.append({'name': name, 'argv': argv, 'exit_code': done.returncode})
        assert done.returncode == 0
    assert sha(ZIP) == before
    (ROOT / 'input_manifest.json').write_text(json.dumps({
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'original_zip': str(ZIP), 'zip_bytes': ZIP.stat().st_size,
        'zip_sha256': before, 'original_zip_unchanged': True,
        'zip_members': len(entries), 'selected_documents': extracted,
        'archived_code_executed': False, 'conversion_commands': records
    }, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'selected_documents': len(extracted), 'zip_members': len(entries),
                      'zip_unchanged': True, 'text': str(ROOT / 'official_amd_2026.txt')}))


if __name__ == '__main__':
    main()
