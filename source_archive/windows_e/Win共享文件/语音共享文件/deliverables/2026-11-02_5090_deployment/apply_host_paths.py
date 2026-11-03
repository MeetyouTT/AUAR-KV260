from pathlib import Path
import json, shutil
ROOT=Path('E:/Win共享文件/语音共享文件')
OUT=ROOT/'deliverables/2026-11-02_5090_deployment'
BACK=OUT/'before'
changed=[]
staged={}
def replace(rel,old,new):
    p=ROOT/rel; original=BACK/rel; raw=original.read_bytes() if original.exists() else p.read_bytes(); text=staged.get(rel,raw.decode('utf-8-sig').replace('\r\n','\n'))
    if text.count(old)!=1:raise RuntimeError(f'Expected exactly one edit anchor: {rel}')
    b=BACK/rel;b.parent.mkdir(parents=True,exist_ok=True)
    if not b.exists():b.write_bytes(raw)
    staged[rel]=text.replace(old,new)
    changed.append(rel)

runtime='deliverables/2026-10-30_board_owner/integration/production_model_host/production_runtime.py'
replace(runtime,"""    expected=dict(schema_version=1,host='192.168.50.1',port=8797,
        allowed_peers=['192.168.50.2'],local_health=True,startup_seconds=300,lifetime_seconds=None)
    if set(value)!=set(expected)|{'voice_python'} or any(value[k]!=v for k,v in expected.items()):
        raise ValueError('fixed_inference_configuration_required')""","""    expected=dict(schema_version=1,port=8797,
        local_health=True,startup_seconds=300,lifetime_seconds=None)
    # Local setup can run before the board cable is connected. Each allowed
    # bind address has exactly one peer scope; arbitrary LAN exposure is refused.
    endpoints=(('192.168.50.1',['192.168.50.2']),('127.0.0.1',['127.0.0.1']))
    if (set(value)!=set(expected)|{'host','allowed_peers','voice_python'}
            or any(value[k]!=v for k,v in expected.items())
            or (value['host'],value['allowed_peers']) not in endpoints):
        raise ValueError('fixed_inference_configuration_required')""")
replace('deliverables/2026-10-30_board_owner/integration/production_model_host/manage.py',
"    connection=http.client.HTTPConnection('192.168.50.1',8797,timeout=2)",
"    settings,_=config()\n    connection=http.client.HTTPConnection(settings['host'],settings['port'],timeout=2)")
replace('deliverables/2026-10-18_board_dialogue/board_ssh.py',
"from pathlib import Path\nimport subprocess", "from pathlib import Path\nimport os\nimport shutil\nimport subprocess")
replace('deliverables/2026-10-18_board_dialogue/board_ssh.py',
"KEY=Path('C:/Users/35870/.codex/visualizations/2026/10/09/01a12110-3ba4-7651-b3d7-2e6560916eb6/board-access-20261018/id_ed25519')",
"KEY=Path(os.environ.get('AURA_BOARD_SSH_KEY', str(Path.home()/'.ssh/aura_5090_board_ed25519')))\nKNOWN_HOSTS=Path(os.environ.get('AURA_BOARD_SSH_KNOWN_HOSTS', str(Path.home()/'.ssh/aura_migration_known_hosts')))\nSSH=shutil.which('ssh.exe') or shutil.which('ssh')")
replace('deliverables/2026-10-18_board_dialogue/board_ssh.py',
"    result=subprocess.run(['C:/Windows/System32/OpenSSH/ssh.exe','-i',str(KEY),'-o','IdentitiesOnly=yes',",
"    if not SSH or not KEY.is_file() or not KNOWN_HOSTS.is_file():\n        raise RuntimeError('Configure host-local SSH executable, private key and verified known-hosts file')\n    result=subprocess.run([SSH,'-i',str(KEY),'-o','UserKnownHostsFile='+str(KNOWN_HOSTS),'-o','IdentitiesOnly=yes',")

replace('start_model_dashboard.ps1',
"    [switch]$Snapshot,", "    [string]$VoicePython = '',\n    [switch]$Snapshot,")
replace('start_model_dashboard.ps1',
"$dashboardPythonRoot = Join-Path $env:USERPROFILE '.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python'",
"$dashboardConfig = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $dashboardRoot 'aura/config/model_inference.local.json') | ConvertFrom-Json\n$dashboardConsole = if ($VoicePython) { $VoicePython } else { [string]$dashboardConfig.voice_python }\n$dashboardPythonRoot = Split-Path -Parent $dashboardConsole")
replace('start_model_dashboard.ps1',
"    $dashboardConsole = Join-Path $dashboardPythonRoot 'python.exe'\n    $dashboardProof = Join-Path $dashboardRoot 'deliverables\\2026-10-30_runtime_dashboard\\manual_snapshot.json'",
"    $dashboardProof = Join-Path $dashboardRoot 'aura\\output\\runtime_dashboard_snapshot.json'")
config_path=ROOT/'aura/config/model_inference.local.json'
b=BACK/'aura/config/model_inference.local.json';b.parent.mkdir(parents=True,exist_ok=True)
if not b.exists():b.write_bytes(config_path.read_bytes())
config=json.loads(config_path.read_bytes())
config.update(host='127.0.0.1',allowed_peers=['127.0.0.1'],voice_python='D:/AURARuntimes/voice-py310/Scripts/python.exe')
config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
changed.append('aura/config/model_inference.local.json')
for rel,text in staged.items():
    (ROOT/rel).write_bytes(text.encode('utf-8'))
(OUT/'local_path_changes.json').write_text(json.dumps({'files':list(dict.fromkeys(changed)),
    'mode':'LOCAL_ONLY_UNTIL_BOARD_CONNECTED','backup':str(BACK)},indent=2),encoding='utf-8')
print(json.dumps({'modified':list(dict.fromkeys(changed))}))
