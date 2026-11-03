"""Start the wired voice stack and confirm readiness of every dependency."""
import argparse
import http.client
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
AURA=ROOT/'aura'
sys.path.insert(0,str(AURA))
from common.voice_service_capabilities import require_current_voice,source_fingerprint


def save(value):
    target=HERE/'models_launch.json'
    temporary=target.with_name(target.name+'.tmp-'+uuid.uuid4().hex)
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(target)


def read_health(port,host='192.168.50.1'):
    connection=http.client.HTTPConnection(host,port,timeout=1)
    try:
        connection.request('GET','/health')
        response=connection.getresponse()
        raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise ValueError('Health response exceeds size limit')
        value=json.loads(raw)
        if response.status!=200 or value.get('ready') is not True:
            raise ValueError('Service is not ready on port '+str(port))
        return value
    finally:connection.close()


def require_health(port,value,model,fingerprint):
    if port==8791:
        if value.get('protocol')!='aura-asr-1' or value.get('ready') is not True:
            raise ValueError('ASR listener has an incompatible protocol')
    else:require_current_voice(value,model,fingerprint)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--voice-python')
    parser.add_argument('--run-id',default=None)
    parser.add_argument('--ready-timeout',type=float,default=300)
    args=parser.parse_args(argv)
    config=json.loads((AURA/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
    voice=Path(args.voice_python or json.loads((ROOT/'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json').read_text(encoding='utf-8'))['voice']['python'])
    if not voice.is_file():raise SystemExit('Pass the actual accepted voice environment with --voice-python')
    if not 5<=args.ready_timeout<=600:raise SystemExit('Readiness timeout must be within 5..600 seconds')
    state={'run_id':args.run_id or uuid.uuid4().hex,'status':'STARTING','ready':False,
           'services':{},'started_unix':time.time()}
    owned=[];save(state)
    try:
        with socket.socket() as probe:probe.bind(('192.168.50.1',0))
        fingerprint=source_fingerprint(AURA);state['source_fingerprint']=fingerprint
        for port in (8791,8792):
            with socket.socket() as probe:
                probe.settimeout(.5);listening=probe.connect_ex(('192.168.50.1',port))==0
            if listening:
                value=read_health(port);require_health(port,value,config['model'],fingerprint)
                state['services'][str(port)]={'reused':True,'ready':True}
        if config['ollama_host']=='http://127.0.0.1:11435':
            from project_ollama import ensure
            ensure()
        flags=(getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)
               |getattr(subprocess,'CREATE_NO_WINDOW',0))
        for port,script,extra in (
            (8791,'asr_server.py',['--model-dir',str(AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14')]),
            (8792,'board_model_host.py',['--root',str(HERE/'model_host'),'--voice-python',str(voice)])):
            if str(port) in state['services']:continue
            with (HERE/f'port_{port}_stdout.log').open('ab') as output,(HERE/f'port_{port}_stderr.log').open('ab') as error:
                process=subprocess.Popen([str(voice),'-B','-u',str(AURA/'tools'/script),'--listen','192.168.50.1',
                    '--port',str(port),*extra],cwd=AURA,stdin=subprocess.DEVNULL,stdout=output,stderr=error,creationflags=flags)
            owned.append((port,process));state['services'][str(port)]={'pid':process.pid,'reused':False,'ready':False};save(state)
        deadline=time.monotonic()+args.ready_timeout
        pending={int(port) for port,row in state['services'].items() if not row['ready']}
        while pending:
            for port,process in owned:
                if process.poll() is not None:raise RuntimeError('Service exited on port '+str(port)+'; inspect port stderr log')
            for port in tuple(pending):
                try:
                    value=read_health(port);require_health(port,value,config['model'],fingerprint)
                except (OSError,ValueError,http.client.HTTPException):continue
                state['services'][str(port)]['ready']=True;pending.remove(port);save(state)
            if not pending:break
            if time.monotonic()>=deadline:raise TimeoutError('Model service readiness deadline expired')
            time.sleep(.25)
        state['status']='STARTING_FRONTEND';save(state)
        frontend=ROOT/'deliverables/2026-10-21_environment_frontend/start_frontend.py'
        result=subprocess.run([str(voice),'-B',str(frontend)],cwd=ROOT,stdin=subprocess.DEVNULL,
            capture_output=True,text=True,encoding='utf-8',timeout=40,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (HERE/'frontend_launch_stdout.log').write_text(result.stdout,encoding='utf-8')
        (HERE/'frontend_launch_stderr.log').write_text(result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError('Audio frontend start failed; inspect frontend_launch_stderr.log')
        if json.loads(result.stdout).get('ready') is not True:raise RuntimeError('Audio frontend is not ready')
        state['services']['8795']={'ready':True,'launcher':'pinned independent CPU frontend'}
        state.update(status='READY',ready=True,finished_unix=time.time());save(state)
        print(json.dumps(state,ensure_ascii=False));return 0
    except Exception as exc:
        for port,process in owned:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
        state.update(status='FAILED',ready=False,error=type(exc).__name__+': '+str(exc)[:500],finished_unix=time.time())
        save(state);print(json.dumps(state,ensure_ascii=False),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
