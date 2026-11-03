"""Isolated client and hidden GTK dialog verification; no UI service restart."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
files={p.relative_to(HERE/'board_candidate').as_posix():p.read_text(encoding='utf-8') for p in (HERE/'board_candidate').rglob('*.py')}
payload=base64.b64encode(json.dumps(files).encode()).decode()
script=r'''
import base64,collections,hashlib,importlib,json,os,subprocess,sys,threading,uuid
from pathlib import Path
from types import SimpleNamespace
files=json.loads(base64.b64decode('PAYLOAD'))
base=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/runtime/aura')
stage=Path('/home/root/aura-profile-memory-candidate-20261026')/uuid.uuid4().hex
stage.mkdir(parents=True,exist_ok=False)
before=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
for name,text in files.items():
    p=(stage/name).resolve();p.relative_to(stage);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text);compile(text,str(p),'exec')
sys.path.insert(0,str(base));sys.dont_write_bytecode=True
for package in ('common','board','board.runtime','board.runtime.audio','tools'):
    module=importlib.import_module(package);module.__path__=[str(stage/package.replace('.','/'))]+list(module.__path__)
from board.runtime.audio.channel_jobs import ChannelConversationJobs
from common.conversation_selection import ConversationSelection
checks=[]
client=ChannelConversationJobs.__new__(ChannelConversationJobs)
client.condition=threading.Condition();client.closed=False;client.waiting=client.active=client.channel=None
client.boot_id='synthetic-boot';client.session_id='guest-session';client.generation=0
client.progress=collections.deque();client.results=collections.deque();client.profile_selection=None
client.conversation_selection=ConversationSelection(stage/'synthetic-anonymous.json')
client.identity_flow=SimpleNamespace(reset=lambda:None,public=lambda:{})
client.acks=SimpleNamespace(submit=lambda *a:None);client.include_voice=True
client.config={'enabled':True,'host':'127.0.0.1','port':8792,'timeout_ms':120000}
client.feedback_assets={};client.feedback_error='';client.last_ack=client.last_voice_route=None
selection={'mode':'profile','board_boot_id':'synthetic-boot','session_id':'synthetic-session',
           'conversation_id':'a'*32,'profile_id':'b'*32,'access_token':'8'*64,'profile_name':'Synthetic A'}
client.select_profile(selection);old=client.profile_selection['conversation_id']
new=client.select_conversation(resume=False)
assert old!=new and client.session_id=='synthetic-session'
assert selection['access_token'] not in json.dumps(client.public())
checks.append('profile actor preserved across new conversation; public state redacted')
client.select_profile(None)
assert client.profile_selection is None and client.session_id!='synthetic-session'
assert selection['access_token'] not in client.conversation_selection.path.read_text()
checks.append('guest switch drops profile and starts separate anonymous conversation')
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk
assert Gtk.init_check()[0]
class HiddenDialog(Gtk.Dialog):
    def show_all(self):self.get_content_area().show_all()
    def run(self):return Gtk.ResponseType.CANCEL
from tools.profile_selection_ui import profile_dialog
import common.profile_selection
common.profile_selection.read_selection=lambda *a:selection
window=Gtk.Window()
ui=SimpleNamespace(Gtk=SimpleNamespace(Dialog=HiddenDialog,Label=Gtk.Label,ResponseType=Gtk.ResponseType),
                   window=window,controller=SimpleNamespace(public=lambda:{'phase':'IDLE','playing':False}),
                   board_boot_id='synthetic-boot',transcriber=client)
result=profile_dialog(ui)
assert result['message']=='已返回' and client.profile_selection is None
window.destroy();checks.append('actual GTK dialog constructed hidden; cancel activates no profile')
after=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
assert before==after
value=dict(status='PASS',stage=str(stage),checks=checks,production_ui_pid_unchanged=True,
           production_deployed=False,microphone_used=False,playback=False,physical_motion=False,
           source_sha256={name:hashlib.sha256(text.encode()).hexdigest() for name,text in files.items()})
(stage/'verification.json').write_text(json.dumps(value,indent=2))
print(json.dumps(value))
'''.replace('PAYLOAD',payload)
value=json.loads(ssh('DISPLAY=:0 python3 -B -',script,timeout=40))
(HERE/'board_candidate_verification.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value))
