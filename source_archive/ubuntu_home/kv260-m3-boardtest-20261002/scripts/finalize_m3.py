#!/usr/bin/env python3
"""Audit completed captured evidence only; no board operations."""
import ast
import base64
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()


def kernel(text):
    match=re.search(r'^AFTER_DMESG_BEGIN\n(.*?)^AFTER_DMESG_END',text,re.M|re.S)
    return match[1].splitlines() if match else []


def main():
    run=Path(sys.argv[1]).resolve()
    controller=json.loads((run/'controller.result.json').read_text())
    assert controller['passed'] and controller['completed_phases']==controller['ordered_phases']
    assert controller['original_baseline_restored'] and controller['baseline_file_hashes_unchanged']
    assert controller['runner_sha256']==sha(ROOT/'scripts/run_m3.py')
    assert controller['collector_sha256']==sha(run/'collect_serial.py')
    assert controller['reviewer_sha256']==sha(ROOT/'scripts/review_board_phase.py')
    prepared=json.loads((run/'preparation.json').read_text())
    commands=[]
    post_review=json.loads((run/'post_review_preparation.json').read_text())
    assert sha(run/'26-post-review.commands.json')==post_review['manifest_sha256']
    for ident,digest in post_review['source_hashes'].items():
        assert sha(run/'action_sources'/('26-post-review.'+ident+'.py'))==digest
    for phase in ['01-preflight','02-state','03-capabilities']+controller['ordered_phases']+['26-post-review']:
        if phase=='07-transfer-bundle':continue
        rows=[json.loads(line) for line in (run/(phase+'.results.jsonl')).read_text().splitlines()]
        actual=[row for row in rows if row.get('type')=='command']
        manifest=json.loads((run/(phase+'.commands.json')).read_text())
        assert any(row.get('type')=='connection' and row.get('ready') for row in rows)
        assert [row['id'] for row in actual]==[row['id'] for row in manifest]
        assert [row['command'] for row in actual]==[row['command'] for row in manifest]
        for row in actual:
            assert row['complete'] and row['exit_code']==0
            output=run/(phase+'.'+row['id']+'.output')
            assert sha(output)==row['integrity_sha256']
            if phase not in ['01-preflight','02-state','03-capabilities']:
                args=shlex.split(row['command'])
                literals=[node.s for node in ast.walk(ast.parse(args[3])) if isinstance(node,ast.Str)]
                assert len(literals)==1
                source=gzip.decompress(base64.b64decode(literals[0])).decode()
                assert source==(run/'action_sources'/(phase+'.'+row['id']+'.py')).read_text()
            commands.append({'phase':phase,'id':row['id'],'sha256':sha(output),'exit_code':0})
    for name,digest in prepared['manifest_hashes'].items():assert sha(run/name)==digest
    for name,digest in prepared['source_hashes'].items():assert sha(run/name)==digest
    transfer=json.loads((run/'07-transfer-bundle.result.json').read_text())
    assert transfer['complete'] and transfer['expected_sha256']==prepared['test_archive']['sha256']
    assert transfer['bytes']==prepared['test_archive']['bytes']
    assert transfer['frames_acknowledged']==(transfer['bytes']+3071)//3072
    new_kernel=set()
    for output in run.glob('*.output'):
        new_kernel.update(kernel(output.read_text()))
    initial_kernel=(run/'01-preflight.kernel_before.output').read_text().splitlines()
    property_warnings={line for line in initial_kernel if 'memory leak will occur' in line}
    property_warnings.update(line for line in new_kernel if 'memory leak will occur' in line)
    old=json.loads((run/'10-remove-original-app.review.json').read_text())['commands'][0]
    assert len(old['refcount_errors'])<=1 and not old['other_error_lines'] and not old['exception_lines']
    repaired=json.loads((run/'12-load-repaired-module.review.json').read_text())['commands'][0]
    repair_epoch=repaired['uptime_before']
    new_refcount=[]
    new_exceptions=[]
    for line in sorted(new_kernel):
        timed=re.match(r'^\[\s*([0-9.]+)\]',line)
        if not timed or float(timed[1])<repair_epoch:continue
        if 'expected refcount' in line:new_refcount.append(line)
        if re.search(r'BUG:|Oops:|Unable to handle|Kernel panic|Call trace:',line):new_exceptions.append(line)
    assert not new_refcount and not new_exceptions
    removed=json.loads((run/'20-remove-m3.review.json').read_text())['commands'][0]
    assert not removed['refcount_errors'] and not removed['other_error_lines'] and not removed['exception_lines']
    scratch=[]
    for line in (run/'16-m3-scratch.m3-scratch.output').read_text().splitlines():
        if line.startswith('{'):
            row=json.loads(line)
            if row.get('event') in ['write32','read32','scratch_original_saved','scratch_original_restored','scratch_pass']:
                scratch.append(row)
    writes=[row['value'] for row in scratch if row['event']=='write32']
    assert writes==['0x00000000','0xffffffff','0x55aa33cc','0xaa55cc33',controller['scratch_original']]
    final=json.loads((run/'25-final-state.drivers_and_parameters.output').read_text())
    original=json.loads((run/'02-state.drivers_and_parameters.output').read_text())
    for key in ['root_device','loaded_srcversion','zocl_parameters','fpga_state','firmware_name','vart_conf']:assert final[key]==original[key]
    original_hashes={row['path']:row['sha256'] for row in map(json.loads,(run/'02-state.baseline_hashes.output').read_text().splitlines())}
    final_hashes={row['path']:row['sha256'] for row in map(json.loads,(run/'25-final-state.baseline_hashes.output').read_text().splitlines())}
    assert original_hashes==final_hashes
    installed=[json.loads(line) for line in (run/'26-post-review.installed_hashes.output').read_text().splitlines()]
    assert {row['path']:row['sha256'] for row in installed}=={
        '/'+row['path']:row['sha256'] for row in prepared['candidate_runtime']['runtime_files']}
    manager_text=(run/'26-post-review.manager_logs.output').read_text()
    discovery=json.loads(re.search(r'^MANAGER_DISCOVERY (.*)$',manager_text,re.M)[1])
    initial_uptime=float(original['uptime'].split()[0])
    manager_error_lines=[]
    for line in manager_text.splitlines():
        timed=re.match(r'^\[\s*([0-9.]+)\]',line)
        if timed and float(timed[1])>=initial_uptime and re.search(r'ERROR|error|Failed|failed',line):
            manager_error_lines.append(line)
    load_warnings={phase:sum(len(row['property_warnings']) for row in json.loads((run/(phase+'.review.json')).read_text())['commands'])
                   for phase in ['13-load-m3','23-restore-official-app']}
    summary={'status':'m3_finite_board_validation_passed_and_original_baseline_restored',
        'reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'board_verified':True,'successful_commands':len(commands),'command_evidence':commands,
        'scope':'one M3 load; full-width SCRATCH and same-model serial DPU tests; original baseline restored',
        'test_archive_transfer':{k:transfer[k] for k in ['bytes','expected_sha256','frames_acknowledged','complete']},
        'dpu_identity':json.loads((run/'14-m3-query.comparison.json').read_text()),
        'classification':json.loads((run/'17-m3-functional.comparison.json').read_text()),
        'scratch_original':controller['scratch_original'],'scratch_write_sequence':writes,
        'scratch_restored_and_unchanged_after_inference':True,
        'performance':{'official':controller['06-official-performance'],'m3':controller['18-m3-performance']},
        'performance_median_delta_percent':controller['performance_median_delta_percent'],
        'old_driver_exit_refcount_errors':old['refcount_errors'],
        'repaired_epoch_uptime':repair_epoch,'new_post_repair_refcount_errors':new_refcount,
        'm3_remove_refcount_errors':removed['refcount_errors'],
        'property_warnings':{'unique_observed_lines':len(property_warnings),'new_per_load':load_warnings},
        'recovery':final,'baseline_file_count':len(original_hashes),'baseline_file_hashes_unchanged':True,
        'installed_m3_firmware_hashes_unchanged':True,
        'manager_log_discovery':discovery,'manager_error_like_lines_current_run':sorted(set(manager_error_lines)),
        'board_work_directory':json.loads((run/'run.json').read_text())['board_work_directory'],
        'remaining':['No permanent repaired-driver installation','No concurrent CPU/DPU stress or byte-strobe verification',
                     'Existing DRC warnings and external timing gaps remain','No PWM, motor/actuator, external interfaces or long-running acceptance']}
    destination=run/'board_validation_summary.json'
    assert not destination.exists(),'Refusing to overwrite final evidence'
    destination.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:summary[k] for k in ['status','board_verified','successful_commands','scratch_original','performance_median_delta_percent','new_post_repair_refcount_errors','baseline_file_hashes_unchanged']},ensure_ascii=False))


if __name__=='__main__':
    main()
