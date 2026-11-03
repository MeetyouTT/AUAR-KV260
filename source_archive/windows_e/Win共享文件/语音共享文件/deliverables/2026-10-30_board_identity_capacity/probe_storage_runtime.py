"""Small disposable public SQLite write test and existing runtime inspection."""
import datetime,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path[:0]=[str(P/'deliverables/2026-10-18_board_dialogue'),str(P/'deliverables/2026-10-29_audio_animation_polish')]
from board_ssh import ssh
from board_guard import capture,same
REMOTE=r'''
import importlib.metadata,json,os,resource,sqlite3,statistics,time,uuid
from pathlib import Path
os.nice(19)
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
runtime={}
try:
 import onnxruntime as ort
 runtime=dict(importable=True,version=ort.__version__,providers=ort.get_available_providers(),
   inference_session_created=False,model_loaded=False)
except Exception as exc:runtime=dict(importable=False,error=type(exc).__name__+': '+str(exc))
parent=Path('/home/root').resolve(strict=True);path=parent/('.aura-public-capacity-'+uuid.uuid4().hex)
assert path.parent==parent and not path.exists()
path.mkdir(mode=0o700);dbpath=path/'public.sqlite3';connection=None;timings=[];size=0;cleaned=False
try:
 connection=sqlite3.connect(str(dbpath));connection.execute('PRAGMA journal_mode=WAL');connection.execute('PRAGMA synchronous=FULL')
 connection.execute('CREATE TABLE public_test(id INTEGER PRIMARY KEY,payload TEXT NOT NULL)');connection.commit()
 began=time.monotonic()
 for i in range(12):
  if time.monotonic()-began>6:raise TimeoutError('Six-second disposable write-test budget expired')
  start=time.perf_counter()
  connection.execute('INSERT INTO public_test VALUES(?,?)',(i,'PUBLIC_SYNTHETIC_DATA_'*96));connection.commit()
  timings.append((time.perf_counter()-start)*1000);time.sleep(.03)
 assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 size=sum(p.stat().st_size for p in path.iterdir() if p.is_file())
 actual=list(connection.execute('PRAGMA synchronous'))[0][0];assert actual==2
finally:
 if connection is not None:connection.close()
 # Remove only these known files in our newly created directory, never a glob.
 for suffix in ('-wal','-shm',''):
  target=Path(str(dbpath)+suffix)
  assert target.parent==path and path.parent==parent
  if target.exists():
   if not target.is_file() or target.is_symlink():raise ValueError('Unexpected disposable file ownership')
   target.unlink()
 path.rmdir();cleaned=not path.exists()
assert len(timings)==12 and cleaned
print(json.dumps(dict(status='PASS',scope='12_SMALL_PUBLIC_WAL_FULL_TRANSACTIONS_NOT_THROUGHPUT_OR_POWERLOSS_TEST',
 commit_ms=dict(p50=statistics.median(timings),max=max(timings),samples=timings),
 maximum_test_file_bytes=size,temporary_files_removed=cleaned,
 existing_onnxruntime=runtime,process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
 real_user_databases_opened=False,biometric_data_used=False,service_restarted=False,models_loaded=False)))
'''
report=dict(status='CHECKING',host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
try:
 before=capture();assert before['safe'] and not before['mismatches']
 report.update(json.loads(ssh('python3 -B -',REMOTE,timeout=20)))
 after=capture();same(before,after);report['board_safe_unchanged']=True
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'storage_runtime_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
