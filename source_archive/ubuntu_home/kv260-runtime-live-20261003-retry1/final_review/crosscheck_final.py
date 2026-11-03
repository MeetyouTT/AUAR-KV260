"""Read-only final cross-check of recovered runtime evidence. Writes only this new review."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT=Path('/home/ghmd/kv260-runtime-live-20261003-retry1')
OUT=ROOT/'final_review'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
summary_path=ROOT/'analysis/summary.json'
summary_before=sha(summary_path)
summary=json.loads(summary_path.read_text())
manifest=json.loads((ROOT/'board_evidence_manifest.json').read_text())
evidence=ROOT/'board_evidence'
checks=[]
def checked(condition,name):
    checks.append({'check':name,'passed':bool(condition)})
    assert condition,name
archive=ROOT/'board_evidence.tar.xz'
checked(archive.stat().st_size==522748 and sha(archive)==manifest['archive_sha256']==
        '3384ec011a254ddb2b6baaf489d23ade09844c385e5363af495625f6ccb3b3b0','selected archive SHA/bytes')
checked(len(manifest['members'])==3480,'manifest member count')
actual_names={str(p.relative_to(evidence)) for p in evidence.rglob('*') if p.is_file()}
checked(actual_names==set(manifest['members']),'recovered member set')
for name,value in manifest['members'].items():
    path=evidence/name
    assert path.stat().st_size==value['bytes'] and sha(path)==value['sha256'],name
checks.append({'check':'all 3480 recovered files bytes/SHA','passed':True})
with tarfile.open(str(archive),'r:xz') as stream:
    members=stream.getmembers()
    checked(len(members)==3480 and {m.name for m in members}==set(manifest['members']),
            'XZ archive member set')
    for member in members:
        assert member.isfile()
        raw=stream.extractfile(member).read()
        value=manifest['members'][member.name]
        assert len(raw)==value['bytes'] and hashlib.sha256(raw).hexdigest()==value['sha256'],member.name
checks.append({'check':'all 3480 XZ member payload bytes/SHA','passed':True})
checked(summary['overall_pass'] and summary['baseline_restored'] and not summary['issues'],'summary outcome')
checked(summary['cycles']['raw_remove_count']==summary['cycles']['raw_load_count']==30,'30 normal reloads')
checked(summary['sustained']['inferences_completed']==872 and summary['sustained']['elapsed_seconds']>=1800,
        'sustained duration and inference count')
top5=[['258','0.949879'],['270','0.00931229'],['259','0.00821807'],['257','0.00498451'],['279','0.00388194']]
raw_queries=0;raw_classes=0
for path in (evidence/'agent_logs').rglob('*.json'):
    if not re.fullmatch(r'\d{6}-.+\.json',path.name):continue
    data=json.loads(path.read_text())
    assert data['returncode']==0 and not data['timed_out']
    for channel in ['stdout','stderr']:
        assert sha(path.parent/data[channel])==data[channel+'_sha256']
    if data['argv']==['xdputil','query']:
        query=json.loads((path.parent/data['stdout']).read_text())
        k=query['kernels'][0]
        assert len(query['kernels'])==query['DPU IP Spec']['DPU Core Count']==1
        assert k['fingerprint']=='0x101000056010407' and k['cu_addr']=='0xa0010000'
        assert k['DPU Arch']=='DPUCZDX8G_ISA1_B4096'
        assert k['DPU Frequency (MHz)']==k['XRT Frequency (MHz)']==300
        assert query['DPU IP Spec']['git commit id']==('7d32c41' if path.parent.name=='50-m3-functional' else 'ce8dd1')
        raw_queries+=1
    if data['argv'] and data['argv'][0].endswith('/test_jpeg_classification'):
        text=(path.parent/data['stdout']).read_text()+'\n'+(path.parent/data['stderr']).read_text()
        actual=[list(p) for p in re.findall(r'r[.]index +([0-9]+).*r[.]score +([0-9.eE+-]+)',text)]
        assert actual==top5
        raw_classes+=1
checked(raw_queries==35 and raw_classes==905,'35 raw DPU queries / 905 raw full Top-5 matches')
samples=[]
for path in (evidence/'agent_logs/40-sustained-inference').glob('*.sample.json'):
    value=json.loads(path.read_text());value['source']=str(path.relative_to(evidence));samples.append(value)
samples.sort(key=lambda v:float(v['uptime'].split()[0]))
checked(len(samples)==60,'60 long observation samples')
checked({(s['pid'],s['process_start_ticks']) for s in samples}=={(28924,'2937846')},'stable source PID/starttime')
checked({s['VmRSS'] for s in samples}=={'9524 kB'} and {s['VmSize'] for s in samples}=={'90584 kB'},
        'long phase daemon RSS/VmSize')
checked({s['watch_count'] for s in samples}=={5} and {s['fd_count'] for s in samples}=={7},
        'long phase watch/FD count')
checked({s['zocl_refcnt'] for s in samples}=={'0'} and
        {s['zocl_srcversion'] for s in samples}=={'9BDC942A6014BCCBD1DCB78'},'long phase fixed ZOCL/refcount')
memory={}
for key in ['MemAvailable','Slab','SReclaimable','SUnreclaim']:
    values=[int(s['memory'][key].split()[0]) for s in samples]
    memory[key]={'unit':'kB','first':values[0],'last':values[-1],
                 'min':min(values),'max':max(values),'delta':values[-1]-values[0]}
checked(memory['Slab']['delta']==memory['SReclaimable']['delta']+memory['SUnreclaim']['delta'],
        'slab split reconciles')
checked(memory['MemAvailable']['delta']==-40684 and memory['Slab']['delta']==4676 and
        memory['SReclaimable']['delta']==5120 and memory['SUnreclaim']['delta']==-444,'memory endpoint changes')
candidate=evidence/'candidate-manager.log'
candidate_meta=json.loads((evidence/'agent_logs/60-restore/candidate-final-log.json').read_text())
checked(candidate.stat().st_size==2708388 and sha(candidate)==candidate_meta['sha256']==
        '135a3f4b58f729fd8065300640f6f3a48d789be56fcd32e1d8c2afd01f2cd7ae' and
        candidate_meta['flushed_with']=='SIGINT' and not candidate_meta['ERROR_lines'] and
        not any('ERROR:' in line for line in candidate.read_text(errors='replace').splitlines()),
        'SIGINT-flushed complete candidate log ERROR0')
checked(summary['kernel']['review_count']==165 and not summary['kernel']['unexpected_error_events_unique'] and
        summary['kernel']['permitted_original_error_events_unique']==1 and
        summary['kernel']['property_warning_events_unique']==544,'kernel review diagnostics')
restore=json.loads((evidence/'agent_logs/60-restore/result.json').read_text())
cfg=json.loads((evidence/'config.json').read_text())
checked(restore['original_baseline_restored'] and len(restore['original_hashes'])==26 and
        restore['original_hashes']==cfg['stock_hashes26'] and restore['boot_id']==cfg['boot_id']==
        '64083069-98b7-409b-a455-b7b3b7158745' and restore['driver']=='0991D1B457855C8987936E6' and
        restore['active']==[['kv260-benchmark-b4096',0]],'original baseline 26 files/boot/module/app')
checked(summary_before==sha(summary_path),'completed summary unchanged')
report={'host_review_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'finite_experiment_crosscheck_passed':True,'original_baseline_restored':True,
        'summary_sha256':summary_before,'checks':checks,'long_phase_memory':memory,
        'raw_queries':raw_queries,'raw_full_top5_classifications':raw_classes,
        'long_samples':len(samples),'notes':[
            'RSS is constant during the sustained phase; across all 92 candidate samples RSS changes 9476 to 9524 kB.',
            'Reclaimable slab grows 5120 kB and unreclaimable slab falls 444 kB; this reconciles the 4676 kB Slab increase.',
            'MemAvailable falls 40684 kB. These samples omit Cached/Buffers/Dirty, so they do not establish a complete cause or rule out all leaks.',
            '544 existing overlay property warnings remain; no new target refcount errors after the fixed module.',
            'Finite reversible runtime observation is not permanent deployment, reboot validation, full timing/DRC approval, a new FPS benchmark or PWM validation.']}
with (OUT/'FINAL_CROSSCHECK.json').open('x') as stream:stream.write(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':True,'checks':len(checks),'memory':memory,
                 'output':str(OUT/'FINAL_CROSSCHECK.json')},indent=2))
