"""Local operator CLI. Credentials/grants stay outside the shared project."""
import argparse
import base64
import csv
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import uuid
import wave

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))


def private_write(path,value):
    path=Path(path).resolve()
    try:path.relative_to(AURA.parents[1])
    except ValueError:pass
    else:raise ValueError('Keep profile credentials outside the shared project')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    try:
        fd=os.open(str(temporary),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(value);f.flush();os.fsync(f.fileno())
        if os.name=='nt':
            system=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32'
            who=subprocess.run([str(system/'whoami.exe'),'/user','/fo','csv','/nh'],capture_output=True,text=True,check=True)
            sid=next(csv.reader(io.StringIO(who.stdout)))[1]
            subprocess.run([str(system/'icacls.exe'),str(temporary),'/inheritance:r','/grant:r','*'+sid+':(F)'],
                           capture_output=True,check=True)
        temporary.replace(path)
    finally:
        if temporary.exists():temporary.unlink()


def key_path():
    config=json.loads((AURA/'config/profile_access.local.json').read_text(encoding='utf-8-sig'))
    return Path(os.path.expandvars(config['control_key_file'])).expanduser()


def configure_verifier(path):
    raw=path.read_text(encoding='utf-8').strip()
    import re
    if not re.fullmatch('[0-9a-f]{64}',raw):raise ValueError('Invalid private operator credential')
    target=AURA/'config/profile_access.local.json'
    temporary=target.with_name(target.name+'.tmp-'+uuid.uuid4().hex)
    value={'control_key_file':str(path),'control_key_sha256':hashlib.sha256(raw.encode()).hexdigest()}
    try:
        temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');temporary.replace(target)
    finally:
        if temporary.exists():temporary.unlink()


def control(host,port,key,payload):
    c=http.client.HTTPConnection(host,port,timeout=5)
    try:
        c.request('POST','/v1/profile/control',json.dumps(payload).encode(),
                  {'Content-Type':'application/json','Authorization':'Bearer '+key})
        r=c.getresponse();raw=r.read(32769)
        if len(raw)>32768:raise ValueError('Control response exceeds bound')
        value=json.loads(raw)
        if r.status!=200:raise RuntimeError('Profile control rejected: HTTP '+str(r.status))
        return value
    finally:c.close()


def board_transport():
    sys.path.insert(0,str(AURA.parent/'deliverables/2026-10-18_board_dialogue'))
    from board_ssh import ssh
    return ssh


def publish_board(value):
    # Target the actual UI HOME, which differs from the SSH account HOME on
    # this device. The operator credential is never sent to the board.
    encoded=base64.b64encode(json.dumps(value,ensure_ascii=False).encode()).decode()
    script=r'''
import base64,json,os,subprocess,uuid
from pathlib import Path
value=json.loads(base64.b64decode('PAYLOAD'))
assert value['board_boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip())
environment=Path('/proc/%d/environ'%pid).read_bytes().split(b'\0')
homes=[p[5:].decode() for p in environment if p.startswith(b'HOME=')]
assert len(homes)==1
home=Path(homes[0]).resolve();assert str(home) in ('/root','/home/root')
folder=home/'.local/share/aura';folder.mkdir(parents=True,exist_ok=True)
folder.resolve().relative_to(home)
target=folder/'profile-selection.json';assert not target.is_symlink()
temporary=folder/('profile-selection.tmp-'+uuid.uuid4().hex)
try:
    fd=os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
    os.replace(str(temporary),str(target))
finally:
    if temporary.exists():temporary.unlink()
print(json.dumps({'delivered':True,'activated':False}))
'''.replace('PAYLOAD',encoded)
    result=json.loads(board_transport()('python3 -B -',script,timeout=15))
    if result!={'delivered':True,'activated':False}:raise RuntimeError('Board grant delivery failed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='192.168.50.1');parser.add_argument('--port',type=int,default=8792)
    parser.add_argument('--key-file',type=Path)
    parser.add_argument('--grant-file',type=Path)
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('setup');sub.add_parser('configure');sub.add_parser('list')
    create=sub.add_parser('create');create.add_argument('--name',required=True);create.add_argument('--consent',action='store_true')
    select=sub.add_parser('select');select.add_argument('--profile-id',required=True)
    select.add_argument('--board-boot-id');select.add_argument('--session-id');select.add_argument('--conversation-id')
    select.add_argument('--ttl',type=int,default=900)
    select.add_argument('--board',action='store_true',help='Deliver a boot-bound grant; user activates it on the touchscreen')
    sub.add_parser('guest')
    chat=sub.add_parser('chat-wav');chat.add_argument('wav',type=Path)
    args=parser.parse_args()
    path=(args.key_file or key_path()).resolve()
    grant_path=(args.grant_file or path.with_name('profile-session.json')).resolve()
    if args.action=='setup':
        if path.exists():raise ValueError('Control credential already exists; refusing replacement')
        private_write(path,secrets.token_hex(32)+'\n')
        configure_verifier(path)
        print(json.dumps({'configured':True,'key_file':str(path),'service_restart_required':True}));return
    if args.action=='configure':
        configure_verifier(path)
        print(json.dumps({'verifier_configured':True,'service_restart_required':True}));return
    if args.action=='chat-wav':
        from board.runtime.audio.voice_channel import VoiceChannel
        session=json.loads(grant_path.read_text(encoding='utf-8'))
        with wave.open(str(args.wav),'rb') as f:
            if (f.getframerate(),f.getnchannels(),f.getsampwidth())!=(16000,1,2):raise ValueError('Require 16kHz mono PCM16')
            pcm=f.readframes(f.getnframes())
        meta=dict(protocol='aura-asr-1',board_boot_id=session['board_boot_id'],session_id=session['session_id'],
                  request_id=uuid.uuid4().hex,generation=0,capture_id=uuid.uuid4().hex,
                  sample_count=len(pcm)//2,pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=120000)
        channel=VoiceChannel(args.host,args.port)
        try:
            value=channel.exchange(meta,pcm,lambda h,p:None,conversation=session['conversation_id'],
                                   profile_token=session.get('access_token'))
            # Receipt-only CLI never claims playback or commits an assistant ACK.
            print(json.dumps(value,ensure_ascii=False))
        finally:channel.close()
        return
    key=path.read_text(encoding='utf-8').strip()
    if args.action in ('create','list'):
        payload={'action':args.action}
        if args.action=='create':payload.update(name=args.name,consent=args.consent)
        print(json.dumps(control(args.host,args.port,key,payload),ensure_ascii=False));return
    old=json.loads(grant_path.read_text(encoding='utf-8')) if grant_path.exists() else {}
    payload={'action':args.action,'board_boot_id':old.get('board_boot_id','windows-operator-'+uuid.uuid4().hex),
             'session_id':old.get('session_id',uuid.uuid4().hex)}
    if args.action=='select':
        payload.update(profile_id=args.profile_id,ttl=args.ttl)
        for field in ('board_boot_id','session_id','conversation_id'):
            if getattr(args,field) is not None:payload[field]=getattr(args,field)
        if args.board:
            payload['board_boot_id']=board_transport()('cat /proc/sys/kernel/random/boot_id').strip()
            payload['session_id']=uuid.uuid4().hex
    result=control(args.host,args.port,key,payload)
    result.update(board_boot_id=payload['board_boot_id'],session_id=payload['session_id'])
    private_write(grant_path,json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    if args.action=='select' and args.board:publish_board(result)
    print(json.dumps({'mode':result['mode'],'grant_file':str(grant_path),
                      'expires_in_seconds':result.get('expires_in_seconds')}))


if __name__=='__main__':main()
