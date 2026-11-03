"""Read-only runtime guards shared by this service recovery."""
import ast,hashlib,json,subprocess,sys,time,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path[:0]=[str(A),str(H.parent/'2026-10-18_board_dialogue')]
from board_ssh import ssh
def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
def save(name,value):(H/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def powershell(arguments,timeout=30):
 result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',*arguments],capture_output=True,timeout=timeout)
 if result.returncode:raise RuntimeError((result.stdout+result.stderr).decode('utf-8-sig',errors='replace')[-1000:])
 return result.stdout.decode('utf-8-sig',errors='replace')
def board():
 tree=ast.parse((H.parent/'2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
 script=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in node.targets))
 return json.loads(ssh('python3 -B -',script,timeout=20))
def same_board(current,previous):
 assert current['preflight_ready'],'Board must be idle, mic/listening/motion off and exact source pins valid'
 for key in ('boot','actual_runtime','actual_config','config_sha256','pins','settings','pan'):
  assert current[key]==previous[key],'Concurrent board change: '+key
 for key in ('ui_service','camera_service'):
  for field in ('MainPID','ExecStart','NRestarts','ActiveState'):assert current[key][field]==previous[key][field],key+field
def windows():
 command="""[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);[PSCustomObject]@{
last_boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o');
models=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'ollama*' -or $_.Name -eq 'llama-server.exe'} | Select-Object ProcessId,CreationDate,Name);
listeners=@(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in @(8791,8792,8795,8796,8810,8812,11434,11435)} | Select-Object LocalAddress,LocalPort,OwningProcess | Sort-Object LocalPort,LocalAddress);
ipv4=@(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like '192.168.50.*'} | Select-Object IPAddress,InterfaceAlias)
} | ConvertTo-Json -Depth 5 -Compress"""
 return json.loads(powershell(['-Command',command]))
def checkpoint(phase):
 token=uuid.uuid4().hex;powershell(['-File',str(H/'start_checkpoint.ps1'),'-Job',token,'-Phase',phase])
 path=H/('db_checkpoint_'+token+'.json');until=time.monotonic()+25
 while not path.exists() and time.monotonic()<until:time.sleep(.2)
 value=json.loads(path.read_text(encoding='utf-8'));assert value['status']=='PASS',value.get('error')
 return value
