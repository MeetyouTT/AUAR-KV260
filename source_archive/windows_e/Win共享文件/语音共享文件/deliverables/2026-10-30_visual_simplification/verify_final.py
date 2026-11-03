"""Final metadata-only verification, retaining original source rows and models."""
import hashlib,http.client,json,socket,sys,time,urllib.error,xml.etree.ElementTree as ET
from pathlib import Path
from maintenance import H,P,A,read,save,capture,same,http,owners,checkpoint,powershell
from board_guard import ssh
from common.voice_service_capabilities import require_current_voice,source_fingerprint

b=read('baseline.json');deployed=read('board_deployment.json');assert deployed['status']=='COMMITTED'
current_board=capture();same(deployed['after'],current_board)
for key in ('boot','mechanical_sha256','settings','firmware','fdt_sha256','vart'):
    assert current_board[key]==b['board'][key],key
assert current_board['camera']==b['board']['camera']
changed=[n for n,v in b['board']['pins'].items() if current_board['pins'][n]!=v]
assert changed==['board/runtime/device_observer.py']
observer=json.loads(ssh('python3 -B -',r'''
import json,urllib.request
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as r:s=json.load(r)
v=s.get('device_observer',{})
assert v.get('enabled') is False and v.get('image_upload_enabled') is False
assert v.get('retired_reason')=='semantic_vision_removed'
print(json.dumps(v))
''',timeout=10))
voice=http(8792);hub=http(8812,'127.0.0.1')
model=json.loads((A/'config/board_dialogue_model.json').read_text())['model']
require_current_voice(voice,model,source_fingerprint(A))
assert voice['visual_processing']['semantic_model_enabled'] is False
assert hub['speaker_ready'] and hub['automatic_profile_access'] is False
assert hub['anonymous_binding']['enabled'] and hub['speaker_calibrated'] is False
assert not voice['busy'] and read('public_voice_probe.json')['status']=='PASS'
for port,host,path in ((8812,'127.0.0.1','/v1/observations'),(8792,'192.168.50.1','/v1/voice/visual/frame')):
    c=http.client.HTTPConnection(host,port,timeout=3)
    try:
        c.request('POST',path,b'{}',{'Content-Type':'application/json'})
        response=c.getresponse();value=json.loads(response.read(4096))
        assert response.status==410 and value['image_upload_enabled'] is False
    finally:c.close()
with socket.socket() as probe:
    probe.settimeout(.5);assert probe.connect_ex(('127.0.0.1',8810))!=0
assert read('model_removal.json')['status']=='REMOVED'
assert not Path('D:/AIModels/qwen3-vl-2b-interaction').exists()
storage=json.loads((A/'config/model_storage.local.json').read_text())
old=json.loads((H/'before/aura/config/model_storage.local.json').read_text())
assert {k:v for k,v in old.items() if k!='visual_directory'}==storage
after_owners=owners()
skip={8792,8812,8810}
def preserved(rows):return sorted((r['LocalAddress'],r['LocalPort'],r['OwningProcess']) for r in rows if r['LocalPort'] not in skip)
assert preserved(after_owners['listeners'])==preserved(b['owners']['listeners'])
save('private_after.json',checkpoint('after'))
script=H/'compare_private.py'
cmd='"C:\\Users\\35870\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe" -B "'+str(script)+'"'
launch=r'''$startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
$result=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=COMMAND;CurrentDirectory=ROOT;ProcessStartupInformation=$startup}
if ($result.ReturnValue -ne 0) {throw 'Private comparison launch failed'}
'''.replace('COMMAND',"'"+cmd.replace("'","''")+"'").replace('ROOT',"'"+str(H).replace("'","''")+"'")
powershell(['-Command',launch]);until=time.monotonic()+25
while not (H/'database_verification.json').exists() and time.monotonic()<until:time.sleep(.2)
private=read('database_verification.json');assert private['status']=='PASS',private.get('error')
suite=ET.parse(H/'tests.xml').getroot()
tests=sum(int(s.get('tests',0)) for s in suite.iter('testsuite'))
assert tests==160 and all(int(s.get('failures',0))==0 and int(s.get('errors',0))==0 for s in suite.iter('testsuite'))
changes=read('source_changes.json')
for name,digest in changes['changed'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
assert all(not (P/name).exists() for name in changes['removed_active_modules'])
save('verification.json',dict(status='PASS',voice_revision=voice['service_revision'],source_fingerprint=source_fingerprint(A),
    regression_passed=tests,retired_image_endpoints=410,retired_port_closed=True,model_removed=True,
    model_storage_paths_preserved_except_removed_visual=True,unrelated_listener_owners_preserved=True,
    current_owners=after_owners,board=current_board,observer=observer,camera_process_unchanged=True,
    mechanical_protection_preserved=True,private_database_verification='PASS',microphone_opened=False,
    physical_playback=False,structured_visual_timeline_deployed=False,asr_or_memory_migrated=False))
print(json.dumps({'status':'PASS','revision':voice['service_revision'],'tests':tests,'model_removed':True,'camera_process_unchanged':True,'private_database_verification':'PASS'}))
