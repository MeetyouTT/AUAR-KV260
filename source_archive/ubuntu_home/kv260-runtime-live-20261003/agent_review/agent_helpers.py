# SPDX-License-Identifier: MIT
"""Helpers executed after this run's hash-locked live_common.py. No automatic recovery."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

OFFICIAL_APP = 'kv260-benchmark-b4096'
M3_APP = 'kv260-benchmark-b4096-m3'
TOP5 = [('258','0.949879'),('270','0.00931229'),('259','0.00821807'),
        ('257','0.00498451'),('279','0.00388194')]
CLASSIFIER = '/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification'
IMAGE = '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'
_phase = None
_command_number = 0
_kernel_previous = None
_sample_pid = None
_sample_start = None

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def write_json(path, value):
    temporary = path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    temporary.replace(path)

def begin_phase(name):
    global _phase
    parent = WORK/'agent_logs'
    parent.mkdir(exist_ok=True)
    _phase = parent/name
    _phase.mkdir(exist_ok=False)
    write_json(_phase/'started.json', {'phase':name,'utc':utc_now(),
        'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'automatic_retry':False})
    kernel_check('initial', initialize=True)
    return _phase

def run_logged(argv, label, timeout=120, app=None, cwd=None, combined=False):
    global _command_number
    _command_number += 1
    safe = '{:06d}-{}'.format(_command_number,label)
    assert re.fullmatch(r'[A-Za-z0-9_.-]+',safe)
    env = os.environ.copy()
    if app is not None:
        env['XLNX_VART_FIRMWARE']='/lib/firmware/xilinx/{0}/{0}.xclbin'.format(app)
    before = utc_now()
    timeout_error = None
    try:
        proc = subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              timeout=timeout,cwd=cwd,env=env)
        raw_stdout,raw_stderr,returncode = proc.stdout,proc.stderr,proc.returncode
    except subprocess.TimeoutExpired as error:
        timeout_error = error
        raw_stdout,raw_stderr,returncode = error.stdout or b'',error.stderr or b'',None
    stdout = _phase/(safe+'.stdout')
    stderr = _phase/(safe+'.stderr')
    stdout.write_bytes(raw_stdout)
    stderr.write_bytes(raw_stderr)
    row = {'argv':argv,'cwd':cwd,'firmware':env.get('XLNX_VART_FIRMWARE'),
           'started_utc':before,'finished_utc':utc_now(),'returncode':returncode,
           'timed_out':timeout_error is not None,'timeout_seconds':timeout,
           'stdout':stdout.name,'stdout_sha256':digest(stdout),
           'stderr':stderr.name,'stderr_sha256':digest(stderr)}
    write_json(_phase/(safe+'.json'),row)
    if timeout_error:
        raise RuntimeError('Command timed out: {} (partial raw output {})'.format(label,stdout))
    if returncode:
        raise RuntimeError('Command failed: {} rc={} (raw output {})'.format(label,returncode,stdout))
    raw_result=raw_stdout+b'\n'+raw_stderr if combined else raw_stdout
    return raw_result.decode('utf-8','replace')

def kernel_check(label, initialize=False, allow_stock_remove=False):
    global _kernel_previous
    raw = subprocess.check_output(['dmesg'])
    lines = raw.decode('utf-8','replace').splitlines()
    path = _phase/(label+'.dmesg')
    assert not path.exists()
    path.write_bytes(raw)
    lost = False
    fresh = []
    if _kernel_previous is not None and not initialize:
        anchor = _kernel_previous[-min(16,len(_kernel_previous)):]
        if not anchor:
            fresh = lines
        else:
            matches = [i+len(anchor) for i in range(len(lines)-len(anchor)+1)
                       if lines[i:i+len(anchor)]==anchor]
            if matches:
                fresh = lines[matches[-1]:]
            else:
                lost = True
                fresh = lines
    errors = [s for s in fresh if re.search(r'BUG:|Oops:|Unable to handle|Kernel panic|Call trace:|ERROR|error|expected refcount',s)]
    permitted = []
    if allow_stock_remove:
        permitted = [s for s in errors if 'expected refcount 1 instead of 2' in s and '/axi/zyxclmm_drm' in s]
        if len(permitted)>1:
            permitted=[]
    unexpected = [s for s in errors if s not in permitted]
    value = {'utc':utc_now(),'full_log':path.name,'sha256':digest(path),
        'new_lines':fresh,'continuity_lost':lost,'error_lines':errors,
        'permitted_original_remove_errors':permitted,'unexpected_errors':unexpected,
        'property_warnings':[s for s in fresh if 'memory leak will occur' in s]}
    write_json(_phase/(label+'.kernel-review.json'),value)
    _kernel_previous = lines
    if lost or unexpected:
        raise RuntimeError('Kernel diagnostic or missing log continuity: '+str(path))
    return value

def fields(text):
    return dict((line.split(':',1)[0],line.split(':',1)[1].strip())
                for line in text.splitlines() if ':' in line)

def sample(label, require_candidate=True):
    global _sample_pid,_sample_start
    pid = manager_pid()
    assert pid>0
    process = Path('/proc')/str(pid)
    before = process.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]
    if _sample_pid is None:
        _sample_pid,_sample_start = pid,before
    assert pid==_sample_pid and before==_sample_start,'Manager PID replaced'
    state = fields((process/'status').read_text())
    inotify = {}
    for fdinfo in sorted((process/'fdinfo').iterdir()):
        try:
            text = fdinfo.read_text()
        except FileNotFoundError:
            continue
        descriptors=[]
        for line in text.splitlines():
            if line.startswith('inotify '):
                match=re.search(r'\bwd:([0-9a-fA-F]+)\b',line)
                assert match,'Unknown inotify descriptor'
                descriptors.append(int(match[1],16))
        if descriptors:
            inotify[fdinfo.name]={'lines':len(descriptors),'unique':len(set(descriptors)),
                                 'wd_hex':sorted({format(v,'x') for v in descriptors})}
    after = (process/'stat').read_text().rsplit(')',1)[1].split()[19]
    assert before==after,'Manager replaced during snapshot'
    memory=fields(Path('/proc/meminfo').read_text())
    mod=Path('/sys/module/zocl')
    result={'utc':utc_now(),'uptime':Path('/proc/uptime').read_text().strip(),
            'pid':pid,'process_start_ticks':before,'VmRSS':state.get('VmRSS'),
            'VmSize':state.get('VmSize'),'fd_count':len(list((process/'fd').iterdir())),
            'inotify_fds':inotify,'watch_count':sum(v['unique'] for v in inotify.values()),
            'memory':{k:memory.get(k) for k in ['MemTotal','MemAvailable','Slab','SReclaimable','SUnreclaim']},
            'zocl_srcversion':(mod/'srcversion').read_text().strip(),
            'zocl_refcnt':(mod/'refcnt').read_text().strip(),
            'zocl_params':{p.name:p.read_text().strip() for p in (mod/'parameters').iterdir()},
            'manager_error_lines':manager_errors() if require_candidate else []}
    write_json(_phase/(label+'.sample.json'),result)
    assert result['watch_count']==CFG.get('expected_watches',5),'Inotify count changed'
    assert not result['manager_error_lines'],'Candidate manager reported ERROR'
    assert result['zocl_refcnt']=='0','Driver retained after inference'
    return result

def classify(app,label):
    guard(CFG['fixed_srcversion'],app)
    manager_guard(True)
    output=run_logged([CLASSIFIER,'resnet18',IMAGE],label,app=app,
                      cwd='/home/root/kv260-test-20261001',combined=True)
    actual=re.findall(r'r[.]index +([0-9]+).*r[.]score +([0-9.eE+-]+)',output)
    assert actual==TOP5,'Full Top-5 differs: '+repr(actual)
    guard(CFG['fixed_srcversion'],app)
    manager_guard(True)
    return actual

def dpu_query(app,label,driver=None,candidate=True):
    driver=driver or CFG['fixed_srcversion']
    guard(driver,app)
    manager_guard(candidate)
    text=run_logged(['xdputil','query'],label,app=app)
    value=json.loads(text)
    assert value['DPU IP Spec']['DPU Core Count']==1 and len(value['kernels'])==1
    k=value['kernels'][0]
    assert k['fingerprint']=='0x101000056010407'
    assert k['DPU Arch']=='DPUCZDX8G_ISA1_B4096' and k['cu_addr']=='0xa0010000'
    assert k['DPU Frequency (MHz)']==300 and k['XRT Frequency (MHz)']==300
    assert value['DPU IP Spec']['git commit id']==('7d32c41' if app==M3_APP else 'ce8dd1')
    guard(driver,app)
    manager_guard(candidate)
    return value

def finish_phase(value,passed=True):
    result=dict(value,finished_utc=utc_now(),passed=passed)
    write_json(_phase/'result.json',result)
    print('ACTION_RESULT '+json.dumps(result,ensure_ascii=False),flush=True)
