"""Bounded tracefs lifecycle/cost check on an owned non-DPU fixture only."""
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

SOURCE=Path(__file__).resolve()
TOKEN=hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
ROOT=Path('/home/root/aura-vision-persistent-20261023/uprobe8-isolated')/TOKEN
TRACE=Path('/sys/kernel/tracing')
GROUP='aura_iso_'+TOKEN
INSTANCE=TRACE/'instances'/GROUP
GUARD='aura-uprobe-cleanup-'+TOKEN
BOOT='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
NAMES=('native_enter','native_return','restore_enter','restore_return','wait_enter','wait_native_enter','wait_native_return','wait_cleanup_end')
FIXTURE=r'''
#include <stdint.h>
static volatile uint64_t count;
__attribute__((noinline)) void native_enter(void) { count++; }
__attribute__((noinline)) void native_return(void) { count++; }
__attribute__((noinline)) void restore_enter(void) { count++; }
__attribute__((noinline)) void restore_return(void) { count++; }
__attribute__((noinline)) void wait_enter(void) { count++; }
__attribute__((noinline)) void wait_native_enter(void) { count++; }
__attribute__((noinline)) void wait_native_return(void) { count++; }
__attribute__((noinline)) void wait_cleanup_end(void) { count++; }
void step(void) { native_enter();native_return();restore_enter();restore_return();wait_enter();wait_native_enter();wait_native_return();wait_cleanup_end(); }
uint64_t value(void) { return count; }
'''

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def command(args,timeout=15):
    return subprocess.check_output(args,timeout=timeout,stderr=subprocess.STDOUT,text=True).strip()
def write(path,value,append=False):
    descriptor=None
    try:
        # Text/FileIO append can seek to EOF, which tracefs seq files reject.
        # Match shell >>: append one bounded command without seeking/truncating.
        flags=os.O_WRONLY|os.O_CLOEXEC|(os.O_APPEND if append else os.O_TRUNC)
        descriptor=os.open(str(path),flags)
        raw=(value+'\n').encode()
        if os.write(descriptor,raw)!=len(raw):raise OSError('Partial tracefs command write')
    except OSError as error:
        raise RuntimeError('tracefs write failed: '+str(path)+' value='+repr(value)+' '+str(error)) from error
    finally:
        if descriptor is not None:os.close(descriptor)
def save(path,value):
    temp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
    with temp.open('x') as stream:
        json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)
def definitions():return (TRACE/'uprobe_events').read_text().splitlines()
def owned_definitions():
    return [line for line in definitions() if len(line.split()) and line.split()[0].split(':',1)[-1].startswith(GROUP+'/')]
def same_target(actual,expected):
    try:
        ap,ao=actual.rsplit(':',1);ep,eo=expected.rsplit(':',1)
        return ap==ep and int(ao,16)==int(eo,16)
    except (ValueError,AttributeError):return False
