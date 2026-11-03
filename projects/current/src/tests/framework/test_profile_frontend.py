"""Client selection, local dialog and release use synthetic grants only."""
from collections import deque
import http.client
import json
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock,patch

import pytest

from board.runtime.audio.channel_jobs import ChannelConversationJobs
from common.conversation_selection import ConversationSelection
from common.profile_selection import read_selection
from tools.profile_selection_ui import profile_dialog
from tests.framework.test_profile_memory import prepared,KEY


def grant():
    return dict(mode='profile',board_boot_id='boot-test',session_id='chosen-session',
                access_token='8'*64,conversation_id='b'*32,profile_id='a'*32,profile_name='Synthetic A')


def jobs(tmp_path):
    value=ChannelConversationJobs.__new__(ChannelConversationJobs)
    value.condition=threading.Condition();value.closed=False;value.waiting=value.active=value.channel=None
    value.boot_id='boot-test';value.session_id='guest-session';value.generation=0
    value.progress=deque();value.results=deque();value.profile_selection=None
    value.conversation_selection=ConversationSelection(tmp_path/'anonymous.json')
    value.identity_flow=SimpleNamespace(reset=lambda:None,public=lambda:{})
    value.acks=SimpleNamespace(submit=MagicMock())
    value.config={'enabled':True,'host':'127.0.0.1','port':8792,'timeout_ms':120000}
    value.include_voice=True;value.last_ack=value.last_voice_route=None;value.feedback_assets={};value.feedback_error=''
    return value


def test_client_selection_new_personal_conversation_keeps_grant_actor_and_no_disk_secret(tmp_path):
    client=jobs(tmp_path);value=grant();client.select_profile(value)
    first=client.generation
    cid=client.select_conversation(resume=False)
    assert cid!=value['conversation_id'] and client.session_id==value['session_id']
    assert client.profile_selection['conversation_id']==cid
    assert client.generation>first and not client.conversation_selection.path.exists()
    public=json.dumps(client.public())
    assert value['access_token'] not in public and value['profile_name'] not in public and value['profile_id'] not in public
    client.select_profile(None)
    assert client.session_id!=value['session_id'] and client.profile_selection is None
    assert client.acks.submit.call_count==1
    assert value['access_token'] not in client.conversation_selection.path.read_text()


def test_foreign_boot_and_busy_client_cannot_change_selection(tmp_path):
    client=jobs(tmp_path)
    with pytest.raises(ValueError):client.select_profile(dict(grant(),board_boot_id='old-boot'))
    client.active='current-request'
    with pytest.raises(ValueError):client.select_profile(grant())
    assert client.profile_selection is None and client.generation==0


def test_reading_a_selection_does_not_activate_it_and_bad_files_are_rejected(tmp_path):
    path=tmp_path/'selection.json';path.write_text(json.dumps(grant()))
    import os
    if os.name!='nt':path.chmod(0o600)
    value=read_selection(path,'boot-test')
    assert value['access_token']==grant()['access_token']
    with pytest.raises(ValueError):read_selection(path,'another-boot')
    path.write_text('x'*8193)
    with pytest.raises(ValueError):read_selection(path,'boot-test')


@pytest.mark.parametrize('response,expected',[(0,'cancel'),(1,'guest'),(2,'profile')])
def test_local_dialog_requires_explicit_click_and_never_places_credential_in_message(tmp_path,response,expected):
    Gtk=SimpleNamespace(ResponseType=SimpleNamespace(CANCEL=0,NO=1,YES=2),Dialog=MagicMock(),Label=lambda **kw:kw)
    dialog=Gtk.Dialog.return_value;dialog.run.return_value=response
    client=SimpleNamespace(profile_selection=None,select_profile=MagicMock())
    stage=SimpleNamespace(Gtk=Gtk,window=None,board_boot_id='boot-test',transcriber=client,
                          controller=SimpleNamespace(public=lambda:{'phase':'IDLE','playing':False}))
    with patch('common.profile_selection.read_selection',return_value=grant()):result=profile_dialog(stage)
    if expected=='cancel':client.select_profile.assert_not_called()
    elif expected=='guest':client.select_profile.assert_called_once_with(None)
    else:client.select_profile.assert_called_once_with(grant())
    assert grant()['access_token'] not in json.dumps(result)


def test_live_listening_does_not_open_profile_switch_dialog():
    stage=SimpleNamespace(controller=SimpleNamespace(public=lambda:{'phase':'IDLE','handsfree_dialogue':{'enabled':True}}))
    with pytest.raises(ValueError,match='暂停'):profile_dialog(stage)


def test_release_rejects_old_credential_without_revoking_new_selection(tmp_path):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    model,pid,meta,old=prepared(tmp_path)
    fresh,_=model.profile_access.issue(pid,meta)
    server=AsrServer(('127.0.0.1',0),SimpleNamespace(model_id='fixture'),handler=ModelHandler);server.models=model
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def release(token,origin=None):
        c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
        try:
            headers={'Content-Type':'application/json','X-Aura-Profile':'v1:'+token}
            if origin:headers['Origin']=origin
            c.request('POST','/v1/profile/release',json.dumps({k:meta[k] for k in ('board_boot_id','session_id')}),headers)
            r=c.getresponse();raw=r.read(4096);return r.status,raw
        finally:c.close()
    try:
        assert release(old)[0]==403
        assert model.profile_access.resolve(fresh,meta).profile_id==pid
        assert release(fresh,'http://untrusted.invalid')[0]==403
        assert model.profile_access.resolve(fresh,meta).profile_id==pid
        status,raw=release(fresh)
        assert status==200 and json.loads(raw)=={'released':True}
        with pytest.raises(PermissionError):model.profile_access.resolve(fresh,meta)
    finally:server.shutdown();server.server_close();thread.join(2)
