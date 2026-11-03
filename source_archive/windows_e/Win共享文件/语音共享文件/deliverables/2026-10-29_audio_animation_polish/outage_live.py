"""Existing single native UI, real owned CPU host loss and independent recovery."""
import json,queue,subprocess,sys,threading
from board_guard import H,capture
from board_ssh import KEY
c=json.loads((H/'candidate.json').read_text(encoding='utf-8'));b=capture()
assert b['safe'] and b['actual_runtime']==c['runtime'] and not b['mismatches']
assert json.loads((H/'muted_live_probe.json').read_text())['original_mixer_restored']
remote=(H.parent/'2026-10-27_windows_portrait/live_ui_outage_remote.py').read_text(encoding='utf-8')
command=['C:/Windows/System32/OpenSSH/ssh.exe','-i',str(KEY),'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
 '-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4','root@192.168.50.2','python3 -B -']
p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
p.stdin.write(remote);p.stdin.close();lines=queue.Queue()
def reader():
    for line in p.stdout:lines.put(line)
threading.Thread(target=reader,daemon=True).start()
try:
    first=json.loads(lines.get(timeout=15));assert first['event']=='REMOTE_READY'
    ps=r'''
$ErrorActionPreference='Stop'
$portraitPython=PYTHON
$portraitRecovery=RECOVERY
$portraitStartup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$portraitCommand='"'+$portraitPython+'" -B "'+$portraitRecovery+'"'
$portraitProcess=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$portraitCommand;CurrentDirectory=ROOT;ProcessStartupInformation=$portraitStartup}
if ($portraitProcess.ReturnValue -ne 0) {throw 'Independent recovery creation failed; stop aborted'}
& STOP
'''
    def quote(s):return "'"+str(s).replace("'","''")+"'"
    ps=ps.replace('PYTHON',quote(sys.executable)).replace('RECOVERY',quote(H/'recover_host.py')).replace('ROOT',quote(H)).replace('STOP',quote(H/'stop_owned_portrait.ps1'))
    stopped=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',ps],capture_output=True,timeout=15)
    assert stopped.returncode==0,stopped.stderr.decode('utf-8','replace')[-1000:]
    v=json.loads(lines.get(timeout=50));assert p.wait(timeout=10)==0
    (H/'live_ui_outage.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in v.items() if key!='rows'}));assert v['status']=='PASS'
finally:
    # Also recover synchronously if this monitor failed; the independent WMI
    # recovery remains in force if the caller is interrupted.
    restored=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(H/'start_host.ps1')],capture_output=True,timeout=70)
    if p.poll() is None:
        p.terminate();p.wait(timeout=10)
    assert restored.returncode==0,restored.stderr.decode('utf-8','replace')[-1000:]
