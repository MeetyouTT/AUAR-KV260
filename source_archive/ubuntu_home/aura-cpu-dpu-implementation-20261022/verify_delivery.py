import ast,csv,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_cpu_dpu_implementation')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    r=json.loads((ROOT/'release.json').read_text());audit=json.loads((ROOT/'evidence/active-release-audit.json').read_text())
    assert r['current_production']['camera_pid']==audit['pid']==192540
    assert audit['sface_shadow_absent'] and audit['cu_collector_inactive'] and not audit['active_owned_rollback_timers']
    assert r['T3']['passed'] is False and r['T3']['rollback_verified']
    assert r['T1']['runtime_wiring_board_verified'] is False and not r['T1']['new_database_created']
    assert not r['T2']['runtime_instrumentation_deployed'] and not r['merged_candidate']['board_deployed']
    assert r['audio']['current_recurrence_cleared'] and not r['audio']['root_cause_fixed']
    for line in (ROOT/'calibration-candidate/FILES.sha256').read_text().splitlines():
        expected,name=line.split('  ',1);assert sha(ROOT/'calibration-candidate'/name)==expected
    combined=json.loads((ROOT/'combined-manifest.json').read_text())
    assert len(combined['files'])==11
    for name,meta in combined['files'].items():
        path=ROOT/'combined-candidate/aura'/name
        assert sha(path)==meta['sha256'] and path.stat().st_size==meta['bytes']
    for name,meta in json.loads((ROOT/'metrics-manifest.json').read_text())['files'].items():
        assert sha(ROOT/'metrics-candidate/aura'/name)==meta['sha256']
    assert re.findall(r'Ran (\d+) tests',(ROOT/'combined-test-results.txt').read_text())==['46','10']
    assert 'Ran 5 tests' in (ROOT/'metrics-test-results.txt').read_text()
    with (ROOT/'tasks.csv').open(newline='') as f:tasks=list(csv.DictReader(f))
    assert len(tasks)==8 and all(None not in row and all(v is not None for v in row.values()) for row in tasks)
    py_count=json_count=links=0
    for p in ROOT.rglob('*'):
        assert not p.is_symlink()
        if not p.is_file():continue
        assert '__pycache__' not in p.parts
        assert p.suffix.lower() not in {'.jpg','.jpeg','.png','.webp','.wav','.mp3','.mp4','.npy','.npz','.db','.sqlite','.sqlite3','.raw'}
        if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p));py_count+=1
        if p.suffix=='.json':json.loads(p.read_text());json_count+=1
        if p.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if target.startswith(('http:','https:','#')) or target=='validation.json':continue
                assert (p.parent/target).exists(),(p,target)
                links+=1
    contract=json.loads((ROOT/'evidence/calibration-board-contract.json').read_text())
    assert contract['checks_passed']==8 and not contract['runtime_verified'] and not contract['dpu_opened']
    value={'status':'PASS','verified_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Delivery integrity, syntax, local links and archived result consistency; not additional model or field acceptance',
        'frozen_calibration_entries_verified':22,'combined_source_entries_verified':11,
        'python_files_ast_parsed':py_count,'json_files_parsed_before_report':json_count,
        'local_markdown_links_verified':links,'task_rows':len(tasks),
        'long_run_failure_preserved':True,'current_production_shadow_off':True,
        'board_contract_simulation_is_runtime_acceptance':False,'windows_sync_confirmed':False}
    (ROOT/'validation.json').write_text(json.dumps(value,indent=2)+'\n')
    manifest=ROOT/'FILES.sha256'
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p!=manifest)
    manifest.write_text(''.join(sha(p)+'  '+str(p.relative_to(ROOT))+'\n' for p in files))
    for line in manifest.read_text().splitlines():
        expected,name=line.split('  ',1);assert sha(ROOT/name)==expected
    print(json.dumps({'validation':value,'parent_manifest_files_verified':len(files)}))


if __name__=='__main__':verify()
