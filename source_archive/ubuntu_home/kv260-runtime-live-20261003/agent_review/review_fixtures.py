"""Offline fixtures only: never opens UART or executes board commands."""
import datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path('/home/ghmd/kv260-runtime-live-20261003')
OLD=Path('/home/ghmd/kv260-dfx-manager-repair-20261002/evidence/20261003T043753Z-board-continuation')
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT=ROOT/'agent_review'/('offline-fixtures-'+stamp)
OUT.mkdir(exist_ok=False)
checks=[]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def namespace():
    values={'WORK':OUT,'CFG':{'fixed_srcversion':'9BDC942A6014BCCBD1DCB78','expected_watches':5},
            'digest':digest,'guard':lambda *args:None,'manager_guard':lambda *args:None,
            'manager_pid':lambda:123,'manager_errors':lambda:[]}
    path=ROOT/'reviewed_payload/agent_helpers.py'
    exec(compile(path.read_bytes(),str(path),'exec'),values)
    values['_phase']=OUT
    return values

# Use the unchanged helper code. Only subprocess transports and board guards
# are substituted; exact parsing and output capture code executes normally.
ns=namespace()
for phase,app in [('07-official-functional','kv260-benchmark-b4096'),
                  ('11-official-after-cycles','kv260-benchmark-b4096'),
                  ('13-m3-functional','kv260-benchmark-b4096-m3'),
                  ('16-restored-functional','kv260-benchmark-b4096')]:
    classification=OLD/(phase+'.classification.output')
    reply=SimpleNamespace(stdout=b'',stderr=classification.read_bytes(),returncode=0)
    with patch.object(ns['subprocess'],'run',return_value=reply):
        actual=ns['classify'](app,phase+'-stderr-top5')
    checks.append({'id':phase+'-stderr-top5','passed':actual==ns['TOP5'],
                   'fixture':str(classification),'fixture_sha256':digest(classification)})
    query=OLD/(phase+'.dpu_query.output')
    reply=SimpleNamespace(stdout=query.read_bytes(),stderr=b'non-json diagnostic\n',returncode=0)
    with patch.object(ns['subprocess'],'run',return_value=reply):
        value=ns['dpu_query'](app,phase+'-query')
    checks.append({'id':phase+'-query-json-stdout-only','passed':True,
                   'fixture':str(query),'fixture_sha256':digest(query)})

initial=['[ {:8.6f}] baseline {}'.format(i,i) for i in range(20)]
with patch.object(ns['subprocess'],'check_output',return_value=('\n'.join(initial)+'\n').encode()):
    ns['kernel_check']('kernel-initial',initialize=True)
after=initial[2:]+['[ 20.000000] OF: overlay: WARNING: memory leak will occur']
with patch.object(ns['subprocess'],'check_output',return_value=('\n'.join(after)+'\n').encode()):
    result=ns['kernel_check']('kernel-overlap')
checks.append({'id':'kernel-ring-overlap-preserves-continuity','passed':not result['continuity_lost'] and len(result['new_lines'])==1})
error_lines=after+['[ 21.000000] OF: ERROR expected refcount 1 instead of 2 /axi/zyxclmm_drm']
with patch.object(ns['subprocess'],'check_output',return_value=('\n'.join(error_lines)+'\n').encode()):
    try:
        ns['kernel_check']('kernel-new-error')
    except RuntimeError:
        checks.append({'id':'kernel-new-reference-error-stops-main-test','passed':True})
    else:
        checks.append({'id':'kernel-new-reference-error-stops-main-test','passed':False})
with patch.object(ns['subprocess'],'check_output',return_value=b'[ 100.000000] unrelated truncated ring\n'):
    try:
        ns['kernel_check']('kernel-gap')
    except RuntimeError:
        checks.append({'id':'kernel-missing-overlap-stops-main-test','passed':True})
    else:
        checks.append({'id':'kernel-missing-overlap-stops-main-test','passed':False})

# Build fake proc/sys files; count equal wd values separately by their FD.
fixture=OUT/'proc-sys-fixture'
proc=fixture/'proc/123'
(proc/'fdinfo').mkdir(parents=True)
(proc/'fd').mkdir()
(proc/'stat').write_text('123 (dfx mgrd) '+' '.join(['S']+['0']*18+['999'])+'\n')
(proc/'status').write_text('Name:\tdfx-mgrd\nVmRSS:\t1024 kB\nVmSize:\t8192 kB\n')
(proc/'fdinfo/3').write_text('inotify wd:1 ino:abcd\ninotify wd:1 ino:abcd\n')
(proc/'fdinfo/4').write_text(''.join('inotify wd:{:x} ino:abcd\n'.format(i) for i in [1,2,3,4]))
(proc/'fd/3').write_text('fixture')
(proc/'fd/4').write_text('fixture')
(fixture/'proc/uptime').write_text('123.45 234.56\n')
(fixture/'proc/meminfo').write_text('MemTotal: 4000000 kB\nMemAvailable: 2000000 kB\nSlab: 10000 kB\nSReclaimable: 3000 kB\nSUnreclaim: 7000 kB\n')
module=fixture/'sys/module/zocl'
(module/'parameters').mkdir(parents=True)
(module/'srcversion').write_text('9BDC942A6014BCCBD1DCB78\n')
(module/'refcnt').write_text('0\n')
(module/'parameters/enable_xgq_ert').write_text('1\n')
real_path=Path
def mapped_path(*args):
    result=real_path(*args)
    if str(result)=='/proc' or str(result).startswith('/proc/'):
        return fixture/str(result).lstrip('/')
    if str(result)=='/sys' or str(result).startswith('/sys/'):
        return fixture/str(result).lstrip('/')
    return result
ns['Path']=mapped_path
sample=ns['sample']('fake-process')
checks.append({'id':'watches-counted-per-fd-not-global-wd','passed':sample['watch_count']==5})
(proc/'stat').write_text('123 (dfx mgrd) '+' '.join(['S']+['0']*18+['1000'])+'\n')
try:
    ns['sample']('fake-process-replaced')
except AssertionError:
    checks.append({'id':'same-pid-new-starttime-rejected','passed':True})
else:
    checks.append({'id':'same-pid-new-starttime-rejected','passed':False})

manifest=json.loads((ROOT/'package_manifest.json').read_text())
hashes={name:digest(ROOT/'reviewed_payload'/name) for name in manifest['members']}
checks.append({'id':'frozen-package-member-hashes','passed':hashes==manifest['members']})
checks.append({'id':'frozen-archive-hash','passed':digest(manifest['archive'])==manifest['sha256']})
for path in (ROOT/'reviewed_payload').rglob('*.py'):
    compile(path.read_bytes(),str(path),'exec')
checks.append({'id':'reviewed-python-syntax','passed':True})
result={'scope':'Offline parsing and mock transport fixtures; no board commands or UART',
        'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,
        'passed':all(c['passed'] for c in checks),'evidence':str(OUT)}
(OUT/'fixture-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
