"""Pure mock X11/process/guard fixtures; no Linux/X11/service/device calls."""
import copy
import ctypes as C
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('normal_close',ROOT/'x11_normal_close.py')
module=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=module;spec.loader.exec_module(module)


class Host:
    def __init__(self):
        self.owner=dict(pid=1366,birth='2302',cmdline_sha256='a'*64)
        self.proof=dict(boot_id='synthetic',sources_sha256='b'*64,
            unit=dict(MainPID='1296',Restart='no',SendSIGKILL='no',TimeoutStopUSec='infinity',Job=''))
        self.changed=False;self.exited=False;self.static_calls=0;self.change_at=None
    def static(self,plan):
        self.static_calls+=1
        result=copy.deepcopy(self.proof)
        if self.change_at==self.static_calls: result['sources_sha256']='c'*64
        return result
    def verify_owner(self,expected):
        if self.changed: raise module.Refused('owner_changed')
        return dict(self.owner)
    def process(self,pid): return None if self.exited else dict(self.owner)


class X:
    def __init__(self,host):
        self.host=host;self.sent=[];self.calls=0;self.change_at=None
        self.rows=[dict(window_id=0x120001,title_sha256='d'*64,normal=True,delete_supported=True)]
    def windows(self,pid):
        self.calls+=1;result=copy.deepcopy(self.rows)
        if self.calls==self.change_at: result[0]['title_sha256']='e'*64
        return result
    def send_delete(self,window): self.sent.append(window);self.host.exited=True


