"""Bounded current-runtime benchmark; public inputs, no playback or production writes."""
import ast
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import threading
import time
import urllib.request

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PROJECT = BASE.parent.parent
HANDOFF = BASE / "joint_acceptance_180s_20261102/PERFORMANCE_MEASUREMENT_HANDOFF.json"


def atomic(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


REMOTE = r'''
import array,base64,datetime as dt,hashlib,http.client,json,math,re,threading,time
from pathlib import Path
LOCK=threading.Lock()
STOP=threading.Event()
ERRORS=[]
def output(value):
    value['board_mono']=time.monotonic()
    with LOCK: print(json.dumps(value,ensure_ascii=False,separators=(',',':')),flush=True)
def guard():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==CONTRACT['boot_id'],'boot_changed'
    assert hashlib.sha256(Path(CONTRACT['startup_path']).read_bytes()).hexdigest()==CONTRACT['startup_sha256'],'startup_changed'
    for e in CONTRACT['owners']:
        p=Path('/proc')/str(e['pid'])
        assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==str(e['birth_ticks']),'owner_changed'
        assert hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()==e['command_sha256'],'command_changed'
def http_json(host,port,path,payload=None,timeout=2):
    c=http.client.HTTPConnection(host,port,timeout=timeout)
    try:
        body=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
        c.request('GET' if payload is None else 'POST',path,body,{} if body is None else {'Content-Type':'application/json'})
        r=c.getresponse();raw=r.read(8388609)
        assert len(raw)<=8388608,'response_bound'
        v=json.loads(raw)
        if r.status!=200:raise RuntimeError('http_status_'+str(r.status)+'_'+str((v.get('error') or {}).get('code','unknown')))
        return v,len(raw)
    finally:c.close()
def health():
    v,_=http_json('192.168.50.1',8797,'/health')
    b=v.get('backend') or {};g=b.get('gpu_coordination') or {}
    assert v.get('ok') is True and b.get('model')=='aura-qwen3.8-27b-abliterated:iq4_xs' and b.get('num_step')==16,'model_changed'
    return {'active':v.get('active'),'pending':v.get('pending'),'counts':v.get('counts'),
        'tts_ready':b.get('tts_ready'),'voice_alive':(b.get('voice') or {}).get('alive'),
        'tts_counts':g.get('tts_counts'),'tts_stats':g.get('tts_stats'),'gpu_memory':g.get('memory')}
def gui():
    v,_=http_json('127.0.0.1',8783,'/api/state');r=extended(v)
    assert r.get('pan',{}).get('automatic_following') is False,'following_enabled'
    return r
def observe_gui():
    n=0
    while not STOP.is_set() and time.monotonic()-START<180:
        tick=time.monotonic()
        try:
            if n%10==0:guard()
            r=gui();r['event']='GUI_SAMPLE';r['request_ms']=(time.monotonic()-tick)*1000;output(r)
        except Exception as e:
            ERRORS.append(type(e).__name__+':'+str(e)[:120]);output({'event':'GUI_ERROR','code':ERRORS[-1]});STOP.set();break
        n+=1;STOP.wait(max(0,1-(time.monotonic()-tick)))
def owner(i,kind):
    return {'protocol_version':1,'request_id':CONTRACT['run_id']+'-'+kind+'-'+str(i),
        'board_boot_id':CONTRACT['boot_id'],'session_id':CONTRACT['run_id'],'generation':i}
def inference(kind,payload):
    began=time.monotonic();r,size=http_json('192.168.50.1',8797,'/v1/inference/'+kind,payload,timeout=35)
    elapsed=(time.monotonic()-began)*1000
    assert r.get('ok') is True and all(r.get(k)==payload[k] for k in ['request_id','board_boot_id','session_id','generation']),'response_owner'
    return r['result'],elapsed,size
guard();initial=gui();START=time.monotonic()
output({'event':'START','duration_seconds':180,'scope':'axis_stopped_current_runtime_public_inference',
        'boot_id':CONTRACT['boot_id'],'startup_sha256':CONTRACT['startup_sha256'],
        'public_cases':6,'axis_commands':0,'playback_requests':0,'source_config_changes':0,'initial':initial})
t=threading.Thread(target=observe_gui,daemon=True);t.start()
QUESTIONS=[
 '请用二十到四十个汉字介绍春天公园里适合散步的原因。',
 '请用三十到五十个汉字描述一片安静的星空，避免使用数字。',
 '请用二十到四十个汉字给准备阅读的朋友一句轻松的鼓励。',
 '请用三十到五十个汉字介绍下雨时在家可以做的休闲活动。',
 '请用二十到四十个汉字描述早晨窗边的阳光和一杯热茶。',
 '请用三十到五十个汉字解释整理书桌可以怎样帮助开始学习。']
TTS=[
 '你好，今天的阳光很好，我们一起轻松地聊一会儿吧。',
 '窗外的微风轻轻吹过树叶，安静的午后很适合读一本喜欢的书。',
 '抬头看看夜空，远处的星光像细小的灯火，陪着我们慢慢说话，也让忙碌了一天的心情渐渐平静下来。',
 '今天先给自己一点鼓励，然后从一件容易完成的小事开始吧。',
 '雨点落在窗边发出轻轻的声音，我们可以泡一杯热茶，听听音乐，享受这段安静的时间。',
 '把桌面整理干净，将常用的笔和书放在顺手的位置，再为接下来的学习定一个简单的目标，这样开始行动会更加轻松。']
SYSTEM='这是公开性能测试。只输出一个JSON对象，包含reply_text、emotion、avatar_action三个字段。reply_text用自然中文回答用户；emotion为friendly；avatar_action为空字符串。不得输出解释或思考。'
for i,(question,text) in enumerate(zip(QUESTIONS,TTS),1):
    if STOP.wait(max(0,START+10+(i-1)*20-time.monotonic())):break
    if time.monotonic()-START>150:break
    guard()
    row={'event':'LLM_RESULT','case':i,'public_input':True,'input_characters':len(SYSTEM)+len(question)}
    try:
        before=health();r=gui()
        if r.get('playing') or r.get('job_pending') or before['active'] or before['pending']:
            output({'event':'CASE_SKIPPED','case':i,'reason':'live_or_background_request_active'});continue
        p=owner(i*2,'llm');p.update(task='dialogue',messages=[{'role':'system','content':SYSTEM},{'role':'user','content':question}],
            options={'think':False,'num_predict':120,'output_format':'json'},budget_ms=30000)
        result,elapsed,size=inference('llm',p);reply=json.loads(result['text'])
        valid=isinstance(reply,dict) and set(reply)=={'reply_text','emotion','avatar_action'} and isinstance(reply['reply_text'],str) and bool(reply['reply_text'].strip()) and reply['emotion']=='friendly' and reply['avatar_action']==''
        assert valid,'public_output_contract'
        row.update(ok=True,rpc_ms=elapsed,response_bytes=size,metrics=result.get('metrics'),reply_characters=len(reply['reply_text']),public_reply=reply['reply_text'],health_before=before,health_after=health())
    except Exception as e:row.update(ok=False,error=type(e).__name__+':'+str(e)[:120])
    output(row)
    if STOP.is_set():break
    row={'event':'TTS_RESULT','case':i,'public_input':True,'text_characters':len(text)}
    try:
        before=health();p=owner(i*2+1,'tts');p.update(text=text,budget_ms=30000)
        result,elapsed,size=inference('tts',p);a=result['audio'];pcm=base64.b64decode(a['pcm_base64'],validate=True)
        assert a['encoding']=='pcm_s16le' and a['channels']==1 and a['sample_rate']==24000 and len(pcm)==a['samples']*2 and hashlib.sha256(pcm).hexdigest()==a['sha256'],'pcm_contract'
        samples=array.array('h');samples.frombytes(pcm);peak=max(abs(x) for x in samples);assert peak>0,'silent_output'
        duration=a['samples']/a['sample_rate'];after=health()
        row.update(ok=True,rpc_ms=elapsed,response_bytes=size,samples=a['samples'],sample_rate=a['sample_rate'],audio_seconds=duration,
            rpc_real_time_factor=elapsed/1000/duration,pcm_sha256=a['sha256'],peak_amplitude=peak,
            cache_hit=(after.get('tts_stats') or {}).get('last_cache_hit'),health_before=before,health_after=after)
        del pcm,samples,result
    except Exception as e:row.update(ok=False,error=type(e).__name__+':'+str(e)[:120])
    output(row)
STOP.wait(max(0,START+180-time.monotonic()));STOP.set();t.join(timeout=4);guard()
output({'event':'END','elapsed_seconds':time.monotonic()-START,'final':gui(),'health':health(),'errors':ERRORS,
        'axis_commands':0,'playback_requests':0,'source_config_changes':0,'private_media_exported':False})
'''


def build(contract):
    source = (BASE / "dialogue_latency_20261101/watch_board_latency.py").read_text(encoding="utf-8-sig")
    wanted = {"obj", "token", "metrics", "enum", "jobs", "project"}
    defs = [ast.get_source_segment(source, n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    observer = ast.parse((BASE / "functional_only_check_20261102/functional_only_observer.py").read_text(encoding="utf-8"))
    board = next(n.value.value for n in observer.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BOARD_MAIN" for t in n.targets))
    defs += [ast.get_source_segment(board, n) for n in ast.parse(board).body if isinstance(n, ast.FunctionDef) and n.name == "extended"]
    assert len(defs) == 7
    payload = "import hashlib,http.client,json,re,time\nfrom pathlib import Path\nCONTRACT=" + repr(contract) + "\n" + "\n\n".join(defs) + "\n" + REMOTE
    compile(payload, "public_performance_remote", "exec")
    return payload


def host_observer(stop):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with (HERE / "windows_gpu_health.jsonl").open("x", encoding="utf-8") as out:
        n = 0
        while not stop.is_set():
            began = time.monotonic()
            row = {"host_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "host_mono": began}
            try:
                p = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw,clocks.current.sm", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                vals = [x.strip() for x in p.stdout.strip().split(",")]
                assert p.returncode == 0 and len(vals) == 9
                row["gpu"] = {"name": vals[0], **{k: float(v) for k, v in zip(["total_mib","used_mib","free_mib","utilization_pct","memory_utilization_pct","temperature_c","power_w","sm_mhz"], vals[1:])}}
            except Exception as e: row["gpu_error_type"] = type(e).__name__
            if n % 2 == 0:
                try:
                    with opener.open("http://192.168.50.1:8797/health", timeout=2) as r: h = json.load(r)
                    row["models"] = h
                except Exception as e: row["health_error_type"] = type(e).__name__
            out.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n");out.flush()
            n += 1;stop.wait(max(0,1-(time.monotonic()-began)))


def main():
    h = json.loads(HANDOFF.read_text(encoding="utf-8-sig"))
    assert h["permission_active"] and h["ready"] and h["root_frozen_for_window"]
    assert dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=230) < dt.datetime.fromisoformat(h["window_end_utc"])
    contract = {"run_id":"performance-"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"), "boot_id":h["boot_id"],
        "startup_path":"/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json", "startup_sha256":h["startup_sha256"], "owners":h["owners"],
        "handoff_sha256":hashlib.sha256(HANDOFF.read_bytes()).hexdigest()}
    payload=build(contract)
    if "--check-only" in __import__('sys').argv:
        print(json.dumps({"syntax_valid":True,"case_pairs":6,"board_calls":0}));return
    atomic(HERE/"CONTRACT.json",contract)
    ssh=PROJECT/"deliverables/2026-10-18_board_dialogue/board_ssh.py"
    assert hashlib.sha256(ssh.read_bytes()).hexdigest()=="6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373"
    key=Path.home()/".ssh/aura_5090_board_ed25519";known=Path.home()/".ssh/aura_migration_known_hosts"
    p=subprocess.Popen([shutil.which("ssh.exe") or shutil.which("ssh"),"-i",str(key),"-o","UserKnownHostsFile="+str(known),"-o","IdentitiesOnly=yes","-o","BatchMode=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=4","root@192.168.50.2","python3 -B -"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8")
    p.stdin.write(payload);p.stdin.close()
    stop=threading.Event();worker=threading.Thread(target=host_observer,args=(stop,),daemon=True);worker.start()
    start=dt.datetime.now(dt.timezone.utc).isoformat()
    atomic(HERE/"STATUS.json",{"phase":"RUNNING","run_id":contract["run_id"],"host_started_utc":start,"ssh_pid":p.pid,"payload_sha256":hashlib.sha256(payload.encode()).hexdigest(),"duration_seconds":180})
    events=[]
    try:
        with (HERE/"board_model_gui.jsonl").open("x",encoding="utf-8") as out:
            for line in p.stdout:
                v=json.loads(line);v["host_received_utc"]=dt.datetime.now(dt.timezone.utc).isoformat()
                out.write(json.dumps(v,ensure_ascii=False,separators=(",",":"))+"\n");out.flush()
                if v.get("event")!="GUI_SAMPLE":
                    events.append(v)
                    print(json.dumps({k:v[k] for k in ["event","case","ok","rpc_ms","audio_seconds","board_mono","elapsed_seconds","error","reason"] if k in v},ensure_ascii=False),flush=True)
    finally:
        stop.set();worker.join(timeout=5)
    err=p.stderr.read();rc=p.wait(timeout=5)
    atomic(HERE/"STATUS.json",{"phase":"FINISHED" if rc==0 else "FAILED","run_id":contract["run_id"],"host_started_utc":start,"host_ended_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"exit_code":rc,"stderr":err[:1600],"events":events,"axis_commands":0,"playback_requests":0,"source_changes":0})
    if rc:raise RuntimeError("Remote measurement failed; retained status")


if __name__=="__main__":main()
