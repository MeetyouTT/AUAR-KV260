"""Bounded extension semantics and complete-call cost; no inference or devices."""
import gc,hashlib,importlib.util,json,math,os,signal,statistics,sys,threading,time
from pathlib import Path

sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT))
from _aura_schedprobe import Probe
from native_thread_probe import NativeThreadSchedProbe

def expect_error(call,error=RuntimeError):
    try:call()
    except error:return
    raise AssertionError('Expected '+error.__name__)
def fd_count():return len(list(Path('/proc/self/fd').iterdir()))
def percentiles(values):
    s=sorted(values);n=len(s)
    if not n:return {'count':0,'mean_ns':None,'p50_ns':None,'p95_ns':None,'p99_ns':None,'max_ns':None}
    return {'count':n,'mean_ns':statistics.mean(s),'p50_ns':s[math.ceil(n*.50)-1],
        'p95_ns':s[math.ceil(n*.95)-1],'p99_ns':s[math.ceil(n*.99)-1],'max_ns':s[-1]}

result={'scope':'ISOLATED_OBSERVER_SEMANTICS_AND_COST_NOT_PRODUCTION_OR_DPU_TEST',
        'predeclared_cost_gate':{'mean_cpu_ns':100_000,'p99_cpu_ns':500_000,'p99_wall_ns':1_000_000},
        'semantics':[],'cost':{}}
p=Probe();a=p.sample();assert p.owner==(os.getpid(),threading.get_native_id()) and not p.closed
assert len(a)==10 and all(type(n) is int and n>=0 for n in a)
assert a[8]>=a[1] and a[9]>=a[2]
result['semantics'].append('numeric_same_owner_ordered_clocks')
before=p.sample();time.sleep(.03);after=p.sample()
assert after[1]-before[1]>=25_000_000 and after[2]-before[2]<10_000_000
assert after[6]>before[6] and after[4]>=before[4]
result['sleep_interval']={'wall_ns':after[1]-before[1],'thread_cpu_ns':after[2]-before[2],
    'run_delay_ns':after[4]-before[4],'voluntary':after[6]-before[6],'involuntary':after[7]-before[7]}
result['semantics'].append('intentional_sleep_is_off_cpu_without_gil_claim')
before=p.sample();used=time.thread_time_ns();value=1
while time.thread_time_ns()-used<15_000_000:value=(value*17+31)%104729
after=p.sample();assert after[2]-before[2]>=14_000_000
result['busy_interval']={'wall_ns':after[1]-before[1],'thread_cpu_ns':after[2]-before[2],
    'run_delay_ns':after[4]-before[4]}
result['semantics'].append('cpu_clock_observes_busy_work')
errors=[]
def other_thread():
    try:
        expect_error(p.sample)
        q=Probe();raw=q.sample();assert raw[0]==threading.get_native_id() and raw[0]!=a[0];q.close()
    except BaseException as error:errors.append(str(error))
t=threading.Thread(target=other_thread);t.start();t.join(2);assert not t.is_alive() and not errors,errors
result['semantics'].append('cross_thread_rejected_fresh_thread_allowed')
child=os.fork()
if child==0:
    signal.alarm(2)
    try:
        expect_error(p.sample);q=Probe();assert q.sample()[0]==os.getpid();q.close();os._exit(0)
    except BaseException:os._exit(1)
_,status=os.waitpid(child,0);assert status==0
p.sample();result['semantics'].append('fork_inheritance_rejected_parent_and_fresh_child_valid')
fds=fd_count()
for _ in range(64):q=Probe();q.sample();q.close();q.close()
del q;gc.collect();assert fd_count()==fds
for _ in range(64):q=Probe();q.sample();del q
gc.collect();assert fd_count()==fds
result['semantics'].append('close_dealloc_no_descriptor_leak')
expect_error(lambda:Probe(1),TypeError);expect_error(lambda:Probe(unknown=1),TypeError)
expect_error(lambda:p.__init__());p.close();p.close();expect_error(p.sample)
result['semantics'].append('arguments_reinit_closed_calls_rejected')

reference=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/aura/board/vision/thread_sched_metrics.py')
approved=json.loads(Path('/home/root/aura-vision-reliability-20261023/f7624754038f3669/report.json').read_text())
assert hashlib.sha256(reference.read_bytes()).hexdigest()==approved['source_manifest']['board/vision/thread_sched_metrics.py']['sha256']
spec=importlib.util.spec_from_file_location('reference_probe_only',reference);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
observers={'existing_switch':mod.ThreadSwitchProbe(),'existing_python_schedstat':mod.ThreadSchedProbe(),
           'native_full_adapter':NativeThreadSchedProbe()}
try:
    for name,observer in observers.items():
        for _ in range(32):observer.sample()
        walls=[];cpus=[];native_reads=[];stopped_early=False
        for _ in range(1000):
            start=time.monotonic_ns();cpu=time.thread_time_ns()
            sample=observer.sample()
            if sample['tid']!=threading.get_native_id():stopped_early=True;break
            # Includes complete adapter, native PyTuple/PyLong construction,
            # lock/counter updates, return, and consumption of numeric fields.
            consume={'probe_'+key:value for key,value in sample.items()}
            cpus.append(time.thread_time_ns()-cpu);walls.append(time.monotonic_ns()-start)
            native_reads.append(sample['read_wall_ns'])
        result['cost'][name]={'complete_call_wall':percentiles(walls),'complete_call_thread_cpu':percentiles(cpus),
            'reported_read_wall':percentiles(native_reads),'stopped_early':stopped_early,'state':observer.snapshot()}
    n=result['cost']['native_full_adapter'];c=n['complete_call_thread_cpu'];w=n['complete_call_wall']
    result['cost_gate_passed']=(c['count']==1000 and c['mean_ns']<=100_000 and c['p99_ns']<=500_000 and w['p99_ns']<=1_000_000
        and not n['state']['disabled_after_cpu_cost'] and n['state']['read_failures']==0)
    result['semantic_checks_passed']=True
finally:
    for observer in observers.values():observer.close()
result['closed_all_observers']=True
print(json.dumps(result))