class Tests(unittest.TestCase):
    def setUp(self):
        self.host=Host();self.x=X(self.host)
        self.plan=dict(owner=dict(self.host.owner),display=':0')
    def test_lp64_xlib_abi_layout(self):
        self.assertEqual(C.sizeof(module.Data),40)
        self.assertEqual(C.sizeof(module.ClientMessage),96)
        self.assertEqual(C.sizeof(module.Event),192)
        self.assertEqual(module.ClientMessage.data.offset,56)
        self.assertEqual(module.ClientMessage.format.offset,48)
        self.assertEqual(module.ClientMessage.window.offset,32)
        self.assertEqual(C.sizeof(module.Attributes),136)
        self.assertEqual(module.Attributes.map_state.offset,92)
        self.assertEqual(module.Attributes.override_redirect.offset,120)
        self.assertEqual(C.sizeof(module.ErrorEvent),40)
    def test_default_inspect_emits_hash_metadata_only_and_no_send(self):
        result,_=module.inspect(self.plan,'f'*64,self.host,self.x)
        self.assertEqual(result['status'],'INSPECTED');self.assertEqual(self.x.sent,[])
        self.assertEqual(set(result['window']),{'window_id','title_sha256'})
        self.assertNotIn('title',result);self.assertNotIn('argv',result['owner'])
        self.assertGreaterEqual(self.host.static_calls,2)
    def test_dialog_ambiguity_missing_protocol_are_rejected(self):
        for rows in ([],self.x.rows*2,[dict(self.x.rows[0],normal=False)],[dict(self.x.rows[0],delete_supported=False)]):
            self.x.rows=rows
            with self.assertRaises(module.Refused):module.inspect(self.plan,'f'*64,self.host,self.x)
        self.assertEqual(self.x.sent,[])
    def test_original_unsafe_guards_inspect_only_and_refuse_close(self):
        self.host.proof['unit'].update(SendSIGKILL='yes',TimeoutStopUSec='25s')
        result,_=module.inspect(self.plan,'f'*64,self.host,self.x)
        self.assertFalse(result['close_guard_ready'])
        with self.assertRaises(module.Refused):
            module.request_close(self.plan,'f'*64,self.host,self.x,result['review_token'],0x120001)
        self.assertEqual(self.x.sent,[])
    def test_exact_token_window_and_owner_required(self):
        result,_=module.inspect(self.plan,'f'*64,self.host,self.x)
        for token,window in (('0'*64,0x120001),(result['review_token'],123)):
            with self.assertRaises(module.Refused):module.request_close(self.plan,'f'*64,self.host,self.x,token,window)
        self.host.changed=True
        with self.assertRaises(module.Refused):module.request_close(self.plan,'f'*64,self.host,self.x,result['review_token'],0x120001)
        self.assertEqual(self.x.sent,[])
    def test_source_proof_changes_before_after_refuse(self):
        self.host.change_at=2
        with self.assertRaises(module.Refused):module.inspect(self.plan,'f'*64,self.host,self.x)
        self.assertEqual(self.x.sent,[])
    def test_window_changes_in_immediate_repeat_refuse(self):
        result,_=module.inspect(self.plan,'f'*64,self.host,self.x)
        self.x.change_at=self.x.calls+2
        with self.assertRaises(module.Refused):module.request_close(self.plan,'f'*64,self.host,self.x,result['review_token'],0x120001)
        self.assertEqual(self.x.sent,[])
    def test_only_one_normal_delete_and_bounded_owner_observation(self):
        result,_=module.inspect(self.plan,'f'*64,self.host,self.x)
        closed=module.request_close(self.plan,'f'*64,self.host,self.x,result['review_token'],0x120001)
        self.assertTrue(closed['owner_exited']);self.assertFalse(closed['forced_action'])
        self.assertEqual(self.x.sent,[0x120001])
    def test_non_exiting_owner_is_reported_without_force_or_repeat(self):
        now=[0.]
        self.x.send_delete=lambda window:self.x.sent.append(window)
        result,_=module.inspect(self.plan,'f'*64,self.host,self.x)
        closed=module.request_close(self.plan,'f'*64,self.host,self.x,result['review_token'],0x120001,
            clock=lambda:now[0],wait=lambda seconds:now.__setitem__(0,now[0]+seconds),observe_seconds=20.)
        self.assertFalse(closed['owner_exited']);self.assertEqual(self.x.sent,[0x120001])
        self.assertLessEqual(now[0],20.001);self.assertFalse(closed['forced_action'])
    def test_actual_event_structure_is_only_wm_delete_client_message(self):
        class Lib:
            def XSendEvent(self,display,window,propagate,mask,event):
                value=C.cast(event,C.POINTER(module.Event)).contents.xclient
                self.captured=(display,window,propagate,mask,value.type,value.send_event,value.message_type,
                               value.format,list(value.data.l))
                return 1
        lib=Lib();client=module.X11.__new__(module.X11);client.lib=lib;client.display=17
        client.atom=lambda name:{'WM_PROTOCOLS':41,'WM_DELETE_WINDOW':42}[name]
        client.sync=lambda:None;client.send_delete(0x120001)
        self.assertEqual(lib.captured,(17,0x120001,0,0,33,1,41,32,[42,0,0,0,0]))
    def test_reviewed_original_plan_hash_and_exact_prefix(self):
        path=ROOT/'original_gui.plan.json';raw=path.read_bytes()
        value=module.load_plan(path,module.sha(raw))
        self.assertEqual(value['owner']['pid'],1366)
        self.assertEqual(value['owner']['birth'],'2302')
        with self.assertRaises(module.Refused):module.load_plan(path,'0'*64)
    def test_unreviewed_entry_outside_allowed_runtime_is_rejected(self):
        value=json.loads((ROOT/'original_gui.plan.json').read_text())
        value['owner']['argv'][2]='/home/root/unrelated/aura/tools/board_avatar_gtk.py'
        value['owner']['cmdline_sha256']=module.sha(('\0'.join(value['owner']['argv'])+'\0').encode())
        with tempfile.TemporaryDirectory(prefix='x11-public-plan-') as directory:
            path=Path(directory)/'plan.json';raw=json.dumps(value).encode();path.write_bytes(raw)
            with self.assertRaises(module.Refused):module.load_plan(path,module.sha(raw))


if __name__=='__main__':unittest.main(verbosity=2)
