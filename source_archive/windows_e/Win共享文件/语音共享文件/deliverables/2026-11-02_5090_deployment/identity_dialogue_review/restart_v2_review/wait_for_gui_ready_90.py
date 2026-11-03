"""Wait at most 90 seconds for filtered API readiness; no state is exported."""
import http.client
import json
from pathlib import Path
import subprocess
import time

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
started=time.monotonic();deadline=started+90
ready=False;unit_failed=False
while time.monotonic()<deadline:
    unit=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=ActiveState,MainPID'],capture_output=True,text=True,timeout=3)
    assert unit.returncode==0
    fields=dict(line.split('=',1) for line in unit.stdout.splitlines() if '=' in line)
    if fields.get('ActiveState')=='failed' and fields.get('MainPID')=='0':
        unit_failed=True;break
    connection=http.client.HTTPConnection('127.0.0.1',8783,timeout=2)
    try:
        connection.request('GET','/api/state');response=connection.getresponse();raw=response.read(2097153)
        if response.status==200 and len(raw)<=2097152:
            value=json.loads(raw)
            pair=value.get('character_pair',{});hands=value.get('handsfree_dialogue',{});display=value.get('avatar_display',{})
            ready=(value.get('ui_page')=='main' and pair.get('state')=='READY'
                and hands.get('enabled') is False and hands.get('state')=='PAUSED'
                and hands.get('microphone_open') is False and display.get('visible') is True)
            value=raw=None
            if ready:break
    except (OSError,ValueError,http.client.HTTPException):pass
    finally:connection.close()
    time.sleep(min(1,max(0,deadline-time.monotonic())))
print(json.dumps({'api_ready_for_observation':ready,'unit_failed':unit_failed,
    'waited_seconds':round(time.monotonic()-started,3),'board_mutations':False,
    'api_state_exported':False}))
