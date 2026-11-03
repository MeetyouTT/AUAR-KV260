"""Real child/file interleavings for normal stop; no model processes or ports."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
HOST=OUT.parents[1]/'deliverables/2026-10-30_board_owner/integration/production_model_host'
sys.path.insert(0,str(HOST))
source=Path(os.environ.get('AURA_MANAGE_UNDER_TEST',str(HOST/'manage.py')))
spec=importlib.util.spec_from_file_location('manage_stop_race_under_test',source)
manage=importlib.util.module_from_spec(spec);spec.loader.exec_module(manage)

CHILD=r'''
import json,os,sys,time
from pathlib import Path
root=Path(sys.argv[1]);session=sys.argv[2];mode=sys.argv[3]
control=root/'sessions'/session/'CONTROL.json'
gate=root/'metadata_probe_entered'
until=time.monotonic()+15
while not (control.exists() and gate.exists()):
    if time.monotonic()>until:raise RuntimeError('isolated test gate timed out')
    time.sleep(.005)
request=json.loads(control.read_bytes())
assert request['session_id']==session and request['action']=='stop'
state=dict(session_id=session,status='FAILED' if mode=='failed' else 'CLOSED',
    server_closed=True,owned_tts_closed=mode!='tts_open',
    last_control=dict(control_id=request['control_id'],status='ACCEPTED',action='stop'))
def write(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value),encoding='utf-8');os.replace(temporary,path)
write(control.parent/'status.json',state)
if mode in ('foreign_session','changed_record'):
    record=json.loads((root/'latest.json').read_bytes())
    if mode=='foreign_session':
        other='b'*32;record['session_id']=other;state['session_id']=other
        target=root/'sessions'/other;target.mkdir()
        write(target/'status.json',state)
    record['owner']['created_utc']='different-owner-birth'
    write(root/'latest.json',record)
'''


class StopExitRace(unittest.TestCase):
    def exercise(self,mode):
        with tempfile.TemporaryDirectory(prefix='aura-stop-race-') as directory:
            root=Path(directory);session='a'*32
            state_dir=root/'sessions'/session;state_dir.mkdir(parents=True)
            (state_dir/'status.json').write_text(json.dumps(dict(session_id=session,status='READY')))
            child=subprocess.Popen([sys.executable,'-I','-B','-c',CHILD,str(root),session,mode],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            record=dict(schema_version=1,session_id=session,owner=dict(pid=child.pid,
                created_utc='original-child-birth',executable=sys.executable,command_sha256='public-test'))
            (root/'latest.json').write_text(json.dumps(record))
            calls=[]
            def actual_child_owner_check(expected):
                self.assertEqual(expected,record)
                calls.append('metadata_check')
                if len(calls)==1:
                    self.assertIsNone(child.poll());return True
                # stop has already read READY. The real child now writes its
                # terminal state and exits while the metadata call is pending.
                stale=json.loads((state_dir/'status.json').read_bytes())
                self.assertEqual(stale['status'],'READY')
                (root/'metadata_probe_entered').write_text('public test gate')
                self.assertEqual(child.wait(timeout=5),0)
                return False
            try:
                with patch.object(manage,'HERE',root),patch.object(manage,'LATEST',root/'latest.json'),\
                        patch.object(manage,'same_owner',side_effect=actual_child_owner_check):
                    if mode=='clean':
                        result=manage.stop(wait_seconds=5)
                        self.assertEqual(result['status'],'CLOSED')
                        self.assertEqual(result['session_id'],session)
                        self.assertTrue(result['state']['owned_tts_closed'])
                        self.assertFalse(result['forced_action'])
                    else:
                        code='stop_owner_record_changed' if mode in ('foreign_session','changed_record') else 'owner_exit_not_confirmed_clean'
                        with self.assertRaisesRegex(RuntimeError,code):manage.stop(wait_seconds=5)
                self.assertEqual(len(calls),2)
            finally:
                if child.poll() is None:child.terminate();child.wait(timeout=5)
                child.communicate(timeout=5)

    def test_real_child_closes_during_metadata_probe(self):self.exercise('clean')
    def test_changed_session_after_exit_is_rejected(self):self.exercise('foreign_session')
    def test_changed_record_same_session_is_rejected(self):self.exercise('changed_record')
    def test_failed_child_terminal_state_is_rejected(self):self.exercise('failed')
    def test_open_tts_terminal_state_is_rejected(self):self.exercise('tts_open')


if __name__=='__main__':unittest.main()
