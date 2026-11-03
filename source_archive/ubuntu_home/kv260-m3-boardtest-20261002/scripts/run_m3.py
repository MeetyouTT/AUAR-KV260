#!/usr/bin/env python3
"""Run the frozen single-load M3 validation and original baseline recovery."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL='0991D1B457855C8987936E6'
OFFICIAL='kv260-benchmark-b4096'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def top5(path):
    return re.findall(r'r[.]index +([0-9]+).*r[.]score +([0-9.eE+-]+)',path.read_text())


def evidence(run,phase):
    rows=[json.loads(line) for line in (run/(phase+'.results.jsonl')).read_text().splitlines()]
    commands=[row for row in rows if row.get('type')=='command']
    manifest=json.loads((run/(phase+'.commands.json')).read_text())
    assert any(row.get('type')=='connection' and row.get('ready') for row in rows)
    assert [row['id'] for row in commands]==[row['id'] for row in manifest]
    assert [row['command'] for row in commands]==[row['command'] for row in manifest]
    for row in commands:
        assert row['complete'] and row['exit_code']==0,'Failed or incomplete command: '+phase
        assert sha(run/(phase+'.'+row['id']+'.output'))==row['integrity_sha256'],'Decoded output changed'
    return commands


def performance(run,phase):
    result={}
    for threads in (1,2):
        values=[]
        for repeat in (1,2,3):
            text=(run/(phase+'.t%d_r%d.output'%(threads,repeat))).read_text()
            values.append(float(re.search(r'FPS=([0-9.]+)',text)[1]))
        result[str(threads)]={'fps':values,'median_fps':statistics.median(values)}
    destination=run/(phase+'.summary.json')
    assert not destination.exists()
    destination.write_text(json.dumps(result,indent=2)+'\n')
    return result


def query_check(run,phase,candidate):
    query=json.loads((run/(phase+'.dpu_query.output')).read_text())
    assert query['DPU IP Spec']['DPU Core Count']==1 and len(query['kernels'])==1
    kernel=query['kernels'][0]
    assert kernel['DPU Arch']=='DPUCZDX8G_ISA1_B4096' and kernel['fingerprint']=='0x101000056010407'
    assert kernel['cu_addr']=='0xa0010000' and kernel['DPU Frequency (MHz)']==300
    assert kernel['XRT Frequency (MHz)']==300 and query['DPU IP Spec']['IP version']=='v4.1.0'
    spec=query['DPU IP Spec']
    assert spec['git commit id']==('7d32c41' if candidate else 'ce8dd1')
    assert spec['generation timestamp']==('2023-02-21 21-30-00' if candidate else '2022-11-30 19-15-00')
    return {'architecture_fingerprint_address_frequency_match':True,'ip_spec':spec}


def events(path):
    rows=[]
    for line in path.read_text().splitlines():
        if line.startswith('{'):
            row=json.loads(line)
            if 'event' in row:rows.append(row)
    return rows


def main():
    run=Path(sys.argv[1]).resolve()
    started=run/'controller.started.json'
    assert not started.exists(),'No automatic restart or repeat of board actions'
    prepared=json.loads((run/'preparation.json').read_text())
    for name,digest in prepared['manifest_hashes'].items():assert sha(run/name)==digest
    for name,digest in prepared['source_hashes'].items():assert sha(run/name)==digest
    phases=prepared['ordered_phases']
    status={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'runner_sha256':sha(Path(__file__)),'collector_sha256':sha(run/'collect_serial.py'),
            'reviewer_sha256':sha(ROOT/'scripts/review_board_phase.py'),
            'ordered_phases':phases,'completed_phases':[],'passed':False,'review_issues':[]}
    started.write_text(json.dumps(status,indent=2)+'\n')
    epoch=float(json.loads((run/'02-state.drivers_and_parameters.output').read_text())['uptime'].split()[0])
    expected=top5(Path('/home/ghmd/kv260-overlay-repair-20261002/evidence/board_validation_20261003T005805Z/03-baseline-functional.classification.output'))
    assert len(expected)==5
    try:
        for phase in phases:
            print('START FROZEN PHASE '+phase,flush=True)
            if phase=='07-transfer-bundle':
                subprocess.run([sys.executable,str(run/'transfer_bundle.py')],check=True,cwd=str(run))
                transfer=json.loads((run/'07-transfer-bundle.result.json').read_text())
                assert transfer['complete'] and transfer['expected_sha256']==prepared['test_archive']['sha256']
                commands=[]
            else:
                subprocess.run([sys.executable,str(run/'collect_serial.py'),phase],check=True,cwd=str(run))
                commands=evidence(run,phase)
            snapshots=[row for row in commands if 'AFTER_DMESG_BEGIN\n' in (row.get('output') or '')]
            if snapshots:
                subprocess.run([sys.executable,str(ROOT/'scripts/review_board_phase.py'),str(run),phase,str(epoch)],check=True)
                review=json.loads((run/(phase+'.review.json')).read_text())
                for row in review['commands']:
                    if row['uptime_after'] is None:continue
                    assert row['kernel_interval_isolated']
                    assert not row['exception_lines'] and not row['other_error_lines'],'New kernel error; stop'
                    if phase=='10-remove-original-app':
                        assert len(row['refcount_errors'])<=1
                        assert all('expected refcount 1 instead of 2' in line and '/axi/zyxclmm_drm' in line for line in row['refcount_errors'])
                    else:
                        assert not row['refcount_errors'],'New reference error after repair; stop'
                    epoch=row['uptime_after']
            if phase in ('05-official-functional','17-m3-functional','24-restored-functional'):
                assert top5(run/(phase+'.classification.output'))==expected,'Classification differs'
                comparison=query_check(run,phase,phase=='17-m3-functional')
                comparison.update({'top5_match':True,'top5':expected})
                (run/(phase+'.comparison.json')).write_text(json.dumps(comparison,indent=2)+'\n')
            if phase=='14-m3-query':
                comparison=query_check(run,phase,True)
                output=(run/'14-m3-query.metadata_after_query.output').read_text()
                uuid=prepared['candidate_runtime']['xclbin_uuid']
                assert uuid.replace('-','') in output.lower().replace('-',''),'Candidate UUID missing from captured kernel metadata'
                comparison['uuid_observed_in_kernel_log']=uuid
                (run/(phase+'.comparison.json')).write_text(json.dumps(comparison,indent=2)+'\n')
            if phase=='15-m3-identity':
                rows=events(run/'15-m3-identity.m3-identity.output')
                assert any(row['event']=='identity_pass' for row in rows)
            if phase=='16-m3-scratch':
                rows=events(run/'16-m3-scratch.m3-scratch.output')
                saved=[row['value'] for row in rows if row['event']=='scratch_original_saved']
                restored=[row['value'] for row in rows if row['event']=='scratch_original_restored']
                assert len(saved)==1 and saved==restored
                assert any(row['event']=='scratch_pass' for row in rows)
                status['scratch_original']=saved[0]
            if phase in ('06-official-performance','18-m3-performance'):
                status[phase]=performance(run,phase)
                if phase=='18-m3-performance':
                    ratios={t:100*(status[phase][t]['median_fps']/status['06-official-performance'][t]['median_fps']-1) for t in ('1','2')}
                    status['performance_median_delta_percent']=ratios
                    if any(abs(value)>=10 for value in ratios.values()):status['review_issues'].append('Performance median differs by at least 10%; restore baseline and review evidence')
            if phase=='19-m3-post-check':
                text=(run/'19-m3-post-check.m3-post-check.output').read_text()
                check=json.loads(re.search(r'^POST_CHECK (.*)$',text,re.M)[1])
                assert check['identity']==[0x41555241,0x10000,0xa5078450]
                assert check['scratch']==status['scratch_original'],'SCRATCH changed during inference'
            if phase=='25-final-state':
                final=json.loads((run/'25-final-state.drivers_and_parameters.output').read_text())
                original=json.loads((run/'02-state.drivers_and_parameters.output').read_text())
                for key in ['root_device','loaded_srcversion','zocl_parameters','fpga_state','firmware_name','vart_conf']:
                    assert final[key]==original[key],'Recovery mismatch: '+key
                before={row['path']:row['sha256'] for row in map(json.loads,(run/'02-state.baseline_hashes.output').read_text().splitlines())}
                after={row['path']:row['sha256'] for row in map(json.loads,(run/'25-final-state.baseline_hashes.output').read_text().splitlines())}
                assert before==after,'Original file hashes changed'
                status['original_baseline_restored']=True
                status['baseline_file_hashes_unchanged']=True
            status['completed_phases'].append(phase)
            (run/'controller.progress.json').write_text(json.dumps(status,indent=2)+'\n')
            print('PHASE EVIDENCE PASSED '+phase,flush=True)
        status['passed']=not status['review_issues']
        print('M3 FINITE VALIDATION AND ORIGINAL BASELINE RECOVERY FINISHED',flush=True)
    except Exception as error:
        status['error']=str(error)
        print('STOPPED WITHOUT RETRY: '+str(error),flush=True)
        return 1
    finally:
        status['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (run/'controller.result.json').write_text(json.dumps(status,indent=2)+'\n')
    return 0 if status['passed'] else 2


if __name__=='__main__':
    sys.exit(main())
