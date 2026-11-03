"""Real owned-host outage/recovery with board client; never touches native UI."""
import json,queue,subprocess,sys,threading,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import KEY
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import json,sys,time
from pathlib import Path
from types import SimpleNamespace
root=Path(ROOT);sys.path.insert(0,str(root/'aura'))
from board.runtime.portrait_offload import PortraitOffload
config=json.loads((root/'aura/config/board_avatar_gtk.json').read_text())['portrait_offload'];config['fps']=24
client=PortraitOffload(config,(423,438));core=SimpleNamespace(talk_gen=1,idle_gain=1.,emotion='neutral',reply_text='',fsm=SimpleNamespace(state=SimpleNamespace(label='IDLE')))
began=time.monotonic();announced=False;local_after_ready=False;recovered=False;frames=0;rows=[]
try:
    while time.monotonic()-began<25:
        at=time.monotonic()-began;value=client.offer(core,at,0.,0.,0,'none');status=client.status()
        if value is not None and '_portrait_rgb' in value:
            assert len(value['_portrait_rgb'])==423*438*3;frames+=1
        if not announced and frames>=5:
            print(json.dumps({'event':'REMOTE_READY'}),flush=True);announced=True
        if announced and status['mode']=='local':local_after_ready=True
        if local_after_ready and status['mode']=='remote':recovered=True
        if len(rows)==0 or at-rows[-1]['at']>=.25:rows.append(dict(at=at,**status))
        time.sleep(1/(24 if status['mode']=='remote' else 8))
    report={'status':'PASS' if announced and local_after_ready and recovered else 'FAIL',
        'remote_started':announced,'local_fallback_observed':local_after_ready,'remote_recovered':recovered,
        'verified_rgb_frames':frames,'rows':rows,'final':client.status(),'physical_native_sink':False,
        'physical_audio':False,'microphone':False,'motor':False}
finally:client.close()
print(json.dumps(report),flush=True)
'''.replace('ROOT',repr(c['runtime']))
live_ui='--live-ui' in sys.argv
if live_ui:remote=(HERE/'live_ui_outage_remote.py').read_text(encoding='utf-8')
command=['C:/Windows/System32/OpenSSH/ssh.exe','-i',str(KEY),'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
    '-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4','root@192.168.50.2','python3 -B -']
process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
process.stdin.write(remote);process.stdin.close();lines=queue.Queue()
def reader():
    for line in process.stdout:lines.put(line)
threading.Thread(target=reader,daemon=True).start()
try:
    first=json.loads(lines.get(timeout=15));assert first['event']=='REMOTE_READY'
    recovery=str(HERE/'recover_host.py');python=sys.executable
    # An independent WMI parent restores only this owned service even if this
    # diagnostic caller is interrupted after stopping it.
    ps=r'''
$ErrorActionPreference='Stop'
$portraitPython=PYTHON
$portraitRecovery=RECOVERY
$portraitStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$portraitCommand='"'+$portraitPython+'" -B "'+$portraitRecovery+'"'
$portraitProcess=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$portraitCommand;CurrentDirectory=ROOT;ProcessStartupInformation=$portraitStartup}
if ($portraitProcess.ReturnValue -ne 0) { throw 'Independent host recovery creation failed' }
& STOP
'''.replace('PYTHON',"'"+python.replace("'","''")+"'").replace('RECOVERY',"'"+recovery.replace("'","''")+"'")
    ps=ps.replace('ROOT',"'"+str(HERE).replace("'","''")+"'").replace('STOP',"'"+str(HERE/'stop_host.ps1').replace("'","''")+"'")
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',ps],capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr.decode('utf-8','replace')
    value=json.loads(lines.get(timeout=50));assert process.wait(timeout=10)==0
    (HERE/('live_ui_outage.json' if live_ui else 'outage_probe.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in value.items() if k!='rows'}))
    assert value['status']=='PASS'
finally:
    if process.poll() is None:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
