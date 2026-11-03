"""Read-only board inventory, executed remotely through board_ssh.py."""
import http.client
import json
from pathlib import Path
import subprocess
import os

def get(host,port,path):
    connection=http.client.HTTPConnection(host,port,timeout=4)
    try:
        connection.request('GET',path);reply=connection.getresponse();raw=reply.read(1048576)
        return {'status':reply.status,'value':json.loads(raw)}
    except Exception as exc:return {'error':str(exc)}
    finally:connection.close()

report={'hostname':os.uname().nodename,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'ui':get('127.0.0.1',8783,'/api/state'), 'camera':get('127.0.0.1',8790,'/health'),
        'host_asr':get('192.168.50.1',8791,'/health'),
        'host_voice':get('192.168.50.1',8792,'/health'),
        'ui_unit':subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],universal_newlines=True),
        'processes':subprocess.check_output(['ps','-eo','pid,args'],universal_newlines=True)}
print(json.dumps(report,ensure_ascii=False))
