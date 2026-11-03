"""Visible, click-owned MCP01 sampling. No speaker model runs on the board."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import wave


def active_aura():
    roots=set()
    for line in subprocess.check_output(['ps','-eo','args'],universal_newlines=True).splitlines():
        try: args=shlex.split(line)
        except ValueError: continue
        for arg in args:
            if arg.endswith('/tools/board_avatar_gtk.py'):
                root=Path(arg).resolve().parents[1]
                if (root/'board/runtime/audio/capture.py').is_file():roots.add(str(root))
    if len(roots)!=1:raise RuntimeError('Need one active avatar runtime')
    return Path(roots.pop())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True)
    parser.add_argument('--restore-monitor',action='store_true')
    args=parser.parse_args()
    if len(args.session)!=32 or any(c not in '0123456789abcdef' for c in args.session):
        parser.error('Require a random session token')
    aura=active_aura();sys.path.insert(0,str(aura))
    from board.runtime.audio.capture import Mcp01Capture
    from tools.board_avatar_gtk import register_font
    register_font(aura/'assets/fonts/DroidSansFallbackFull.ttf')
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk,GLib,Gdk
    directory=Path.home()/'.local/share/aura/speaker_test_recordings'/args.session
    directory.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(directory,0o700)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def owner_state():
        with opener.open('http://127.0.0.1:8783/api/state',timeout=2) as response:return json.load(response)
    def busy():
        value=owner_state()
        if type(value.get('playing')) is not bool or type(value.get('paused')) is not bool:
            raise ValueError('Invalid audio owner state')
        return (value['playing'] or value['paused'] or value.get('phase')!='IDLE'
                or value.get('automatic_conversation',{}).get('enabled') is not False
                or value.get('handsfree_dialogue',{}).get('enabled') is True)
    def restore():
        if not args.restore_monitor:return
        value=owner_state()
        if value.get('handsfree_dialogue',{}).get('enabled') is False:
            request=urllib.request.Request('http://127.0.0.1:8783/api/command',
                data=json.dumps({'type':'conversation_toggle'}).encode(),
                headers={'Origin':'http://127.0.0.1:8783','Content-Type':'application/json'})
            with opener.open(request,timeout=4) as response:json.load(response)

    class MeteredCapture(Mcp01Capture):
        level=0.
        def _read_pcm(self,process):
            pcm=bytearray()
            while True:
                chunk=process.stdout.read(min(4096,self.max_samples*2-len(pcm)+1))
                if not chunk:break
                pcm.extend(chunk)
                if len(pcm)>self.max_samples*2:raise ValueError('Audio exceeds capture limit')
                even=chunk[:len(chunk)//2*2]
                if even:
                    values=struct.unpack('<%dh'%(len(even)//2),even)
                    self.level=math.sqrt(sum(v*v for v in values)/len(values))/32768
                with self._lock:self._sample_count=len(pcm)//2
            return pcm

    class Window(Gtk.Window):
        prompts=[
            '今天我用自然的声音来登记，周围已经安静，希望玩偶以后可以通过声音认出我。',
            '我平时会自然地和玩偶聊天，不需要刻意改变声音，希望下次说话时它还能认出我。',
            '这次我保持平时聊天的语气，换一些不同的内容，让玩偶记录我的声音特点。',
            '这一段是新的验证录音，请根据前面登记的声音，检查是不是同一个人在说话。']
        def __init__(self):
            super().__init__(title='声纹测试 · 板端MCP01采样')
            self.capture=None;self.thread=None;self.index=0;self.clips=[];self.closing=False;self.status='READY';self.error=''
            self.last_saved=0;self.last_result=''
            self.set_keep_above(True);self.fullscreen();self.set_border_width(16)
            self.connect('delete-event',self.close_window)
            box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);self.add(box)
            self.title_label=Gtk.Label(label='声纹测试 · 第1段 / 共4段');self.title_label.set_name('heading');box.pack_start(self.title_label,False,False,0)
            self.device=Gtk.Label(label='板端 MCP01 麦克风 · 电脑/耳机麦克风不参与');box.pack_start(self.device,False,False,0)
            self.status_label=Gtk.Label(label='尚未录音：点击下方按钮后，再开始说话');self.status_label.set_name('status');box.pack_start(self.status_label,False,False,0)
            self.prompt=Gtk.Label(label=self.prompts[0]);self.prompt.set_line_wrap(True);self.prompt.set_max_width_chars(38);self.prompt.set_justify(Gtk.Justification.CENTER);box.pack_start(self.prompt,True,True,0)
            self.timer=Gtk.ProgressBar();self.timer.set_show_text(True);self.timer.set_text('0.0 / 10.0 秒');box.pack_start(self.timer,False,False,0)
            self.meter=Gtk.ProgressBar();self.meter.set_show_text(True);self.meter.set_text('实际麦克风音量：待开录');box.pack_start(self.meter,False,False,0)
            self.start=Gtk.Button(label='开始第1段登记录音');self.start.set_size_request(-1,64);self.start.connect('clicked',self.start_clip);box.pack_start(self.start,False,False,0)
            close=Gtk.Button(label='退出采样并恢复免点击监听');close.connect('clicked',self.close_window);box.pack_start(close,False,False,0)
            note=Gtk.Label(label='点击开始会保存这一段测试声音。第4段仅验证，不参与登记模板。');note.set_line_wrap(True);box.pack_start(note,False,False,0)
            css=Gtk.CssProvider();css.load_from_data(b'window { background:#102c3a; color:#f1f6fa; font:18px "Droid Sans Fallback";} label#heading {font-size:26px;} label#status {color:#89efd3;font-size:22px;} button {font:22px "Droid Sans Fallback";padding:10px;} progressbar trough {min-height:16px;}')
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.show_all();self.present();GLib.timeout_add(100,self.tick);self.save_state()

        def save_state(self):
            value={'scope':'VISIBLE_BOARD_MCP01_SAMPLING','session_id':args.session,'status':self.status,
                   'index':self.index,'clips':self.clips,'error':self.error,'pid':os.getpid(),
                   'microphone_open':bool(self.capture and self.capture.snapshot()['state']=='RECORDING')}
            temporary=directory/'sampler_state.tmp';temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(directory/'sampler_state.json')

        def start_clip(self,*_):
            if self.closing or self.status=='RECORDING' or self.index>=4:return
            self.error='';self.start.set_sensitive(False);self.status='STARTING';self.status_label.set_text('正在检查麦克风独占权限…');self.save_state()
            self.thread=threading.Thread(target=self.record,daemon=True);self.thread.start()

        def record(self):
            try:
                self.capture=MeteredCapture(busy,max_seconds=10)
                self.capture.start();GLib.idle_add(self.mark_started)
                while self.capture.snapshot()['state']=='RECORDING':
                    if self.closing or busy():self.capture.cancel();raise RuntimeError('录音已取消或播放状态发生变化')
                    time.sleep(.1)
                self.capture.stop();clip=self.capture.take()
                if self.closing:return
                number=self.index+1;path=directory/('clip-%02d.wav'%number)
                with path.open('xb') as stream:
                    with wave.open(stream,'wb') as output:
                        output.setparams((1,2,16000,0,'NONE','not compressed'));output.writeframes(clip.pcm)
                meta=dict(clip.metadata(),session_id=args.session,clip_number=number,
                          source='ACTUAL_MCP01_VISIBLE_USER_CLICK',wav_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                path.with_suffix('.json').write_text(json.dumps(meta,indent=2),encoding='utf-8');os.chmod(path,0o600);os.chmod(path.with_suffix('.json'),0o600)
                GLib.idle_add(self.completed,meta)
            except Exception as exc:GLib.idle_add(self.failed,str(exc))
            finally:
                if self.capture:self.capture.close()

        def mark_started(self):
            if not self.closing:
                self.status='RECORDING';self.status_label.set_text('正在录音 · 现在开口 · 10秒后自动结束');self.save_state()
            return False

        def completed(self,meta):
            if self.closing:return False
            self.clips.append(meta);self.index+=1;self.status='READY' if self.index<4 else 'SAMPLES_READY'
            self.timer.set_fraction(1);self.timer.set_text('本段已保存，等待电脑质量检查')
            if self.index<4:
                self.title_label.set_text('声纹测试 · 第%d段 / 共4段'%(self.index+1));self.prompt.set_text(self.prompts[self.index])
                self.status_label.set_text('上一段已保存。准备好后点击下一段，再开口。')
                self.start.set_label('开始第%d段%s录音'%(self.index+1,'独立验证' if self.index==3 else '登记'));self.start.set_sensitive(True)
            else:
                self.title_label.set_text('4段样本采集完成');self.status_label.set_text('等待电脑验证 · 此时尚未登记成功')
                self.prompt.set_text('可以在聊天中告诉我“已完成屏幕采样”。检查结果会显示在这里。');self.start.set_label('等待电脑检查');self.start.set_sensitive(False)
            self.save_state();return False

        def failed(self,message):
            if self.closing:return False
            self.status='ERROR';self.error=message;self.status_label.set_text('未开始/已失败：'+message);self.start.set_sensitive(True);self.save_state();return False

        def tick(self):
            if self.closing:return False
            if self.capture and self.status=='RECORDING':
                snapshot=self.capture.snapshot();seconds=snapshot['sample_count']/16000
                self.timer.set_fraction(min(1,seconds/10));self.timer.set_text('%.1f / 10.0 秒'%seconds)
                self.meter.set_fraction(min(1,self.capture.level*12));self.meter.set_text('实际麦克风音量：%d'%round(self.capture.level*32768))
            if time.monotonic()-self.last_saved>1:
                self.save_state();self.last_saved=time.monotonic()
                result=directory/'verification_result.json'
                if result.is_file():
                    try:
                        message=json.loads(result.read_text(encoding='utf-8'))['message']
                        if message!=self.last_result:self.status_label.set_text(message);self.last_result=message
                    except (ValueError,KeyError):pass
            return True

        def close_window(self,*_):
            if self.closing:return True
            self.closing=True
            if self.capture:self.capture.cancel()
            if self.thread and self.thread.is_alive():self.thread.join(timeout=4)
            self.status='CLOSED';self.save_state()
            try:restore()
            except Exception as exc:(directory/'restore_error.txt').write_text(str(exc),encoding='utf-8')
            Gtk.main_quit();self.destroy();return True

    window=Window()
    try:Gtk.main()
    finally:
        if not window.closing:window.close_window()


if __name__=='__main__':main()
