"""Transport failure/ownership/deadline tests without a real listening socket."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from board.runtime.board_dialogue_client import InferenceHttpClient, ModelRequestError
from common.model_inference_wire import Owner, make_response


def payload():
    return dict(protocol_version=1,request_id='synthetic-request',board_boot_id='synthetic-boot',
                session_id='synthetic-session',generation=1,budget_ms=3000,
                task='dialogue',messages=[dict(role='user',content='公开测试')])


class Response:
    status=200
    def __init__(self,body,content_type='application/json'):self.body,self.content_type=body,content_type
    def getheader(self,key,default=''):return self.content_type
    def read(self,limit):return self.body[:limit]


class Connection:
    def __init__(self,host,port,timeout,response):
        self.host,self.port,self.timeout=host,port,timeout
        self.response,self.sock,self.closed,self.sent=response,None,False,[]
    def request(self,*args):self.sent.append(args)
    def getresponse(self):return self.response
    def close(self):self.closed=True


def client(body,**kwargs):
    connections=[]
    def factory(host,port,timeout):
        value=Connection(host,port,timeout,Response(body))
        connections.append(value);return value
    return InferenceHttpClient('192.168.50.1',8814,clock=lambda:10.,connection_factory=factory,**kwargs),connections


def test_validated_request_budget_shrinks_and_connection_closes():
    request=payload();response=make_response(Owner.from_dict(request),result=dict(text='{"reply_text":"测试"}'))
    transport,connections=client(json.dumps(response).encode())
    assert transport.request('llm',request,deadline=12)['ok']
    connection=connections[0]
    sent=json.loads(connection.sent[0][2])
    assert sent['budget_ms']==2000 and request['budget_ms']==3000
    assert connection.sent[0][1]=='/v1/inference/llm' and connection.closed
    assert len(connections)==1


def test_old_owner_is_rejected_and_not_retried():
    request=payload();owner=Owner.from_dict(dict(request,generation=0))
    transport,connections=client(json.dumps(make_response(owner,result=dict(text='{}'))).encode())
    with pytest.raises(ValueError):transport.request('llm',request,deadline=12)
    assert len(connections)==1 and connections[0].closed


def test_expired_and_cancelled_requests_send_nothing():
    transport,connections=client(b'{}')
    with pytest.raises(TimeoutError):transport.request('llm',payload(),deadline=9)
    with pytest.raises(InterruptedError):transport.request('llm',payload(),deadline=12,cancelled=lambda:True)
    assert not connections


def test_remote_cancel_can_use_target_owner_while_inference_is_registered():
    owner=Owner.from_dict(payload())
    body=make_response(owner,result=dict(cancelled=True,state='cancelled'))
    transport,connections=client(json.dumps(body).encode())
    original=Connection('192.168.50.1',8814,1,Response(b'{}'))
    transport._connections[(owner,'llm')]=original
    assert transport.cancel(owner)['ok']
    assert original.closed and len(connections)==1
    assert connections[0].sent[0][1]=='/v1/inference/cancel'
    assert json.loads(connections[0].sent[0][2])['request_id']==owner.request_id


def test_transport_does_not_accept_redirect_content():
    transport,connections=client(b'<html>redirect</html>')
    def factory(host,port,timeout):
        value=Connection(host,port,timeout,Response(b'',content_type='text/html'))
        connections.append(value);return value
    transport.connection_factory=factory
    with pytest.raises(ModelRequestError):transport.request('llm',payload(),deadline=12)
    assert len(connections)==1 and connections[0].closed
