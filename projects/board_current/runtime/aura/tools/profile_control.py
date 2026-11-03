"""Authenticated local profile selection; public voice requests use scoped grants."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import time

from common.profile_access import ProfileAccess


def access_from_config(aura):
    path=Path(aura)/'config/profile_access.local.json'
    if not path.is_file():return ProfileAccess()
    config=json.loads(path.read_text(encoding='utf-8-sig'))
    if set(config) not in ({'control_key_file'},{'control_key_file','control_key_sha256'}) or not isinstance(config['control_key_file'],str):
        raise ValueError('Invalid local profile control configuration')
    if config.get('control_key_sha256') is not None:
        return ProfileAccess(verifier=config['control_key_sha256'])
    key=Path(os.path.expandvars(config['control_key_file'])).expanduser()
    return ProfileAccess(key.read_text(encoding='utf-8').strip() if key.is_file() else None)


@contextmanager
def turn_profile(models,meta):
    value=getattr(models,'profile_turns',{}).get(meta['request_id'])
    if value is None:
        yield None;return
    if value['context']!=meta:raise PermissionError('Profile turn belongs to another recording')
    with models.profile_access.use(value['grant']) as pid:yield pid


def profile_options(pid):
    return {} if pid is None else {'profile':pid}


def validate_request(models,meta,cid,token=None):
    pid=None
    if token is not None:
        access=getattr(models,'profile_access',None)
        if access is None:raise PermissionError('Profile access is not configured')
        grant=access.resolve(token,meta);pid=grant.profile_id
    store=getattr(models,'conversations',None)
    if callable(getattr(store,'check_scope',None)):store.check_scope(cid,profile=pid)
    return pid


def handle_control(handler):
    try:
        local={handler.server.server_address[0],'127.0.0.1','::1'}
        if handler.client_address[0] not in local or handler.headers.get('Origin') or handler.headers.get('Transfer-Encoding'):
            raise PermissionError('Profile control requires a local operator')
        values=handler.headers.get_all('Authorization',[])
        if len(values)!=1 or not re.fullmatch('Bearer [0-9a-f]{64}',values[0]):raise PermissionError('Missing local operator credential')
        models=handler.server.models
        access=getattr(models,'profile_access',None)
        if access is None:raise PermissionError('Profile control is not configured')
        access.authenticate(values[0][7:])
        sizes=handler.headers.get_all('Content-Length',[])
        if len(sizes)!=1 or handler.headers.get('Content-Type')!='application/json':raise ValueError('Expected one bounded JSON body')
        size=int(sizes[0])
        if not 2<=size<=4096:raise ValueError('Profile control body exceeds bound')
        raw=handler.rfile.read(size)
        if len(raw)!=size:raise ValueError('Incomplete profile control body')
        value=json.loads(raw)
        if not isinstance(value,dict):raise ValueError('Invalid profile control request')
        action=value.get('action')
        if action=='list' and set(value)=={'action'}:
            result={'profiles':models.conversations.profiles()}
        elif action=='create' and set(value)=={'action','name','consent'}:
            result={'profile_id':models.conversations.create_profile(value['name'],consent=value['consent'])}
        elif action in ('select','guest'):
            required={'action','board_boot_id','session_id'}|({'profile_id'} if action=='select' else set())
            optional={'ttl','conversation_id'} if action=='select' else set()
            if not required<=set(value) or set(value)-required-optional:raise ValueError('Invalid selection fields')
            if action=='guest':
                access.revoke(value);result={'mode':'guest','conversation_id':secrets.token_hex(16)}
            else:
                models.conversations.require_profile(value['profile_id'])
                cid=value.get('conversation_id',secrets.token_hex(16))
                models.conversations.check_scope(cid,profile=value['profile_id'])
                token,grant=access.issue(value['profile_id'],value,ttl=value.get('ttl',900))
                result={'mode':'profile','access_token':token,'conversation_id':cid,
                        'expires_in_seconds':value.get('ttl',900),'expires_unix':time.time()+value.get('ttl',900),
                        'profile_id':grant.profile_id,
                        'profile_name':next(p['name'] for p in models.conversations.profiles() if p['id']==grant.profile_id)}
        else:raise ValueError('Unknown profile control action')
        handler.send(200,result)
    except PermissionError:handler.send(403,{'error':'Profile access denied'})
    except (ValueError,TypeError,KeyError,OSError):handler.send(400,{'error':'Invalid profile control request'})


def handle_release(handler):
    try:
        if handler.headers.get('Origin') or handler.headers.get('Transfer-Encoding'):raise PermissionError()
        tokens=handler.headers.get_all('X-Aura-Profile',[]);sizes=handler.headers.get_all('Content-Length',[])
        if len(tokens)!=1 or not re.fullmatch('v1:[0-9a-f]{64}',tokens[0]):raise PermissionError()
        if len(sizes)!=1 or not 2<=int(sizes[0])<=512 or handler.headers.get('Content-Type')!='application/json':raise ValueError()
        value=json.loads(handler.rfile.read(int(sizes[0])))
        if not isinstance(value,dict) or set(value)!={'board_boot_id','session_id'}:raise ValueError()
        access=handler.server.models.profile_access
        # Keep resolve and revoke atomic, so an obsolete token cannot revoke a
        # newer selection for the same device/session.
        with access.lock:
            access.resolve(tokens[0][3:],value);access.revoke(value)
        handler.send(200,{'released':True})
    except (PermissionError,AttributeError):handler.send(403,{'error':'Profile access denied'})
    except (ValueError,TypeError,KeyError,OSError):handler.send(400,{'error':'Invalid profile release request'})
