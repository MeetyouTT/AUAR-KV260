#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read recovered evidence, verify it, and write new JSON/CSV. Never accesses the board."""
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path
import re

OFFICIAL='kv260-benchmark-b4096'
M3='kv260-benchmark-b4096-m3'
TOP5=[['258','0.949879'],['270','0.00931229'],['259','0.00821807'],
      ['257','0.00498451'],['279','0.00388194']]
CLASSIFIER='/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification'
IMAGE='/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'
PHASES=['10_start.py','20_functional.py','30_official_reload.py',
        '40_sustained_inference.py','50_m3_functional.py','60_restore.py']
RESULT_PHASES=['20-official-functional','30-official-reload','40-sustained-inference',
               '50-m3-functional','60-restore']
ERROR_RE=re.compile(r'BUG:|Oops:|Unable to handle|Kernel panic|Call trace:|ERROR|error|expected refcount')

def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):value.update(chunk)
    return value.hexdigest()

def analyze(root,output):
    root=root.resolve();output=output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    evidence=root/'board_evidence'
    issues=[]
    def require(condition,message,category='evidence'):
        if not condition:issues.append({'category':category,'message':message})
        return bool(condition)
    def read_json(path,required=True):
        try:return json.loads(path.read_text())
        except (OSError,ValueError) as error:
            if required:require(False,str(path)+': '+str(error))
            return {}
    def member_path(name):
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe member: '+name)
        target=evidence/relative
        if target.is_symlink() or evidence.resolve() not in target.resolve().parents:
            raise ValueError('Unsafe recovered path: '+name)
        return target
    manifest_path=root/'board_evidence_manifest.json'
    manifest=read_json(manifest_path)
    members=manifest.get('members',{})
    integrity=[]
    require(isinstance(members,dict) and bool(members),'Evidence manifest has no members','integrity')
    for name,expected in members.items():
        try:
            target=member_path(name)
            actual={'bytes':target.stat().st_size,'sha256':sha(target)}
            matches=actual==expected
            require(matches,'Manifest mismatch: '+name,'integrity')
            integrity.append(dict(name=name,expected=expected,actual=actual,matches=matches))
        except (OSError,ValueError) as error:
            require(False,'Manifest member unavailable: '+name+' '+str(error),'integrity')
            integrity.append({'name':name,'matches':False,'error':str(error)})
    actual_members={str(p.relative_to(evidence)) for p in evidence.rglob('*') if p.is_file()}
    require(actual_members==set(members),'Manifest and recovered member set differ','integrity')
    archive_format=manifest.get('archive_format','tar.gz')
    require(archive_format in ['tar.gz','tar.xz'],'Unsupported evidence archive format','integrity')
    archive=root/('board_evidence.tar.xz' if archive_format=='tar.xz' else 'board_evidence.tar.gz')
    archive_ok=False
    try:
        archive_ok=(archive.stat().st_size==manifest.get('archive_bytes') and
                    sha(archive)==manifest.get('archive_sha256'))
    except OSError:pass
    require(archive_ok,'Recovered archive SHA/size unavailable or mismatched','integrity')
    config=read_json(evidence/'config.json')
    require(manifest.get('work')==config.get('work'),'Manifest work and config work differ','integrity')
    package=read_json(root/'package_manifest.json')
    require(config and sha(evidence/'config.json')==package.get('config_sha256'),
            'Recovered config differs from reviewed package','integrity')
    status=read_json(evidence/'controller-status.json')
    require(status.get('state')=='complete','Controller state is not complete','controller')
    require(not status.get('failures'),'Controller records experiment/recovery failures','controller')
    require(status.get('completed_phases')==PHASES,'Controller lacks the full ordered phase list','controller')
    results={phase:read_json(evidence/'agent_logs'/phase/'result.json') for phase in RESULT_PHASES}
    for phase,result in results.items():
        require(result.get('passed') is True,'Phase not passed or missing: '+phase,'phases')

    ledger=[];queries=[];classifications=[]
    query_counts={phase:0 for phase in RESULT_PHASES}
    classification_counts={phase:0 for phase in RESULT_PHASES}
    def query_matches(value,app):
        try:
            spec=value['DPU IP Spec'];kernels=value['kernels']
            k=kernels[0]
            return (spec['DPU Core Count']==1 and len(kernels)==1 and
                spec['git commit id']==('7d32c41' if app==M3 else 'ce8dd1') and
                k['fingerprint']=='0x101000056010407' and k['cu_addr']=='0xa0010000' and
                k['DPU Arch']=='DPUCZDX8G_ISA1_B4096' and
                k['DPU Frequency (MHz)']==300 and k['XRT Frequency (MHz)']==300)
        except (KeyError,IndexError,TypeError):return False
    for path in sorted((evidence/'agent_logs').rglob('*.json')):
        if not re.fullmatch(r'\d{6}-.+\.json',path.name):continue
        meta=read_json(path);phase=path.parent.name
        valid=True;outputs={}
        for stream in ['stdout','stderr']:
            name=meta.get(stream)
            if not name or Path(name).name!=name:
                require(False,'Command stream path missing/unsafe: '+str(path),'commands');valid=False;continue
            stream_path=path.parent/name
            try:
                data=stream_path.read_bytes();outputs[stream]=data
                ok=sha(stream_path)==meta.get(stream+'_sha256')
                require(ok,'Command stream SHA mismatch: '+str(stream_path),'commands');valid=valid and ok
                require(str(stream_path.relative_to(evidence)) in members,'Raw stream absent from manifest','integrity')
            except OSError as error:
                require(False,'Missing raw stream: '+str(stream_path)+' '+str(error),'commands');valid=False
        ok=meta.get('returncode')==0 and not meta.get('timed_out',False)
        require(ok,'Failed/timed-out raw command: '+str(path),'commands');valid=valid and ok
        argv=meta.get('argv',[])
        row={'phase':phase,'metadata':str(path.relative_to(evidence)),
             'argv':argv,'returncode':meta.get('returncode'),'valid':valid}
        ledger.append(row)
        app=M3 if phase=='50-m3-functional' else OFFICIAL
        expected_firmware='/lib/firmware/xilinx/{0}/{0}.xclbin'.format(app)
        if argv==['xdputil','query']:
            query_counts[phase]=query_counts.get(phase,0)+1
            try:value=json.loads(outputs.get('stdout',b''))
            except (ValueError,UnicodeDecodeError):value={}
            match=query_matches(value,app) and meta.get('firmware')==expected_firmware
            require(match,'DPU query mismatch: '+str(path),'functional')
            queries.append(dict(row,app=app,matches=match,query=value))
        if argv and argv[0]==CLASSIFIER:
            classification_counts[phase]=classification_counts.get(phase,0)+1
            text=(outputs.get('stdout',b'')+b'\n'+outputs.get('stderr',b'')).decode('utf-8','replace')
            actual=[list(p) for p in re.findall(r'r[.]index +([0-9]+).*r[.]score +([0-9.eE+-]+)',text)]
            match=(actual==TOP5 and argv==[CLASSIFIER,'resnet18',IMAGE] and
                meta.get('firmware')==expected_firmware and meta.get('cwd')=='/home/root/kv260-test-20261001')
            require(match,'Raw full Top-5/command mismatch: '+str(path),'functional')
            classifications.append(dict(row,app=app,matches=match,top5=actual))
    cycle=results.get('30-official-reload',{})
    cycle_rows=cycle.get('samples',[])
    require(cycle.get('cycles')==30 and len(cycle_rows)==30 and
        [r.get('cycle') for r in cycle_rows]==list(range(1,31)),'30 cycle records incomplete','cycles')
    require(all(r.get('top5')==TOP5 for r in cycle_rows),'Cycle recorded Top-5 mismatch','cycles')
    for phase,expected in [('20-official-functional',1),('30-official-reload',30),('50-m3-functional',1),('60-restore',1)]:
        require(query_counts.get(phase)==expected,'Raw query count differs: '+phase,'functional')
        require(classification_counts.get(phase)==expected,'Raw classification count differs: '+phase,'functional')
    reload_remove=sum(r['phase']=='30-official-reload' and r['argv']==['dfx-mgr-client','-remove'] for r in ledger)
    reload_load=sum(r['phase']=='30-official-reload' and r['argv']==['dfx-mgr-client','-load',OFFICIAL] for r in ledger)
    require(reload_remove==30 and reload_load==30,'Raw normal reload remove/load counts differ from 30','cycles')
    sustained=results.get('40-sustained-inference',{})
    elapsed=sustained.get('elapsed_seconds')
    count=sustained.get('inferences_completed')
    require(isinstance(elapsed,(int,float)) and elapsed>=1800,'Sustained elapsed <1800 or unavailable','sustained')
    require(isinstance(count,int) and count>0 and classification_counts.get('40-sustained-inference')==count,
            'Sustained inference count and complete raw classifications differ','sustained')
    require(query_counts.get('40-sustained-inference')==2,'Sustained initial/final query missing','sustained')

    sample_rows=[]
    def kb(value,label):
        match=re.fullmatch(r'(\d+)\s+kB',value or '')
        require(bool(match),'Memory value unavailable/not kB: '+label,'sampling')
        return int(match[1]) if match else None
    for path in (evidence/'agent_logs').rglob('*.sample.json'):
        sample=read_json(path);phase=path.parent.name
        try:uptime=float(sample['uptime'].split()[0])
        except (KeyError,ValueError,IndexError,AttributeError):uptime=None
        require(uptime is not None,'Sample uptime missing: '+str(path),'sampling')
        watch=sum(len(set(fd.get('wd_hex',[]))) for fd in sample.get('inotify_fds',{}).values())
        require(watch==sample.get('watch_count')==config.get('expected_watches',5),
                'Sample inotify count differs: '+str(path),'sampling')
        for fd in sample.get('inotify_fds',{}).values():
            require(fd.get('unique')==len(set(fd.get('wd_hex',[]))) and fd.get('lines',0)>=fd.get('unique',0),
                    'Per-FD watch record inconsistent: '+str(path),'sampling')
        require(sample.get('zocl_srcversion')==config.get('fixed_srcversion') and
            sample.get('zocl_refcnt')=='0' and sample.get('zocl_params')=={'enable_xgq_ert':'1'},
            'Sample module state differs: '+str(path),'sampling')
        require(not sample.get('manager_error_lines'),'Sample manager ERROR: '+str(path),'sampling')
        memory=sample.get('memory',{})
        sample_rows.append({'phase':phase,'source':str(path.relative_to(evidence)),
            'utc':sample.get('utc'),'uptime_seconds':uptime,'pid':sample.get('pid'),
            'process_start_ticks':sample.get('process_start_ticks'),'watch_count':sample.get('watch_count'),
            'RSS_kB':kb(sample.get('VmRSS'),str(path)+':RSS'),
            'MemAvailable_kB':kb(memory.get('MemAvailable'),str(path)+':MemAvailable'),
            'Slab_kB':kb(memory.get('Slab'),str(path)+':Slab'),
            'SUnreclaim_kB':kb(memory.get('SUnreclaim'),str(path)+':SUnreclaim')})
    sample_rows.sort(key=lambda r:(r['uptime_seconds'] if r['uptime_seconds'] is not None else float('inf'),r['source']))
    identities={(r['pid'],r['process_start_ticks']) for r in sample_rows}
    require(len(identities)==1 and all(pid and tick for pid,tick in identities),
            'Candidate samples missing or manager PID/starttime changed','sampling')
    for phase,expected in [('20-official-functional',1),('30-official-reload',30),('50-m3-functional',1)]:
        require(sum(r['phase']==phase for r in sample_rows)==expected,'Sample count differs: '+phase,'sampling')
    long_rows=[r for r in sample_rows if r['phase']=='40-sustained-inference']
    require(len(long_rows)>=2 and len(sustained.get('samples',[]))==len(long_rows),
            'Sustained sample records incomplete','sampling')
    long_declared=sustained.get('samples',[])
    require(bool(long_declared) and isinstance(long_declared[-1].get('elapsed_seconds'),(int,float)) and
            long_declared[-1]['elapsed_seconds']>=1800 and long_declared[-1].get('inferences_completed')==count,
            'Final sustained sample elapsed/count incomplete','sampling')
    def stats(rows):
        result={'sample_count':len(rows)}
        if rows:result.update(first_sample=rows[0]['source'],last_sample=rows[-1]['source'])
        for key in ['watch_count','RSS_kB','MemAvailable_kB','Slab_kB','SUnreclaim_kB']:
            values=[r[key] for r in rows if r[key] is not None]
            result[key]={'first':rows[0][key] if rows else None,'last':rows[-1][key] if rows else None,
                         'min':min(values) if values else None,'max':max(values) if values else None}
        times=[r['uptime_seconds'] for r in rows if r['uptime_seconds'] is not None]
        result['sample_uptime_span_seconds']=times[-1]-times[0] if times else None
        result['largest_sample_gap_seconds']=max((b-a for a,b in zip(times,times[1:])),default=None)
        return result

    kernel_reviews=[];new_events=set();error_events=set();property_events=set();permitted_events=set()
    def kernel_events(review,label):
        fresh=review.get('new_lines',[])
        errors=[line for line in fresh if ERROR_RE.search(line)]
        properties=[line for line in fresh if 'memory leak will occur' in line]
        allowed=review.get('permitted_stock_remove_errors',review.get('permitted_original_remove_errors',[]))
        new_events.update(fresh);error_events.update(errors);property_events.update(properties);permitted_events.update(allowed)
        require(set(review.get('error_lines',review.get('new_error_lines',[])))==set(errors),
                'Kernel serialized error classification differs: '+label,'kernel')
        require(not review.get('continuity_lost',False) and review.get('continuity_confirmed',True),
                'Kernel continuity unavailable: '+label,'kernel')
        require(not [line for line in errors if line not in allowed],'Unexpected kernel error: '+label,'kernel')
        require(len(allowed)<=1 and all('expected refcount 1 instead of 2' in line and '/axi/zyxclmm_drm' in line for line in allowed),
                'Unapproved kernel error allowance: '+label,'kernel')
        require(not allowed or label in ['original-remove-review.json','agent_logs/60-restore/current-removed.kernel-review.json'],
                'Kernel allowance used outside original-driver removal: '+label,'kernel')
        kernel_reviews.append({'source':label,'new_lines':len(fresh),'error_lines':errors,
                               'property_warning_lines':properties,'permitted_errors':allowed})
    def local_board_path(name):
        value=Path(name);work=Path(config.get('work','/missing-work'))
        try:return member_path(str(value.relative_to(work)))
        except ValueError:
            require(False,'Board evidence path outside work: '+name,'kernel');return None
    for name in ['original-remove-review.json','candidate-start-review.json']:
        path=evidence/name
        review=read_json(path)
        if not review:continue
        kernel_events(review,name)
        before=local_board_path(review.get('before_log',''))
        after=local_board_path(review.get('after_log',''))
        if before and after:
            try:
                require(sha(before)==review.get('before_sha256') and sha(after)==review.get('after_sha256'),
                        'Start kernel raw-log SHA differs: '+name,'kernel')
                old=before.read_text().splitlines();new=after.read_text().splitlines()
                size=min(16,len(old));anchor=old[-size:] if size else []
                positions=[i+size for i in range(len(new)-size+1) if anchor and new[i:i+size]==anchor]
                require(len(positions)==1,'Start kernel raw unique overlap missing: '+name,'kernel')
                if len(positions)==1:
                    require(new[positions[0]:]==review.get('new_lines'),'Start kernel raw increment differs: '+name,'kernel')
            except OSError as error:require(False,'Start kernel raw-log missing: '+str(error),'kernel')
    for phase in RESULT_PHASES:
        paths=list((evidence/'agent_logs'/phase).glob('*.kernel-review.json'))
        paths.sort(key=lambda p:(read_json(p).get('utc',''),p.name))
        require(bool(paths),'Phase kernel review absent: '+phase,'kernel')
        previous=None
        for path in paths:
            review=read_json(path);label=str(path.relative_to(evidence))
            full=path.parent/review.get('full_log','missing-full-log')
            try:
                require(sha(full)==review.get('sha256'),'Kernel raw dmesg SHA differs: '+label,'kernel')
                lines=full.read_text().splitlines()
                if previous is not None:
                    size=min(16,len(previous));anchor=previous[-size:] if size else []
                    positions=[i+size for i in range(len(lines)-size+1) if anchor and lines[i:i+size]==anchor]
                    require(bool(positions),'Kernel raw overlap unavailable: '+label,'kernel')
                    if positions:require(lines[positions[-1]:]==review.get('new_lines'),
                                         'Kernel raw increment differs: '+label,'kernel')
                else:require(review.get('new_lines')==[],'Initial kernel review is not a baseline','kernel')
                previous=lines
            except OSError as error:require(False,'Kernel raw log missing: '+str(error),'kernel')
            kernel_events(review,label)

    final_log_review=read_json(evidence/'agent_logs/60-restore/candidate-final-log.json')
    log=evidence/'candidate-manager.log'
    final_errors=[]
    log_verified=False
    try:
        final_errors=[line for line in log.read_text(errors='replace').splitlines() if 'ERROR:' in line]
        log_verified=(sha(log)==final_log_review.get('sha256') and log.stat().st_size==final_log_review.get('bytes') and
                      final_errors==final_log_review.get('ERROR_lines') and final_log_review.get('flushed_with')=='SIGINT')
    except OSError:pass
    require(log_verified,'Flushed complete candidate log unavailable/mismatched','candidate-log')
    require(not final_errors,'Flushed complete candidate log contains ERROR','candidate-log')
    restored=results.get('60-restore',{})
    baseline=read_json(evidence/'baseline/state.json')
    restored_queries=[r for r in queries if r['phase']=='60-restore']
    restored_classes=[r for r in classifications if r['phase']=='60-restore']
    restore_raw_ok=(len(restored_queries)==len(restored_classes)==1 and
        all(r['matches'] and r['valid'] for r in restored_queries+restored_classes))
    restore_ok=(status.get('baseline_restored') is True and restored.get('original_baseline_restored') is True and
        restored.get('boot_id')==config.get('boot_id')==baseline.get('boot_id') and
        restored.get('original_hashes')==config.get('stock_hashes26') and len(config.get('stock_hashes26',{}))==26 and
        restored.get('driver')==config.get('stock_srcversion') and restored.get('active')==[[OFFICIAL,0]] and
        restored.get('top5')==TOP5 and query_matches(restored.get('query',{}),OFFICIAL) and
        restored.get('stock_files_overwritten') is False and restore_raw_ok and
        baseline.get('card_cid')=='0353445345333247805558c00401a100' and baseline.get('kernel')=='5.15.36-xilinx-v2022.2')
    require(restore_ok,'Baseline recovery proof incomplete or mismatched','recovery')
    require(not restored.get('recovery_diagnostics'),'Recovery diagnostics present','recovery')
    integrity_ok=(archive_ok and len(integrity)==len(members) and all(r['matches'] for r in integrity) and
        actual_members==set(members) and not any(r['category']=='integrity' for r in issues))
    overall=not issues
    summary={'host_analysis_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'root':str(root),'scope':'Offline aggregation of recovered finite board experiment',
        'overall_pass':overall,'baseline_reported_restored':status.get('baseline_restored') is True,
        'baseline_restored':bool(restore_ok and integrity_ok),'controller':status,
        'expected_boot_id':config.get('boot_id'),'manifest_sha256':sha(manifest_path) if manifest_path.exists() else None,
        'input_integrity':{'passed':integrity_ok,'archive_sha256':manifest.get('archive_sha256'),
                           'member_count':len(members),'members':integrity},
        'phases':{phase:{'passed':result.get('passed'),'result_present':bool(result)} for phase,result in results.items()},
        'functional':{'query_count':len(queries),'classification_count':len(classifications),
            'query_counts_by_phase':query_counts,'classification_counts_by_phase':classification_counts,
            'all_queries_match':bool(queries) and all(r['matches'] for r in queries),
            'all_top5_match':bool(classifications) and all(r['matches'] for r in classifications),
            'queries':queries,'classifications':classifications},
        'cycles':{'declared':cycle.get('cycles'),'records':len(cycle_rows),
                  'raw_remove_count':reload_remove,'raw_load_count':reload_load},
        'sustained':{'elapsed_seconds':elapsed,'inferences_completed':count,'samples':len(long_rows)},
        'sampling':{'candidate_pid_starttime_pairs':[list(v) for v in sorted(identities,key=str)],
            'overall':stats(sample_rows),'by_phase':{phase:stats([r for r in sample_rows if r['phase']==phase]) for phase in RESULT_PHASES}},
        'kernel':{'review_count':len(kernel_reviews),'new_events_unique':len(new_events),
            'counts_cover_all_required_intervals':not any(r['category']=='kernel' for r in issues),
            'error_events_unique':len(error_events),'permitted_original_error_events_unique':len(permitted_events),
            'unexpected_error_events_unique':sorted(error_events-permitted_events),
            'property_warning_events_unique':len(property_events),'property_warning_lines':sorted(property_events),
            'reviews':kernel_reviews},
        'candidate_final_log':{'verified':log_verified,'sha256':final_log_review.get('sha256'),
            'bytes':final_log_review.get('bytes'),'ERROR_lines':final_errors},
        'recovery':{'verified':restore_ok,'original_file_count':len(restored.get('original_hashes',{})),
                    'boot_id':restored.get('boot_id'),'driver':restored.get('driver'),
                    'diagnostics':restored.get('recovery_diagnostics')},
        'issues':issues,'limitations':['Finite observations do not prove absence of every memory leak.',
            'Inference loop is not a throughput benchmark.','Board wall-clock timestamps can differ from host time; sustained duration uses monotonic elapsed.']}
    (output/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    (output/'commands.json').write_text(json.dumps(ledger,indent=2)+'\n')
    with (output/'samples.csv').open('w',newline='') as stream:
        columns=['phase','source','utc','uptime_seconds','pid','process_start_ticks','watch_count',
                 'RSS_kB','MemAvailable_kB','Slab_kB','SUnreclaim_kB']
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows(sample_rows)
    with (output/'metrics.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['phase','metric','first','last','min','max','sample_count'])
        groups=dict(summary['sampling']['by_phase'],all_candidate=summary['sampling']['overall'])
        for phase,values in groups.items():
            for metric in ['watch_count','RSS_kB','MemAvailable_kB','Slab_kB','SUnreclaim_kB']:
                v=values[metric];writer.writerow([phase,metric,v['first'],v['last'],v['min'],v['max'],values['sample_count']])
    return summary

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path,help='New output directory; default ROOT/analysis; existing output is rejected')
    args=parser.parse_args()
    result=analyze(args.root,args.output or args.root/'analysis')
    print(json.dumps({'overall_pass':result['overall_pass'],'baseline_restored':result['baseline_restored'],
        'issues':len(result['issues']),'samples':result['sampling']['overall']['sample_count'],
        'classification_count':result['functional']['classification_count'],
        'output':str(args.output or args.root/'analysis')},indent=2))
    return 0 if result['overall_pass'] else 1

if __name__=='__main__':raise SystemExit(main())
