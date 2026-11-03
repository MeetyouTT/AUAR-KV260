#!/usr/bin/env python3
"""Finalize only after all planned driver checks and baseline recovery finish."""
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def top5(path):
    return re.findall(r'r[.]index +([0-9]+).*r[.]score +([0-9.eE+-]+)', path.read_text())


def main():
    run = Path(sys.argv[1]).resolve()
    phases = ['02-state','03-baseline-functional','04-baseline-performance','05-save-original','05b-save-live-snapshots',
        '05c-save-action-guard','07-unpack-candidate','08-remove-old-app','09-unload-original-module','10-load-repaired-module',
        'c1-load-official','c1-functional','11-repaired-performance','c1-remove-official','c2-load-official','c2-functional',
        'c2-remove-official','c3-load-official','c3-functional','c3-remove-official','r1-unload-repaired-module',
        'r2-restore-original-module','r3-restore-official-app','r4-restored-functional','r5-final-state']
    command_checks = []
    for phase in phases:
        rows = [json.loads(s) for s in (run / (phase+'.results.jsonl')).read_text().splitlines()]
        records = [r for r in rows if r.get('type') == 'command']
        manifest=json.loads((run/(phase+'.commands.json')).read_text())
        assert any(r.get('type')=='connection' and r.get('ready') for r in rows), 'Root connection not confirmed'
        assert [r['id'] for r in records]==[r['id'] for r in manifest], 'Missing command evidence: '+phase
        assert [r['command'] for r in records]==[r['command'] for r in manifest], 'Manifest differs from actual command: '+phase
        assert records and all(r['complete'] and r['exit_code']==0 for r in records), 'Failed or incomplete phase: '+phase
        for row in records:
            path = run / (phase+'.'+row['id']+'.output')
            assert sha(path)==row['integrity_sha256'], 'UART decoded output changed'
            command_checks.append({'phase':phase,'id':row['id'],'exit_code':0,'sha256':sha(path)})
    transfer = json.loads((run/'06-candidate-transfer.result.json').read_text())
    assert transfer['complete'] and transfer['expected_sha256']=='3126707fe3c9165fd743dcbcc1408247337b538524e8b4de6c4edaa4e997cfef'
    final = json.loads((run/'r5-final-state.drivers_and_parameters.output').read_text())
    initial = json.loads((run/'02-state.drivers_and_parameters.output').read_text())
    assert final['loaded_srcversion']=='0991D1B457855C8987936E6' and final['zocl_parameters']==initial['zocl_parameters']
    assert final['fpga_state']=='operating' and final['firmware_name']==initial['firmware_name'] and final['vart_conf']==initial['vart_conf']
    before_hashes = [json.loads(s) for s in (run/'02-state.baseline_hashes.output').read_text().splitlines()]
    after_hashes = [json.loads(s) for s in (run/'r5-final-state.baseline_hashes.output').read_text().splitlines()]
    assert {r['path']:r['sha256'] for r in before_hashes}=={r['path']:r['sha256'] for r in after_hashes}, 'Baseline file hashes changed'
    expected_top = top5(run/'03-baseline-functional.classification.output')
    assert len(expected_top)==5
    for phase in ['c1-functional','c2-functional','c3-functional','r4-restored-functional']:
        assert top5(run/(phase+'.classification.output'))==expected_top, 'Classification changed: '+phase
        q=json.loads((run/(phase+'.dpu_query.output')).read_text())
        assert len(q['kernels'])==1 and q['kernels'][0]['fingerprint']=='0x101000056010407'
        assert q['kernels'][0]['cu_addr']=='0xa0010000' and q['kernels'][0]['DPU Frequency (MHz)']==300
    performance={}
    for label,phase in [('original','04-baseline-performance'),('repaired','11-repaired-performance')]:
        performance[label]={}
        for threads in (1,2):
            values=[float(re.search(r'FPS=([0-9.]+)',(run/(phase+'.t%d_r%d.output'%(threads,n))).read_text())[1]) for n in (1,2,3)]
            performance[label][str(threads)]={'fps':values,'median_fps':statistics.median(values)}
    deltas={str(t):100*(performance['repaired'][str(t)]['median_fps']/performance['original'][str(t)]['median_fps']-1) for t in (1,2)}
    assert all(abs(value)<10 for value in deltas.values()), 'Performance change needs review before completion'
    old=json.loads((run/'08-remove-old-app.review.json').read_text())['commands'][0]
    assert len(old['refcount_errors'])==1 and 'instead of 2' in old['refcount_errors'][0]
    cycles=[]
    for cycle in (1,2,3):
        data=json.loads((run/('c%d-remove-official.review.json'%cycle)).read_text())['commands'][0]
        assert data['kernel_interval_isolated'] and not data['refcount_errors'] and not data['exception_lines'] and not data['other_error_lines']
        cycles.append({'cycle':cycle,'uptime_before':data['uptime_before'],'uptime_after_snapshot_start':data['uptime_after'],
            'new_refcount_errors':0,'new_exception_lines':0})
    recovered=json.loads((run/'r3-restore-official-app.review.json').read_text())
    assert not any(c['refcount_errors'] or c['exception_lines'] or c['other_error_lines'] for c in recovered['commands'])
    final_kernel_text=(run/'r3-restore-official-app.restore-official-app.output').read_text().split('AFTER_DMESG_BEGIN\n',1)[1].split('AFTER_DMESG_END',1)[0]
    epoch=json.loads((run/'09-unload-original-module.review.json').read_text())['commands'][0]['uptime_after']
    unexpected=[line for line in final_kernel_text.splitlines() if 'expected refcount' in line and float(re.match(r'^\[\s*([0-9.]+)\]',line)[1])>=epoch]
    assert not unexpected, 'A delayed post-repair node reference error appeared'
    summary={'status':'finite_board_validation_passed_and_original_baseline_restored','board_verified':True,
        'scope':'ZOCL repair on official app only; no permanent installation, no M3 load, no SD/QSPI flash or reboot',
        'original_remove_refcount_errors':old['refcount_errors'],'cycles':cycles,'classification_top5':expected_top,
        'performance':performance,'performance_median_delta_percent':deltas,'recovery':final,
        'baseline_hashes_unchanged':True,'successful_commands':len(command_checks),'command_evidence':command_checks,
        'board_work_directory':json.loads((run/'run.json').read_text())['board_work_directory'],
        'remaining':['Permanent adoption of repaired driver not performed','Existing OF property warnings remain','Long-running/concurrent hot-unplug safety not validated','M3 co-existence and registers not tested']}
    output=run/'board_validation_summary.json'
    assert not output.exists(), 'Refusing to overwrite final summary'
    output.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:summary[k] for k in ['status','board_verified','cycles','performance_median_delta_percent','baseline_hashes_unchanged','successful_commands']},ensure_ascii=False))


if __name__=='__main__':
    main()
