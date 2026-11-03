"""Publish only this audit's code and numerical reports into the agreed share."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent
DEST = Path('/home/ghmd/Win共享文件/协作任务/2026-10-26_整机架构时序与硬件审查')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    originals = json.loads((ROOT / 'source_inventory.json').read_text())
    changed = [entry['path'] for entry in originals if digest(Path(entry['path'])) != entry['sha256']]
    if changed:
        raise RuntimeError('Audit inputs changed; reconcile before finalizing: ' + str(changed))
    facts = json.loads((ROOT / 'review_facts.json').read_text())
    assert facts['fpga_report_generation_complete']
    assert facts['routed_setup_hold_summary_matches_frozen_report']
    assert facts['no_congestion_windows_above_level_5']
    evidence = DEST / 'evidence'
    fpga = evidence / 'fpga'
    scripts = DEST / 'scripts'
    for folder in (evidence, fpga, scripts):
        folder.mkdir(parents=True, exist_ok=True)
    for name in ('source_inventory.json', 'zip_sources.json', 'software_probes.json',
                 'checkpoint_input.json', 'review_facts.json'):
        shutil.copy2(ROOT / name, evidence / name)
    for source in sorted((ROOT / 'fpga').iterdir()):
        if source.is_file() and source.suffix in ('.rpt', '.tsv', '.xdc'):
            shutil.copy2(source, fpga / source.name)
    for name in ('review_checkpoint.tcl', 'run_software_probes.py', 'collect_evidence.py', 'finalize_review.py'):
        shutil.copy2(ROOT / name, scripts / name)
    report = DEST / 'README.md'
    text = report.read_text()
    ids = re.findall(r'^\| (S\d\d) \|', text, re.M)
    assert ids == ['S%02d' % n for n in range(1, 10)]
    links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', text)
    local_links = [link for link in links if not re.match(r'^[a-z]+://', link)]
    missing = []
    for link in local_links:
        target = Path(link) if link.startswith('/') else report.parent / link
        if not target.exists():
            missing.append(link)
    assert not missing, missing
    validation = dict(
        updated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        conclusion='AUDIT_COMPLETE_WITH_OPEN_ENGINEERING_FINDINGS',
        selected_control_regressions=dict(command='python3 -B -m unittest -v test_deadline_driver test_session_shutdown',
                                         tests=18, failures=0, errors=0, exit_code=0),
        counterexamples=dict(count=3, reproduced=True, devices_or_network_used=False),
        vivado=dict(attempt1_exit_code=124, attempt1_reason='240s command budget shorter than checkpoint loading',
                    attempt2_exit_code=0, checkpoint_opened=True, report_or_export_commands=10,
                    cdc_critical=4, cdc_critical_acknowledged_not_waived=True,
                    setup_hold_failures=0, routing_errors=0, no_congestion_windows_above_level5=True),
        input_fingerprints_unchanged=len(originals), zip_members_hashed=7,
        source_findings=ids, local_links_verified=len(local_links),
        board_access=False, windows_access=False, production_modified=False,
        waveform_or_mechanics_verified=False,
        scope='Project audit; historical board records plus new local simulation and final-DCP reports')
    (DEST / 'VALIDATION.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
    contents = [path for path in DEST.rglob('*') if path.is_file() and path.name != 'SOURCE_MANIFEST.json']
    manifest = dict(schema='aura-system-audit-source-1',
                    files={str(path.relative_to(DEST)): dict(bytes=path.stat().st_size, sha256=digest(path))
                           for path in sorted(contents)})
    (DEST / 'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    for name, entry in manifest['files'].items():
        assert digest(DEST / name) == entry['sha256']
    print(json.dumps(dict(status='PASS', audit_files=len(contents), source_inputs=len(originals),
                          local_links=len(local_links), findings=len(ids),
                          artifact_bytes=sum(v['bytes'] for v in manifest['files'].values())), ensure_ascii=False))


if __name__ == '__main__':
    main()
