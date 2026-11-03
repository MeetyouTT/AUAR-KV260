"""Start only project Ollama, with optional calibrated fit target at creation.

Never terminates/restarts an existing daemon. A new config beside an already
healthy process is reported as requiring a controlled restart, not applied.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import urllib.request
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
HOST='http://127.0.0.1:11435'
STORAGE=json.loads((ROOT/'aura/config/model_storage.local.json').read_text(encoding='utf-8-sig'))

def atomic_json(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    temporary.write_text(json.dumps(value,indent=2),encoding='utf-8');os.replace(temporary,path)

def read_version():
    try:
        with urllib.request.urlopen(HOST+'/api/version',timeout=2) as response:
            if response.status!=200:return None
            raw=response.read(65537)
            if len(raw)>65536:raise RuntimeError('Project version response exceeds bound')
            value=json.loads(raw);version=value.get('version')
            if not isinstance(version,str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+.][\w.-]+)?',version):
                raise RuntimeError('Unexpected service on project Ollama endpoint')
            return version
    except OSError:return None

def load_runtime_policy():
    path=ROOT/'aura/config/ollama_runtime.local.json'
    if not path.exists():return None
    raw=path.read_bytes()
    if len(raw)>16384:raise ValueError('Ollama runtime configuration exceeds bound')
    value=json.loads(raw.decode('utf-8-sig'))
    required={'schema_version','fit_target_mib','calibration_id','gpu_uuid','ollama_version'}
    if not isinstance(value,dict) or set(value)!=required:raise ValueError('Unexpected Ollama runtime policy fields')
    if type(value['schema_version']) is not int or value['schema_version']!=1:raise ValueError('Invalid Ollama policy schema')
    target=value['fit_target_mib']
    if type(target) is not int or not 1<=target<=1048576:raise ValueError('fit_target_mib must be a measured positive MiB integer')
    if not isinstance(value['calibration_id'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}',value['calibration_id']):
        raise ValueError('A calibration_id source is required')
    if not isinstance(value['gpu_uuid'],str) or not re.fullmatch(r'GPU-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value['gpu_uuid']):
        raise ValueError('A calibrated physical GPU UUID is required')
    if not isinstance(value['ollama_version'],str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+.][\w.-]+)?',value['ollama_version']):
        raise ValueError('A pinned local Ollama version is required')
    return dict(value,config_sha256=hashlib.sha256(raw).hexdigest())

def project_environment(policy):
    # Only a copy is passed to the project child; no global/user/system env edit.
    env=dict(os.environ,OLLAMA_HOST='127.0.0.1:11435',
      OLLAMA_MODELS=STORAGE['ollama_directory'],OLLAMA_NO_CLOUD='1',
      OLLAMA_NUM_PARALLEL='1',OLLAMA_MAX_LOADED_MODELS='1',OLLAMA_CONTEXT_LENGTH='2048')
    if policy is not None:
        if env.get('LLAMA_ARG_FIT','on').lower()!='on':raise ValueError('Inherited LLAMA_ARG_FIT disables the calibrated fit policy')
        env['LLAMA_ARG_FIT_TARGET']=str(policy['fit_target_mib'])
    return env

def verify_policy_bindings(policy,executable,env,*,running_version=None):
    if policy is None:return None
    if running_version is not None and running_version!=policy['ollama_version']:
        raise ValueError('Running project Ollama version differs from calibration')
    result=subprocess.run([executable,'--version'],env=env,capture_output=True,text=True,timeout=5,
      creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError('Cannot verify installed Ollama version')
    text=result.stdout+'\n'+result.stderr
    client=re.findall(r'client version(?: is)?\s+v?(\d+\.\d+\.\d+(?:[-+.][\w.-]+)?)',text,re.I)
    general=re.findall(r'ollama version(?: is)?\s+v?(\d+\.\d+\.\d+(?:[-+.][\w.-]+)?)',text,re.I)
    installed=(client or general)
    if len(set(installed))!=1 or installed[0]!=policy['ollama_version']:
        raise ValueError('Installed Ollama version differs from calibration')
    gpu=subprocess.run(['nvidia-smi','--query-gpu=uuid,memory.total','--format=csv,noheader,nounits'],
      capture_output=True,text=True,timeout=3,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if gpu.returncode:raise RuntimeError('Cannot verify calibrated GPU')
    rows=list(csv.reader(gpu.stdout.strip().splitlines()))
    # A single-value policy is intentionally limited to the calibrated one-GPU
    # host. Multiple-device layout requires a separately calibrated schema.
    if len(rows)!=1 or len(rows[0])!=2:raise ValueError('Calibrated policy requires the original single-GPU host')
    identity,total=[v.strip() for v in rows[0]]
    if identity.casefold()!=policy['gpu_uuid'].casefold() or not total.isdecimal():raise ValueError('GPU identity differs from calibration')
    total=int(total)
    if not 0<policy['fit_target_mib']<total:raise ValueError('Fit target is outside the calibrated device capacity')
    visible=env.get('CUDA_VISIBLE_DEVICES')
    if visible is not None and visible not in ('0',identity):raise ValueError('Inherited CUDA GPU selection differs from calibration')
    return {'ollama_version':installed[0],'gpu_uuid':identity,'gpu_total_mib':total,
            'executable':str(Path(executable).resolve()),'executable_sha256':hashlib.sha256(Path(executable).read_bytes()).hexdigest()}

def inspect_ownership():
    # Fixed read-only query: no PID/path interpolation and no process actions.
    command=r"""[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$ownerListeners=@(Get-NetTCPConnection -State Listen -LocalPort 11435 -ErrorAction SilentlyContinue)
$ownerIds=@($ownerListeners.OwningProcess | Select-Object -Unique)
if ($ownerIds.Count -ne 1) { throw 'Project listener owner is not unique' }
$ownerProcess=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$ownerIds[0])
if (-not $ownerProcess) { throw 'Project listener process disappeared' }
[pscustomobject]@{pid=[int]$ownerProcess.ProcessId;creation_utc=$ownerProcess.CreationDate.ToUniversalTime().ToString('o');
 executable=$ownerProcess.ExecutablePath;command_line=$ownerProcess.CommandLine;parent_pid=[int]$ownerProcess.ParentProcessId;
 listeners=@($ownerListeners | Select-Object LocalAddress,LocalPort,OwningProcess)} | ConvertTo-Json -Depth 5 -Compress
