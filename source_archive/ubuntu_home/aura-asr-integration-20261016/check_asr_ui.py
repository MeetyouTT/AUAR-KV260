"""Actual GTK layout; injected ASR states are host UI checks, not board ASR."""
import json
from pathlib import Path
import sys
import subprocess
import time

AURA=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0,str(AURA))
from tools.preview_board_touch import LayoutPreview

WORK=Path(__file__).resolve().parent
actual=json.loads((WORK/'actual_asr.json').read_text())['records'][1]['result']

class Preview(LayoutPreview):
    def view(self):
        value=super().view()
        if value['snapshot']:
            value['snapshot']['modules'].pop('interaction',None)
            value['snapshot']['modules'].pop('host',None)
        return value

    def __init__(self):
        self.asr={'state':'IDLE'}
        self.rec={'state':'IDLE','can_start':True,'can_stop':False}
        super().__init__()

    def refresh(self):
        super().refresh()
        state={'phase':'IDLE','paused':False,'playing':False,'avatar_command_pending':0,
               'local_recording':self.rec,'local_transcription':self.asr}
        self.stage.refresh_runtime(state,self.stage.refresh_settings(state))
        self.stage.mode_label.set_text('主机界面验证 · 注入状态，非板端联网结果')
        return True

p=Preview()
out=WORK/'gtk-preview';out.mkdir(exist_ok=True)
report={'scope':'HOST_GTK_WITH_INJECTED_STATES','board_asr_verified':False,'screens':{}}
try:
    for name,value in [('pending',{'state':'TRANSCRIBING'}),('recognized',actual),
                       ('long_text',dict(actual,text='长文本布局测试。'*40)),
                       ('error',{'state':'ERROR','error':'ConnectionRefusedError: test-only'}),
                       ('empty',{'state':'EMPTY'}),('cancelled',{'state':'CANCELLED'})]:
        p.asr=value
        p.rec={'state':'READY' if name!='cancelled' else 'CANCELLED','can_start':True,'can_stop':False,
               'result':{'duration_seconds':5}}
        p.refresh();p.drain()
        stage=p.stage
        rect=stage.window.get_allocation()
        assert (rect.width,rect.height)==(1024,600),(name,rect.width,rect.height)
        scroll=stage.transcript_label.get_parent().get_parent()
        box=scroll.get_allocation()
        assert box.height<=60,(name,box.height)
        if name=='long_text':
            adj=scroll.get_vadjustment()
            assert adj.get_upper()>adj.get_page_size(),(adj.get_upper(),adj.get_page_size())
            adj.set_value(adj.get_upper()-adj.get_page_size());p.drain()
        if name=='recognized':assert stage.transcript_label.get_text()==actual['text']
        if name=='cancelled':assert '你好' not in stage.transcript_label.get_text()
        subprocess.run([sys.executable,'-B',str(AURA/'tools/board_screen_capture.py'),
                        str(out/(name+'.png'))],check=True,timeout=3)
        report['screens'][name]={'width':rect.width,'height':rect.height,'transcript':stage.transcript_label.get_text(),
                                 'scroll_height':box.height,'status':stage.status.get_text()}
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS','states':list(report['screens']),'scope':report['scope']}))
finally:p.close()
