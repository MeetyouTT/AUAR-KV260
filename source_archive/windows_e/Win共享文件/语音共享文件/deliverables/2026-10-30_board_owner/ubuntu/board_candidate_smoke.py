"""Real ARM Python/HTTP/SQLite execution with synthetic model responses only."""
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import threading
import urllib.request

BASE='http://192.168.50.1:52003'
PIN='3a75d77ec2053624e5159f461585f2e15a6bde261fb90f825333b6abb71f6b5c'
ROOT=Path('/home/root/aura-board-owner-candidate-20261030/control-d14a9312f888b7b8')


def main():
    signal.alarm(45)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(BASE+'/manifest.json',timeout=4) as r:raw=r.read(65537)
    assert len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==PIN
    manifest=json.loads(raw)
    assert manifest['purpose']=='synthetic_board_control_smoke' and manifest['candidate_root']==str(ROOT)
    assert str(ROOT).startswith('/home/root/aura-board-owner-candidate-20261030/control-')
    assert not ROOT.is_symlink() and shutil.disk_usage('/home/root').free>16*1024*1024
    ROOT.mkdir(parents=True,exist_ok=True)
    sources={}
    for entry in manifest['entries']:
        relative=Path(entry['name']);assert not relative.is_absolute() and '..' not in relative.parts
        target=ROOT/relative;assert ROOT.resolve() in target.resolve().parents and not target.is_symlink()
        target.parent.mkdir(parents=True,exist_ok=True)
        with opener.open(BASE+'/assets/'+entry['sha256'],timeout=4) as r:data=r.read(entry['bytes']+1)
        assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
        if target.exists():assert target.read_bytes()==data
        else:
            with target.open('xb') as out:out.write(data)
        sources[entry['name']]=entry['sha256']
    for relative in ('common','board','board/runtime'):
        init=ROOT/'code'/relative/'__init__.py'
        if init.exists():assert init.read_bytes()==b''
        else:init.write_bytes(b'')
    sys.path.insert(0,str(ROOT/'code'))
    from common.board_memory import BoardMemoryStore
    from common.model_inference_wire import Owner,validate_request,make_response,audio_payload
    import board.runtime.board_dialogue as dialogue
    from board.runtime.board_dialogue_client import InferenceHttpClient
    assert str(ROOT/'code') in dialogue.__file__
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            kind=self.path.rsplit('/',1)[-1]
            payload=validate_request(kind,json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            owner=Owner.from_dict(payload);calls.append(kind)
            if kind=='llm':result=dict(text=json.dumps(dict(reply_text='公开合成测试通过。',emotion='friendly',avatar_action=''),ensure_ascii=False))
            elif kind=='tts':result=dict(audio=audio_payload(b'\x01\x00'*320))
            else:result=dict(cancelled=True,state='cancelled')
            raw=json.dumps(make_response(owner,result=result)).encode()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix='synthetic-smoke-',dir=str(ROOT)) as temporary:
            store=BoardMemoryStore(Path(temporary)/'synthetic.db')
            controller=dialogue.BoardDialogueController(store,InferenceHttpClient('127.0.0.1',server.server_port),
                board_boot_id='synthetic-arm-boot',system_prompt='公开合成测试：返回三字段JSON')
            scope=dict(kind='conversation',id='synthetic-arm-session')
            plan=controller.prepare_text('这是一条公开合成测试',scope=scope,session_id=scope['id'],generation=1,budget_ms=5000)
            assert not any(m['role']=='assistant' for m in store.context(scope)['messages'])
            try:controller.acknowledge(plan,playback_token=plan.playback_token,sha256='0'*64,samples=plan.samples)
            except ValueError:pass
            else:raise AssertionError('Foreign audio receipt accepted')
            controller.acknowledge(plan,playback_token=plan.playback_token,sha256=plan.sha256,samples=plan.samples)
            assert any(m['role']=='assistant' for m in store.context(scope)['messages'])
            second=controller.prepare_text('这是第二条公开合成测试',scope=scope,session_id=scope['id'],generation=2,budget_ms=5000)
            assert controller.cancel(scope['id'],generation=2)
            try:controller.acknowledge(second,playback_token=second.playback_token,sha256=second.sha256,samples=second.samples)
            except dialogue.StaleGeneration:pass
            else:raise AssertionError('Stale generation audio receipt accepted')
            assert controller.idle
            result=dict(actual_arm_execution=True,synthetic_model=True,real_llm_tts=False,
                actual_asr=False,actual_playback=False,hardware_actions=0,production_changed=False,
                candidate_root=str(ROOT),sources=sources,wire_calls=calls,
                checks=['real_sqlite','real_loopback_http','user_before_ack','full_receipt_required',
                        'assistant_after_ack','cancel','late_generation_rejected','idle_after_cancel'])
    finally:server.shutdown();server.server_close();thread.join(timeout=2)
    signal.alarm(0)
    print(json.dumps(result))


if __name__=='__main__':main()
