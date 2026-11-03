"""Launch only the separately pinned, board-peer-restricted A/B portrait fixture."""
from pathlib import Path
import datetime,json,os,subprocess,time,uuid
from fixture_identity import process_identity
phase=Path(__file__).parent.parent;root=phase.parent.parent.parent
aura=root/'aura'
python=Path('C:/Users/35870/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
assert python.is_file()
run=phase/'paired_ab/windows_fixture'/uuid.uuid4().hex;run.mkdir(parents=True)
ready=run/'ready.json';log_path=run/'host.log'
command=[str(python),'-B',str(phase/'paired_ab/isolated_portrait_server.py'),'--aura',str(aura),
 '--source-config',str(aura/'config/portrait_host.local.json'),'--board-manifest',str(phase/'board_source/manifest.json'),
 '--expected-revision','763d0b05a67a79ff6f8a6d9d5e2a67cc9cc060181499cef7a416bccdf7315bac',
 '--ready-file',str(ready),'--execute']
dependencies=Path('C:/Users/35870/.codex/visualizations/2026/10/26/01a1772c-f263-75f1-bfa1-9bd865e5caa9/animation-fps-deps')
assert dependencies.is_dir()
# Match the live host_entry.py bootstrap without running it or writing its logs.
environment=dict(os.environ);environment['PYTHONPATH']=str(dependencies)+os.pathsep+environment.get('PYTHONPATH','')
environment['OMP_NUM_THREADS']=environment['OPENBLAS_NUM_THREADS']='1'
with log_path.open('w',encoding='utf8') as log:
    process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
      cwd=str(root),env=environment,creationflags=subprocess.CREATE_NO_WINDOW)
state=dict(pid=process.pid,command=command,ready_file=str(ready),log=str(log_path),production_modified=False,dependency_path=str(dependencies),omp_threads=1,openblas_threads=1,
           identity=process_identity(process.pid),created_at_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
old=phase/'paired_ab/isolated-host-state.json'
if old.exists():
    previous=json.loads(old.read_text(encoding='utf8'))
    (phase/'paired_ab'/('isolated-host-state-'+str(previous['pid'])+'.json')).write_text(json.dumps(previous,indent=2),encoding='utf8')
(phase/'paired_ab/isolated-host-state.json').write_text(json.dumps(state,indent=2),encoding='utf8')
print(json.dumps(state))