"""
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],
      capture_output=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError('Cannot inspect project daemon ownership')
    value=json.loads(result.stdout.decode('utf-8-sig'))
    if (type(value.get('pid')) is not int or value['pid']<=0 or not value.get('creation_utc')
        or not value.get('executable') or not value.get('command_line')):raise RuntimeError('Incomplete project daemon ownership')
    rows=value.get('listeners')
    if (not isinstance(rows,list) or not rows or any(r.get('LocalPort')!=11435 or r.get('OwningProcess')!=value['pid']
      or r.get('LocalAddress')!='127.0.0.1' for r in rows)):raise RuntimeError('Unexpected project listener scope')
    return value

def ownership_matches(record,current):
    expected=record.get('ownership')
    if not isinstance(expected,dict):return False
    return all(expected.get(key)==current.get(key) for key in ('pid','creation_utc','executable','command_line','listeners'))

def port_available():
    try:
        with socket.socket() as probe:probe.bind(('127.0.0.1',11435))
        return True
    except OSError:return False

def ensure():
    policy=load_runtime_policy();version=read_version()
    if version is not None and policy is None:
        return {'status':'REUSED','host':HOST,'ready':True,'runtime_policy_requested':False,
                'needs_controlled_restart':False,'launch_environment_applied':None,'effective_runner_budget_verified':False}
    executable=shutil.which('ollama')
    if not executable:raise RuntimeError('Ollama executable not installed')
    env=project_environment(policy)
    bindings=verify_policy_bindings(policy,executable,env,running_version=version)
    if version is not None:
        current=inspect_ownership();record_path=HERE/'project_ollama_process.json'
        try:prior=json.loads(record_path.read_text(encoding='utf-8-sig'))
        except (OSError,ValueError):prior={}
        matched=(ownership_matches(prior,current) and prior.get('runtime_policy')==policy and prior.get('bindings')==bindings)
        status={'status':'REUSED','host':HOST,'ready':True,'runtime_policy_requested':True,
          'requested_fit_target_mib':policy['fit_target_mib'],'calibration_id':policy['calibration_id'],
          'ownership':current,'bindings':bindings,'policy_recorded_for_current_process_creation':matched,
          'needs_controlled_restart':not matched,'launch_environment_applied':None,
          'effective_runner_budget_verified':False,
          'message':'Existing healthy daemon unchanged; a config edit does not alter its environment'}
        atomic_json(HERE/'project_ollama_policy_status.json',status);return status
    if not port_available():raise RuntimeError('Project port is occupied; no process will be stopped or replaced')
    with (HERE/'project_ollama_stdout.log').open('a',encoding='utf-8') as output,\
         (HERE/'project_ollama_stderr.log').open('a',encoding='utf-8') as error:
        process=subprocess.Popen([executable,'serve'],env=env,cwd=ROOT,stdout=output,stderr=error,
          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    record={'pid':process.pid,'host':HOST,'models':env['OLLAMA_MODELS'],
      'runtime_policy':policy,'bindings':bindings,'ownership':None,'ready':False,
      'launch_environment_applied':bool(policy),'effective_runner_budget_verified':False}
    atomic_json(HERE/'project_ollama_process.json',record)
    for _ in range(30):
        version=read_version()
        if version is not None:
            if policy is not None and version!=policy['ollama_version']:raise RuntimeError('New daemon version differs from calibrated policy')
            current=inspect_ownership()
            if current['pid']!=process.pid:raise RuntimeError('Ready project endpoint belongs to another process')
            expected_executable=str(Path(executable).resolve())
            if os.path.normcase(current['executable'])!=os.path.normcase(expected_executable):raise RuntimeError('Ready daemon executable differs')
            record.update(ownership=current,ready=True);atomic_json(HERE/'project_ollama_process.json',record)
            status={'status':'STARTED','host':HOST,'ready':True,'runtime_policy_requested':bool(policy),
              'needs_controlled_restart':False,'launch_environment_applied':bool(policy),
              'effective_runner_budget_verified':False,'ownership':current,'bindings':bindings}
            atomic_json(HERE/'project_ollama_policy_status.json',status);return status
        if process.poll() is not None:raise RuntimeError('Project Ollama failed; inspect project_ollama_stderr.log')
        time.sleep(1)
    raise RuntimeError('Project Ollama did not become ready')

if __name__=='__main__':print(json.dumps(ensure(),ensure_ascii=False))
