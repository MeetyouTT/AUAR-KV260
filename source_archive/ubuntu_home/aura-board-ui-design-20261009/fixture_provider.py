#!/usr/bin/env python3
"""Explicit local UI fixture. Never opens a device, model, database or PL."""
import io
import json
from pathlib import Path
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs,urlsplit
from PIL import Image,ImageDraw

BOOT = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
EPOCH = 'ui-fixture-'+str(time.monotonic_ns())
SESSION = 'fixture-session'
KEY = {'camera_epoch':'fixture-camera','track_id':7,'track_generation':2}
STATE = {'audio':'READY','interaction':'IDLE','reply':'接口测试数据：未运行识别或模型。','generation':1}
SEQUENCE = FRAME = 0
FRAMES = {}
COMMANDS = []
image = Image.new('RGB',(569,148),'#dfebf3')
ImageDraw.Draw(image).text((25,60),'UI INTERFACE TEST - NOT CAMERA',fill='#025e8f')
stream = io.BytesIO();image.save(stream,format='JPEG');JPEG = stream.getvalue()


def millis():return int(time.monotonic()*1000)


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,code,value,mime='application/json',headers=None):
        body = value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
        self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
        for name,value in (headers or {}).items():self.send_header(name,value)
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_GET(self):
        global SEQUENCE,FRAME
        path = urlsplit(self.path)
        if path.path == '/v1/ui/status':
            SEQUENCE += 1;FRAME += 1;stamp = millis()
            ref = {'camera_epoch':KEY['camera_epoch'],'frame_id':FRAME,'captured_mono_ms':stamp}
            FRAMES[FRAME] = ref
            while len(FRAMES)>4:FRAMES.pop(min(FRAMES))
            modules = {'interaction':{'state':STATE['interaction'],'transcript':'接口联调，不是真实录音',
                         'reply':STATE['reply'],'timings_ms':{}},
                       'camera':{'state':'READY'},'vision':{'state':'READY','people_count':1},
                       'npu':{'state':'UNKNOWN'},'pl':{'state':'UNKNOWN'},
                       'target':{'state':'CONFIRMED','selected':KEY,'tracks':[{'key':KEY,'label':'测试对象 7'}]},
                       'identity':{'state':'UNKNOWN','db_version':1,'people':[{'person_id':'fixture-person','display_name':'测试身份'}]},
                       'motion':{'state':'FAULT','detail':'接口联调的测试状态，不代表硬件故障'},
                       'host':{'state':'READY','detail':'测试服务，不是模型'},'audio':{'state':STATE['audio']}}
            caps = {name:True for name in ('record_start','record_stop','cancel','ask_frame',
                                          'target_select','identity_enroll','identity_delete')}
            self.respond(200,{'protocol_version':'aura-ui-1','board_boot_id':BOOT,'service_epoch':EPOCH,
                'sequence':SEQUENCE,'observed_mono_ms':stamp,'ttl_ms':2500,'source_kind':'fixture',
                'context':{'session_id':SESSION,'request_id':'fixture-request','generation':STATE['generation']},
                'modules':modules,'capabilities':caps,'preview':ref})
        elif path.path == '/v1/ui/preview.jpg':
            args = parse_qs(path.query);frame = int(args.get('frame_id',['0'])[0])
            if frame not in FRAMES or args.get('camera_epoch') != [KEY['camera_epoch']]:
                self.respond(404,{'error':'fixture frame expired'});return
            self.respond(200,JPEG,'image/jpeg',{'X-Aura-Boot-Id':BOOT,
                'X-Aura-Camera-Epoch':KEY['camera_epoch'],'X-Aura-Frame-Id':str(frame)})
        elif path.path == '/fixture/commands':self.respond(200,COMMANDS)
        else:self.respond(404,{'error':'unknown fixture route'})
    def do_POST(self):
        if self.path != '/v1/ui/commands':self.respond(404,{});return
        size = int(self.headers.get('Content-Length','0'))
        if not 0<size<=8192:self.respond(400,{});return
        value = json.loads(self.rfile.read(size));action = value.get('action')
        accepted = (value.get('protocol_version') == 'aura-ui-1' and value.get('board_boot_id') == BOOT
                    and value.get('service_epoch') == EPOCH and millis()<value.get('deadline_mono_ms',0)
                    and action in ('record_start','record_stop','cancel','ask_frame','target_select',
                                   'identity_enroll','identity_delete'))
        if accepted:
            COMMANDS.append(value)
            if action == 'record_start':
                STATE.update(audio='RECORDING',interaction='LISTENING',reply='接口测试：录音请求已受理。')
            elif action == 'record_stop':STATE.update(audio='READY',interaction='IDLE',reply='接口测试：停止请求已受理。')
            elif action == 'cancel':
                # Deliberately publish a late answer for the SAME context after ACK.
                STATE.update(audio='READY',interaction='PROCESSING',reply='迟到回答：应被界面抑制。')
        owner = {name:value.get(name) for name in ('protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation')}
        self.respond(200,dict(owner,accepted=accepted,detail='fixture acceptance only'))


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1',8790),Handler).serve_forever()
