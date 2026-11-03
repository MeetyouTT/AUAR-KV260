"""Root-owned, serial public-file ARM performance experiments.

Only immutable source and official CPU runtime wheels enter a new private
directory. Production services, models, databases and packages are not edited.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import KEY, ssh
from resume_baseline import write_json

PRIVATE = '/home/root/aura-board-owner-candidate-20261030'
BOOT = '8100a7fd-0c6a-46c4-82b8-f874988a1521'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def window():
    value = json.loads((HERE.parent/'coordination/runtime_windows.json').read_text(encoding='utf-8-sig'))
    if value['performance_window'].get('state') != 'BUSINESS_ACCEPTANCE_EXCLUSIVE':
        raise RuntimeError('The root does not own the performance window')


def stage():
    window()
    sources = {
        'probe.py': HERE/'resume_inference/board_audio_pipeline_probe.py',
        'adapter.py': HERE/'resume_frontend_optimization/run_candidate_probe.py',
        'candidate.py': HERE/'resume_frontend_optimization/candidate/board_gtcrn_reuse.py',
        'runtime.py': HERE/'resume_ort_candidate/isolated_cpu_runtime.py',
    }
    for name, path in sources.items():
        compile(path.read_text(encoding='utf-8'), str(path), 'exec')
    pins = {name:digest(path) for name,path in sources.items()}
    fingerprint = hashlib.sha256(json.dumps(pins,sort_keys=True).encode()).hexdigest()
    target = PRIVATE+'/perf-'+fingerprint[:16]
    script = '''import base64,hashlib,json,os\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\np=Path(TARGET)\nassert p.parent==Path(PRIVATE) and p.parent.is_dir() and not p.parent.is_symlink()\np.mkdir(mode=0o700,exist_ok=True)\nassert not p.is_symlink() and p.stat().st_mode&0o077==0\nfor name,encoded in SOURCES.items():\n b=base64.b64decode(encoded,validate=True); assert hashlib.sha256(b).hexdigest()==PINS[name]\n t=p/name; assert not t.is_symlink()\n if t.exists(): assert t.read_bytes()==b\n else:\n  fd=os.open(str(t),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n  with os.fdopen(fd,'wb') as out: out.write(b);out.flush();os.fsync(out.fileno())\nprint(json.dumps(dict(status='STAGED_SOURCE_ONLY',root=str(p),pins=PINS)))'''
    import base64
    prefix = '\n'.join(key+'='+repr(value) for key,value in dict(BOOT=BOOT,PRIVATE=PRIVATE,TARGET=target,
        PINS=pins,SOURCES={n:base64.b64encode(p.read_bytes()).decode() for n,p in sources.items()}).items())+'\n'
    result=json.loads(ssh('python3 -B -',prefix+script,timeout=30))
    result['local_sources']={n:str(p) for n,p in sources.items()}
    write_json(HERE/'resume_performance/staged.json',result)
    return result


def run(mode, nice, runs, audio_mode='frontend-profile'):
    window()
    staged=json.loads((HERE/'resume_performance/staged.json').read_text(encoding='utf-8'))
    code=json.loads((HERE/'resume_bundle/staged.json').read_text(encoding='utf-8'))['candidate_root']+'/code'
    root=staged['root']
    argv=['python3','-B',root+'/adapter.py','--candidate-mode',mode,'--probe-file',root+'/probe.py',
        '--candidate-file',root+'/candidate.py','--code-root',code,'--resources-root',PRIVATE,
        '--num-threads','1','--mode',audio_mode,'--runs',str(runs),'--process-nice',str(nice)]
    script='''import hashlib,json,subprocess\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\nfor name,digest in PINS.items(): assert hashlib.sha256((Path(ROOT)/name).read_bytes()).hexdigest()==digest\nr=subprocess.run(ARGV,capture_output=True,text=True,timeout=100)\nprint(json.dumps(dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)))'''
    prefix='\n'.join(k+'='+repr(v) for k,v in dict(BOOT=BOOT,ROOT=root,PINS=staged['pins'],ARGV=argv).items())+'\n'
    now=datetime.datetime.now(datetime.timezone.utc); began=time.monotonic()
    result=dict(started_utc=now.isoformat(),mode=mode,nice=nice,runs=runs,source=staged,argv=argv,
        production_entry_changed=False,physical_microphone_opened=False)
    try:
        value=json.loads(ssh('python3 -B -',prefix+script,timeout=110))
        result.update(value)
        result['result']=json.loads(value['stdout'])
        result['status']=result['result'].get('status','RETURNED')
    except Exception as error:
        result.update(status='ERROR',error_type=type(error).__name__,error=str(error)[-6000:])
    result['elapsed_seconds']=round(time.monotonic()-began,3)
    path=HERE/'resume_performance'/(now.strftime('%Y%m%dT%H%M%S')+'-'+mode+'.json')
    write_json(path,result)
    print(json.dumps(dict(output=str(path),status=result['status'],returncode=result.get('returncode'),
        runs=[dict(rtf=r.get('processing_rtf'),ms=r.get('frontend_processing_ms'),sha=r.get('decision_sha256'))
              for r in result.get('result',{}).get('runs',[])],error=result.get('error')),ensure_ascii=True))


def stage_runtimes():
    window()
    folder=Path(r'D:\AIModels\audio-frontend-eval-20261021\board-ort-candidate-20261030')
    assets=[('onnxruntime','1.19.2',folder/'onnxruntime-1.19.2-cp39-cp39-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl',
        'df2a94179a42d530b936f154615b54748239c2908ee44f0d722cb4df10670f68'),
        ('numpy','1.26.4',folder/'numpy-1.26.4-cp39-cp39-manylinux_2_17_aarch64.manylinux2014_aarch64.whl',
        'd5241e0a80d808d70546c697135da2c613f30e28251ff8307eb72ba696945764')]
    for _,_,path,expected in assets:
        if digest(path)!=expected: raise ValueError('Official runtime wheel SHA differs')
    staged=json.loads((HERE/'resume_performance/staged.json').read_text(encoding='utf-8'))
    root=staged['root']; cache=root+'/wheels'
    script="from pathlib import Path\np=Path(CACHE)\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\nassert p.parent==Path(ROOT) and not p.is_symlink()\np.mkdir(mode=0o700,exist_ok=True)\nassert p.stat().st_mode&0o077==0\n"
    ssh('python3 -B -','CACHE='+repr(cache)+'\nROOT='+repr(root)+'\nBOOT='+repr(BOOT)+'\n'+script)
    reports=[]
    for package,version,path,expected in assets:
        target=cache+'/'+path.name
        check=ssh('python3 -B -','from pathlib import Path\np=Path('+repr(target)+')\nprint("exists" if p.exists() else "absent")\n').strip()
        if check=='absent':
            command=['C:/Windows/System32/OpenSSH/scp.exe','-O','-q','-i',str(KEY),'-o','IdentitiesOnly=yes',
                '-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',path.name,'root@192.168.50.2:'+target]
            result=subprocess.run(command,cwd=str(path.parent),capture_output=True,text=True,timeout=55)
            if result.returncode: raise RuntimeError(result.stderr[-1500:])
        output=root+'/'+package+'-'+version
        argv=['python3','-B',root+'/runtime.py','unpack','--wheel',target,'--sha256',expected,
            '--package',package,'--version',version,'--private-root',root,'--output',output]
        script='''import hashlib,json,os,subprocess\nfrom pathlib import Path\np=Path(TARGET);assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==EXPECTED\np.chmod(0o600)\nr=subprocess.run(ARGV,capture_output=True,text=True,timeout=35)\nprint(json.dumps(dict(package=PACKAGE,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)))'''
        prefix='\n'.join(k+'='+repr(v) for k,v in dict(TARGET=target,EXPECTED=expected,ARGV=argv,PACKAGE=package).items())+'\n'
        value=json.loads(ssh('python3 -B -',prefix+script,timeout=45));reports.append(value)
        if value['returncode']: raise RuntimeError(json.dumps(value))
    report=dict(status='ISOLATED_RUNTIMES_UNPACKED_NOT_IMPORTED',root=root,assets=reports,
        production_packages_changed=False,model_weights_changed=False)
    write_json(HERE/'resume_performance/runtimes.json',report)
    print(json.dumps(report))


def runtime_probe(ort_version,mode,nice,runs,audio_mode):
    window()
    staged=json.loads((HERE/'resume_performance/staged.json').read_text(encoding='utf-8'))
    source=HERE/'resume_frontend_optimization/board_audio_runtime_probe.py'
    expected='ac0af16c9f783b5590ab0e1562ece179b8cc50ade3912c8b08e8b8592778e093'
    if digest(source)!=expected: raise ValueError('Explicit runtime probe source is not the reviewed copy')
    compile(source.read_text(encoding='utf-8'),str(source),'exec')
    root=staged['root'];target=root+'/runtime-probe-'+expected[:16]+'.py'
    import base64
    data=base64.b64encode(source.read_bytes()).decode()
    transfer='''import base64,hashlib,os\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\np=Path(TARGET);assert p.parent==Path(ROOT) and not p.is_symlink()\nb=base64.b64decode(DATA,validate=True);assert hashlib.sha256(b).hexdigest()==EXPECTED\nif p.exists():assert p.read_bytes()==b\nelse:\n fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n with os.fdopen(fd,'wb') as out:out.write(b);out.flush();os.fsync(out.fileno())\n'''
    prefix='\n'.join(k+'='+repr(v) for k,v in dict(BOOT=BOOT,TARGET=target,ROOT=root,DATA=data,EXPECTED=expected).items())+'\n'
    ssh('python3 -B -',prefix+transfer)
    code=json.loads((HERE/'resume_bundle/staged.json').read_text(encoding='utf-8'))['candidate_root']+'/code'
    ort_root=PRIVATE+'/fft-ee19b936d17aa451/deps' if ort_version=='1.17.3' else root+'/onnxruntime-1.19.2'
    numpy_root=root+'/numpy-1.26.4'
    argv=['python3','-B',root+'/runtime.py','run','--ort-root',ort_root,'--ort-version',ort_version,
        '--numpy-root',numpy_root,'--numpy-version','1.26.4',
        '--dependency-path',PRIVATE+'/fft-ee19b936d17aa451/deps',
        '--dependency-path',PRIVATE+'/asr-1.13.8/deps',
        '--dependency-path','/usr/lib/python3.9/site-packages','--code-path',code,
        '--probe',root+'/adapter.py','--probe-sha256',staged['pins']['adapter.py'],'--',
        '--candidate-mode',mode,'--probe-file',target,'--candidate-file',root+'/candidate.py','--code-root',code,
        '--resources-root',PRIVATE,'--num-threads','1','--mode',audio_mode,'--runs',str(runs),
        '--process-nice',str(nice),'--runtime-private-root',root,'--runtime-ort-root',ort_root,
        '--runtime-ort-version',ort_version,'--runtime-numpy-root',numpy_root]
    wrapper='''import hashlib,json,subprocess\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\nfor name,digest in PINS.items():assert hashlib.sha256((Path(ROOT)/name).read_bytes()).hexdigest()==digest\nr=subprocess.run(ARGV,capture_output=True,text=True,timeout=105)\nprint(json.dumps(dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)))'''
    prefix='\n'.join(k+'='+repr(v) for k,v in dict(BOOT=BOOT,ROOT=root,PINS=staged['pins'],ARGV=argv).items())+'\n'
    now=datetime.datetime.now(datetime.timezone.utc)
    record=dict(began_utc=now.isoformat(),ort=ort_version,numpy='1.26.4',mode=mode,nice=nice,
        runs=runs,audio_mode=audio_mode,argv=argv,reviewed_probe_sha256=expected,
        production_entry_changed=False,physical_microphone_opened=False)
    try:
        value=json.loads(ssh('python3 -B -',prefix+wrapper,timeout=115));record.update(value)
        record['result']=json.loads(value['stdout']);record['status']=record['result'].get('status','RETURNED')
    except Exception as error:
        record.update(status='ERROR',error_type=type(error).__name__,error=str(error)[-6000:])
    output=HERE/'resume_performance'/(now.strftime('%Y%m%dT%H%M%S')+'-ort'+ort_version+'-'+mode+'.json')
    write_json(output,record)
    print(json.dumps(dict(output=str(output),status=record['status'],returncode=record.get('returncode'),
        runs=[dict(rtf=r.get('processing_rtf'),ms=r.get('frontend_processing_ms'),sha=r.get('decision_sha256'))
              for r in record.get('result',{}).get('runs',[])],error=record.get('error')),ensure_ascii=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('stage','run','stage-runtimes','run-runtime'))
    parser.add_argument('--mode',choices=('baseline','reuse','io','combined'),default='baseline')
    parser.add_argument('--nice',type=int,choices=(0,-5,-10),default=0)
    parser.add_argument('--runs',type=int,choices=(1,2,3),default=2)
    parser.add_argument('--audio-mode',choices=('frontend-profile','pipeline'),default='frontend-profile')
    parser.add_argument('--ort-version',choices=('1.17.3','1.19.2'),default='1.19.2')
    args=parser.parse_args()
    if args.action=='stage': print(json.dumps(stage()))
    elif args.action=='stage-runtimes': stage_runtimes()
    elif args.action=='run-runtime': runtime_probe(args.ort_version,args.mode,args.nice,args.runs,args.audio_mode)
    else: run(args.mode,args.nice,args.runs,args.audio_mode)
