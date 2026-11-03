"""Compact equivalent JSON on the verified Ollama-owned llama.cpp runner.

No weights are loaded here. Unsupported/unavailable runners fall back before
generation. Never connect to an arbitrary process or a non-loopback address.
"""
import json
from pathlib import Path
import re
import subprocess
import threading
import time
import urllib.request

GRAMMAR=r'''root ::= "{\"a\":" string ",\"b\":" emotion ",\"c\":\"\"}"
string ::= "\"" ([^"\\\x7F\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F]{4}))* "\""
emotion ::= "\"neutral\"" | "\"friendly\"" | "\"happy\"" | "\"sad\""
'''
VERIFIED_BUILD='b1-620d2225c'
_cache={};_lock=threading.Lock()


def _json(base,path,data,deadline,cancelled):
    if cancelled.is_set():raise InterruptedError('Reply cancelled')
    remaining=deadline-time.monotonic()
    if remaining<=0:raise TimeoutError('Native preparation budget expired')
    request=urllib.request.Request(base+path,data=None if data is None else json.dumps(data).encode(),
                                   headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=min(3.,remaining)) as response:
        raw=response.read(1_048_577)
    if len(raw)>1_048_576:raise ValueError('Native metadata exceeds bound')
    if cancelled.is_set():raise InterruptedError('Reply cancelled')
    return json.loads(raw)


def _discover(deadline):
    script=r'''
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new()
$nativeOwner=(Get-NetTCPConnection -LocalPort 11435 -State Listen | Select-Object -First 1).OwningProcess
if (-not $nativeOwner) {throw 'Project Ollama is not listening'}
$nativeParent=Get-CimInstance Win32_Process -Filter "ProcessId=$nativeOwner"
if ($nativeParent.Name -ine 'ollama.exe') {throw 'Unexpected project listener'}
$nativeRows=@(Get-CimInstance Win32_Process -Filter "ParentProcessId=$nativeOwner" | Where-Object {$_.Name -ieq 'llama-server.exe'} | Select-Object ProcessId,ExecutablePath,CommandLine)
ConvertTo-Json -InputObject $nativeRows -Compress
'''
    remaining=deadline-time.monotonic()
    if remaining<=0:raise TimeoutError('Native discovery budget expired')
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
                          capture_output=True,text=True,encoding='utf-8',errors='replace',
                          timeout=min(5.,remaining),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise RuntimeError('Native runner discovery failed')
    rows=json.loads(result.stdout.lstrip('\ufeff'))
    if len(rows)!=1:raise ValueError('Expected one project-owned native runner')
    row=rows[0];command=row['CommandLine']
    port=re.search(r'(?:^|\s)--port\s+(\d+)(?:\s|$)',command)
    model=re.search(r'(?:^|\s)--model\s+(?:"([^"]+)"|(\S+))',command)
    if not port or not model or not 1<=int(port[1])<=65535:raise ValueError('Invalid runner arguments')
    return {'base':'http://127.0.0.1:'+port[1],'model_path':model[1] or model[2],'pid':row['ProcessId']}


def _validate(endpoint,show,expected,deadline,cancelled):
    if Path(endpoint['model_path']).resolve()!=expected:raise ValueError('Native runner model differs')
    props=_json(endpoint['base'],'/props',None,deadline,cancelled)
    if (Path(props['model_path']).resolve()!=expected or props.get('build_info')!=VERIFIED_BUILD
            or props.get('total_slots')!=1 or props['default_generation_settings']['n_ctx']!=2048
            or props.get('chat_template')!=show.get('template')):
        raise ValueError('Native model/template/build/context not verified')
    return props


def prepare(host,body,timeout,cancelled):
    """Return a native target/request only after ownership and identity checks."""
    if host!='http://127.0.0.1:11435' or body.get('think') or body['format']['required']!=['a','b','c']:
        raise ValueError('Native compact route is only for verified local chat')
    deadline=time.monotonic()+min(10.,timeout)
    # A load/keepalive request contains no prompt and generates no tokens. It
    # keeps Ollama's eviction timer correct while inference uses its runner.
    warmed=_json(host,'/api/generate',{'model':body['model'],'keep_alive':body.get('keep_alive','30m')},deadline,cancelled)
    if warmed.get('response') or warmed.get('eval_count',0):raise ValueError('Unexpected warmup generation')
    show=_json(host,'/api/show',{'model':body['model']},deadline,cancelled)
    match=re.search(r'^FROM\s+(.+)$',show['modelfile'],re.M)
    if not match:raise ValueError('Model has no local source')
    expected=Path(match[1].strip().strip('"')).resolve()
    storage=json.loads((Path(__file__).resolve().parents[1]/'config/model_storage.local.json').read_text(encoding='utf-8-sig'))
    if expected.parent!=(Path(storage['ollama_directory'])/'blobs').resolve():
        raise ValueError('Native model must remain in external Ollama storage')
    with _lock:
        endpoint=_cache.get(host)
        try:
            if endpoint is None:raise ValueError('No cached runner')
            props=_validate(endpoint,show,expected,deadline,cancelled)
        except InterruptedError:raise
        except (OSError,ValueError,KeyError):
            endpoint=_discover(deadline)
            props=_validate(endpoint,show,expected,deadline,cancelled)
            _cache[host]=endpoint
    rendered=_json(endpoint['base'],'/apply-template',{'messages':body['messages'],
        'chat_template_kwargs':{'enable_thinking':False},'enable_thinking':False,'add_generation_prompt':True},deadline,cancelled)
    prompt=rendered['prompt']
    if not isinstance(prompt,str) or not prompt.endswith('<|im_start|>assistant\n<think>\n\n</think>\n\n'):
        raise ValueError('Expected non-thinking chat template')
    request={'prompt':prompt,'stream':True,'n_predict':body['options']['num_predict'],
             'temperature':body['options']['temperature'],'top_k':20,'top_p':.95,'min_p':0.,
             'repeat_penalty':1.,'cache_prompt':True,'n_keep':4,'grammar':GRAMMAR}
    if 'seed' in body['options']:request['seed']=body['options']['seed']
    return endpoint['base'],request,{'backend':'llama_native_compact','native_build':props['build_info']}


def normalize_packet(packet):
    result={'message':{'content':packet.get('content') or ''},'done':bool(packet.get('stop'))}
    if packet.get('error'):result['error']=packet['error']
    if result['done']:
        timing=packet.get('timings') or {}
        result.update(prompt_eval_count=timing.get('cache_n',0)+timing.get('prompt_n',0),
                      eval_count=timing.get('predicted_n',packet.get('tokens_predicted',0)),
                      done_reason='length' if packet.get('stopped_limit') else 'stop')
        for source,target in (('prompt_ms','prompt_eval_duration'),('predicted_ms','eval_duration')):
            if source in timing:result[target]=round(timing[source]*1_000_000)
        result['total_duration']=result.get('prompt_eval_duration',0)+result.get('eval_duration',0)
    return result
