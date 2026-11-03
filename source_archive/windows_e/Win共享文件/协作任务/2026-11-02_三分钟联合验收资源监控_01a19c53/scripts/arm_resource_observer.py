from pathlib import Path
import subprocess,json,sys,py_compile
p=Path(__file__).resolve().parent.parent
for script in ['board_monitor.py','watch_start_gate.py']:py_compile.compile(str(p/'scripts'/script),doraise=True)
with (p/'data'/'local_gate_watcher.log').open('wb') as out:
 process=subprocess.Popen([sys.executable,'-X','utf8',str(p/'scripts'/'watch_start_gate.py')],stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
(p/'GATE_WATCHER_LAUNCH.json').write_text(json.dumps({'pid':process.pid,'board_calls_before_gate':0}),encoding='utf-8')
print(json.dumps({'gate_watcher_pid':process.pid,'board_calls_before_gate':0}))
