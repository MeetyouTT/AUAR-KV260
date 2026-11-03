"""Finish read-only status and private-data checks before the Ubuntu handoff."""
import datetime,json,time
from maintenance import H,read,save,capture,http,owners,checkpoint,powershell
from board_guard import ssh
b=read('baseline.json');board=capture()
assert board['safe'] and not board['mismatches']
assert board['actual_runtime']==b['board']['actual_runtime']
assert board['pins']==b['board']['pins'] and board['camera']==b['board']['camera']
for key in ('boot','mechanical_sha256','firmware','fdt_sha256','vart','settings'):
    assert board[key]==b['board'][key],key
diagnostics=json.loads(ssh('python3 -B -',r'''
import json,subprocess
lines=subprocess.check_output(['journalctl','-u','aura-avatar-ui.service','-n','30','--no-pager','-o','cat'],text=True).splitlines()
print(json.dumps([s for s in lines if '"event": "FAILED"' in s or 'Failed to start' in s]))
''',timeout=10))
voice=http(8792);hub=http(8812,'127.0.0.1');current=owners()
assert voice['ready'] and voice['service_revision']=='voice-board-vision-20261030-r12'
assert hub['speaker_ready'] and hub['anonymous_binding']['enabled']
assert hub['visual_processing']['semantic_model_enabled'] is False
skip={8792,8812,8810}
def stable(rows):return sorted((r['LocalAddress'],r['LocalPort'],r['OwningProcess']) for r in rows if r['LocalPort'] not in skip)
assert stable(current['listeners'])==stable(b['owners']['listeners'])
assert not any(r['LocalPort']==8810 for r in current['listeners'])
save('private_after.json',checkpoint('after'))
script=H/'compare_private.py'
command='"C:\\Users\\35870\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" -B "'+str(script)+'"'
ps=r'''$startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$result=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=COMMAND;CurrentDirectory=ROOT;ProcessStartupInformation=$startup}
if ($result.ReturnValue -ne 0) {throw 'Private comparison launch failed'}
'''.replace('COMMAND',"'"+command.replace("'","''")+"'").replace('ROOT',"'"+str(H).replace("'","''")+"'")
powershell(['-Command',ps]);until=time.monotonic()+25
while not (H/'database_verification.json').exists() and time.monotonic()<until:time.sleep(.2)
private=read('database_verification.json');assert private['status']=='PASS',private.get('error')
value=dict(status='HANDED_OFF_TO_UBUNTU',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           windows_ready=True,voice_revision=voice['service_revision'],retired_visual_port_closed=True,
           weights_deleted=False,model_directory='D:/AIModels/qwen3-vl-2b-interaction',
           board_patch_deployed=False,board_restored_and_safe=True,board=board,
           board_startup_errors=diagnostics,private_database_verification='PASS',owners=current,
           structured_visual_timeline_deployed=False,no_deployment_transaction_running=True)
save('handoff_state.json',value)
print(json.dumps({k:value[k] for k in ('status','windows_ready','board_restored_and_safe','weights_deleted','private_database_verification')}))
print(json.dumps({'board_startup_errors':diagnostics}))
