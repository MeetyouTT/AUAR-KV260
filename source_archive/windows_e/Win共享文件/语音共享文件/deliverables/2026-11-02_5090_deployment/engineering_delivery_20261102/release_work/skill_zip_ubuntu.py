from common import *
import base64
pack=OUT/'auar_skills.zip'; metadata=load(QA/'skills_archive.json')
assert sha(pack)==metadata['sha256']
src="""import sys,io,json,os,hashlib,shutil,tempfile,subprocess,zipfile
from pathlib import Path
import base64
b=base64.b64decode(BLOB)
assert hashlib.sha256(b).hexdigest()==DIGEST
results={}
with tempfile.TemporaryDirectory(prefix='auar-skills-release-') as work:
    z=zipfile.ZipFile(io.BytesIO(b))
    assert z.testzip() is None
    z.extractall(work)
    root=Path(work)/'skill'
    for dir,cmd in [
        ('command_guard_validation',['scripts/run_checks.py']),
        ('perception_freshness_benchmark',['-m','unittest','discover','-s','tests']),
        ('llm_voice_runtime_optimization',['scripts/check.py'])]:
        assert (root/dir/'SKILL.md').is_file()
        first=min(os.sched_getaffinity(0))
        p=subprocess.run(['taskset','-c',str(first),sys.executable,'-B']+cmd,cwd=str(root/dir),capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1'))
        if p.returncode:print((p.stderr+p.stdout).decode(errors='replace')[-2000:],file=sys.stderr);sys.exit(p.returncode)
        results[dir]=dict(exit_code=p.returncode,args=cmd,log_sha256=hashlib.sha256(p.stdout+p.stderr).hexdigest())
print(json.dumps({'status':'PASS','ubuntu':'20.04.4 LTS','python':sys.version.split()[0],'max_affinity_per_task':1,'archive_sha256':DIGEST,'result':results}))
"""
result=json.loads(ssh(src.replace('BLOB',repr(base64.b64encode(pack.read_bytes()).decode())).replace('DIGEST',repr(sha(pack)))))
save(QA/'standalone_skills_ubuntu.json',result)
print(result['status'],len(result['result']),result['archive_sha256'])
