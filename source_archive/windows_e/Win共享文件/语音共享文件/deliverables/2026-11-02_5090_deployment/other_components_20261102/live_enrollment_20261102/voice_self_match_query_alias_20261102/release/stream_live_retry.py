"""Host-side streaming observer with the project's unchanged strict SSH options."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import threading

sys.stdout.reconfigure(encoding='utf-8')
HERE=Path(__file__).resolve().parent
OUT=HERE/'LIVE_RETRY_3.jsonl'
assert not OUT.exists()
helper=Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-10-18_board_dialogue\board_ssh.py')
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('strict_board_ssh',helper)
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
assert transport.SSH and transport.KEY.is_file() and transport.KNOWN_HOSTS.is_file()
source=(HERE/'watch_retry_metadata.py').read_text('utf-8')
source='SINCE_UTC='+repr(datetime.datetime.now(datetime.timezone.utc).timestamp()-3)+'\n'+source
compile(source,'<metadata-watch>','exec')
command=[transport.SSH,'-i',str(transport.KEY),'-o','UserKnownHostsFile='+str(transport.KNOWN_HOSTS),
    '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4',
    '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','root@192.168.50.2','python3 -u -B -']
with OUT.open('x',encoding='utf-8') as log:
    log.write(json.dumps(dict(kind='host_start',host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        remote_script_sha256=hashlib.sha256(source.encode()).hexdigest(),strict_known_host_check=True))+'\n');log.flush()
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        text=True,encoding='utf-8',bufsize=1,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    timer=threading.Timer(165,process.terminate);timer.daemon=True;timer.start()
    errors=[]
    def drain_error():
        errors.append(bool(process.stderr.read()))
    reader=threading.Thread(target=drain_error,daemon=True);reader.start()
    try:
        process.stdin.write(source);process.stdin.close()
        count=0;last=None
        for line in process.stdout:
            try:value=json.loads(line)
            except ValueError:continue
            if type(value) is not dict or value.get('kind') not in ('sample','finished'):continue
            value['host_received_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            log.write(json.dumps(value)+'\n');log.flush();count+=1;last=value
        code=process.wait(timeout=5);reader.join(timeout=1)
        result=dict(kind='host_finished',exit_code=code,sample_count=count,stderr_present=any(errors),last=last)
        log.write(json.dumps(result)+'\n');log.flush();print(json.dumps(result))
    finally:
        timer.cancel()
        if process.poll() is None:process.terminate()