def cleanup():
    """Delete only events whose saved path/offset still match this check."""
    meta_path=ROOT/'ownership.json'
    if not meta_path.exists():return {'passed':not INSTANCE.exists() and not owned_definitions(),'nothing_owned':True}
    meta=json.loads(meta_path.read_text())
    assert meta['source_sha256']==sha(SOURCE) and meta['group']==GROUP
    assert meta['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    errors=[]
    if INSTANCE.exists():
        for name in NAMES:
            path=INSTANCE/'events'/GROUP/name/'enable'
            if path.exists():
                try:write(path,'0')
                except Exception as error:errors.append(type(error).__name__+': disable '+name)
        try:write(INSTANCE/'tracing_on','0');INSTANCE.rmdir()
        except Exception as error:errors.append(type(error).__name__+': remove own instance')
    for line in owned_definitions():
        fields=line.split();name=fields[0].split('/',1)[1]
        expected=meta['event_targets'].get(name)
        if len(fields)!=2 or expected is None or not same_target(fields[1],expected):
            errors.append('Ownership mismatch; retained '+name);continue
        try:write(TRACE/'uprobe_events','-:'+GROUP+'/'+name,True)
        except Exception as error:errors.append(type(error).__name__+': remove '+name)
    result={'passed':not errors and not INSTANCE.exists() and not owned_definitions(),'errors':errors,
        'instance_remaining':INSTANCE.exists(),'own_events_remaining':len(owned_definitions())}
    save(ROOT/'cleanup.json',result);return result

def metrics(values):
    ordered=sorted(values)
    return {'count':len(values),'mean_ns':statistics.mean(values),
        'p99_ns':ordered[min(len(ordered)-1,int(.99*len(ordered)))],'maximum_ns':max(values)}
def measure(step,n=500):
    cpu=[];wall=[]
    for _ in range(n):
        w=time.monotonic_ns();c=time.thread_time_ns();step()
        cpu.append(time.thread_time_ns()-c);wall.append(time.monotonic_ns()-w)
    return {'thread_cpu':metrics(cpu),'wall':metrics(wall)}
def global_state():
    names=('tracing_on','current_tracer','trace_clock','set_event_pid')
    return {'uprobe_definitions_sha256':hashlib.sha256('\n'.join(definitions()).encode()).hexdigest(),
        **{name:(TRACE/name).read_text() for name in names}}

def run():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    assert not (ROOT/'report.json').exists(),'One execution per exact helper'
    assert not INSTANCE.exists() and not owned_definitions(),'Refuse pre-existing names'
    before=global_state()
    source=ROOT/'fixture.c';source.write_text(FIXTURE)
    library=ROOT/'fixture.so'
    command(['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(library)])
    symbols=command(['nm','-D','--defined-only',str(library)])
    offsets={line.split()[2]:int(line.split()[0],16) for line in symbols.splitlines() if len(line.split())==3}
    # Verify ELF VA to file offset mapping, rather than assuming equality.
    loads=[]
    raw=command(['readelf','-lW',str(library)])
    for line in raw.splitlines():
        fields=line.split()
        if fields and fields[0]=='LOAD':
            loads.append(tuple(int(fields[i],16) for i in (1,2,4)))
    targets={}
    for name in NAMES:
        va=offsets[name];matches=[off+va-base for off,base,size in loads if base<=va<base+size]
        assert len(matches)==1
        targets[name]=str(library)+':0x'+format(matches[0],'x')
    native=ctypes.CDLL(str(library));native.step.argtypes=[];native.step.restype=None
    native.value.argtypes=[];native.value.restype=ctypes.c_uint64
    for _ in range(10):native.step()
    baseline=measure(native.step)
    report={'complete':False,'passed':False,'scope':'ISOLATED_NON_DPU_FIXTURE_ONLY',
        'production_changes':False,'dpu_jobs_submitted':0,'boot':BOOT,'source_sha256':sha(SOURCE),
        'fixture_sha256':sha(library),'target_pid':os.getpid(),'events':targets,'baseline':baseline,
        'predeclared_gate':{'additional_mean_cpu_ns_per_eight_probes':100000,'p99_cpu_ns':500000,
            'expected_complete_cycles':500,'require_no_lost_events':True}}
    save(ROOT/'ownership.json',{'source_sha256':sha(SOURCE),'group':GROUP,'boot':BOOT,'event_targets':targets})
    save(ROOT/'report.json',report)
    armed=False
    try:
        command(['systemd-run','--unit='+GUARD,'--on-active=45s','--property=RuntimeMaxSec=30',
            '/usr/bin/python3','-B',str(SOURCE),'--cleanup'])
        assert command(['systemctl','show',GUARD+'.timer','-p','ActiveState','--value'])=='active'
        armed=True
        INSTANCE.mkdir()
        write(INSTANCE/'tracing_on','0');write(INSTANCE/'current_tracer','nop')
        write(INSTANCE/'buffer_size_kb','256');write(INSTANCE/'trace_clock','mono')
        precision=INSTANCE/'options'/'nsecs'
        if precision.exists():write(precision,'1')
        for name,target in targets.items():
            write(TRACE/'uprobe_events','p:'+GROUP+'/'+name+' '+target,True)
            event=INSTANCE/'events'/GROUP/name
            write(event/'filter','common_pid == '+str(os.getpid()))
            write(event/'enable','1')
        write(INSTANCE/'trace','');write(INSTANCE/'tracing_on','1')
        counter_before=native.value();tested=measure(native.step);counter_after=native.value()
        write(INSTANCE/'tracing_on','0')
        trace=(INSTANCE/'trace').read_text()
        stats={p.parent.name:p.read_text() for p in (INSTANCE/'per_cpu').glob('cpu*/stats')}
        pattern=re.compile(r'\s(\d+)\.(\d+):\s+(?:'+GROUP+r':)?('+('|'.join(NAMES))+r'):')
        events=[];fraction_digits=set()
        for line in trace.splitlines():
            match=pattern.search(line)
            if match:
                sec,fraction,name=match.groups()
                assert len(fraction)<=9
                fraction_digits.add(len(fraction))
                events.append([int(sec)*1000000000+int(fraction.ljust(9,'0')),name])
        ordered=len(events)==500*len(NAMES) and all(name==NAMES[i%len(NAMES)] for i,(_,name) in enumerate(events))
        assert stats,'No per-CPU loss counters collected'
        lost={}
        for cpu,value in stats.items():
            lost[cpu]={key:int(re.search(r'^'+re.escape(key)+r':\s*(\d+)',value,re.M).group(1))
                for key in ('overrun','commit overrun','dropped events')}
        added=tested['thread_cpu']['mean_ns']-baseline['thread_cpu']['mean_ns']
        report.update(tested=tested,additional_mean_cpu_ns=added,fixture_counter_delta=counter_after-counter_before,
            event_count=len(events),ordered_complete_cycles=ordered,lost_events=lost,numeric_events=events,
            displayed_fraction_digits=sorted(fraction_digits),
            timestamp_scope='Kernel trace text quantization as recorded; ns unit does not imply ns precision',
            cost_gate_passed=added<=100000 and tested['thread_cpu']['p99_ns']<=500000,
            trace_clock=(INSTANCE/'trace_clock').read_text().strip())
        report['measurement_passed']=(ordered and not any(count for row in lost.values() for count in row.values())
            and counter_after-counter_before==500*len(NAMES))
    except Exception as error:
        report['error']=type(error).__name__+': '+str(error)
    finally:
        report['cleanup']=cleanup()
        report['global_state_unchanged']=global_state()==before
        report['complete']=True
        report['passed']=(report.get('measurement_passed',False) and report.get('cost_gate_passed',False)
            and report['cleanup']['passed'] and report['global_state_unchanged'])
        save(ROOT/'report.json',report)
        if armed and report['cleanup']['passed']:
            command(['systemctl','stop',GUARD+'.timer'])
        report['guard_timer_state']=command(['systemctl','show',GUARD+'.timer','-p','ActiveState','--value'])
        save(ROOT/'report.json',report)
    return report

if __name__=='__main__':
    if sys.argv[1:]==['--cleanup']:
        print(json.dumps(cleanup()))
    else:
        assert not sys.argv[1:]
        ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
        with (ROOT/'controller.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result=run()
            print(json.dumps({k:v for k,v in result.items() if k!='numeric_events'}))
