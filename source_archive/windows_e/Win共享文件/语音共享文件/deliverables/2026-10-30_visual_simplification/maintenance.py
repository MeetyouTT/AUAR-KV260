"""Guarded Qwen-VL retirement. Never reads names, templates, images or PCM."""
import datetime, hashlib, json, shutil, socket, subprocess, sys, time, urllib.request
from pathlib import Path

H = Path(__file__).resolve().parent
P = H.parents[1]
A = P / 'aura'
sys.path[:0] = [str(A), str(H.parent / '2026-10-29_audio_animation_polish'),
               str(H.parent / '2026-10-29_service_recovery')]
from board_guard import capture, same
from recovery_common import checkpoint, powershell

FILES = ['aura/tools/device_hub.py', 'aura/tools/voice_channel_source.py',
         'aura/tools/board_model_host.py', 'aura/tools/memory_timeline_host.py',
         'aura/common/voice_service_capabilities.py', 'aura/config/model_storage.local.json',
         'aura/tools/visual_question_host.py', 'aura/tools/visual_voice_host.py',
         'deliverables/2026-10-28_device_skills/start_devices.py']

def save(name, value):
    (H / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def read(name):
    return json.loads((H / name).read_text(encoding='utf-8-sig'))

def http(port, host='192.168.50.1', path='/health'):
    with urllib.request.urlopen(f'http://{host}:{port}{path}', timeout=5) as response:
        return json.load(response)

def owners():
    return json.loads(powershell(['-Command', r'''[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$ports=@(8791,8792,8795,8796,8810,8812,11434,11435)
$listeners=@(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in $ports} | Select-Object LocalAddress,LocalPort,OwningProcess)
$ids=@($listeners.OwningProcess | Sort-Object -Unique)
$processes=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in $ids} | ForEach-Object {
 [pscustomobject]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;creation_utc=$_.CreationDate.ToUniversalTime().ToString('o');exe=$_.ExecutablePath;command_line=$_.CommandLine}
})
[pscustomobject]@{listeners=$listeners;processes=$processes} | ConvertTo-Json -Depth 5 -Compress''']))

def baseline():
    assert not (H / 'baseline.json').exists(), 'Do not overwrite the baseline'
    board = capture(); assert board['safe'] and not board['mismatches']
    time.sleep(.7); same(board, capture())
    voice = http(8792); hub = http(8812, '127.0.0.1')
    assert voice['ready'] and not voice['busy'] and hub['speaker_ready']
    copies = {}
    for name in FILES:
        source = P / name; target = H / 'before' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copies[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    value = dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 board=board, owners=owners(), voice=voice, hub=hub,
                 sources=copies, private_checkpoint=checkpoint('before'))
    save('baseline.json', value)
    print(json.dumps({'status':'BASELINE_SAVED','board_safe':True,'voice_ready':True,
                      'memory_counts':value['private_checkpoint']['databases']['conversation']['counts']}))

def wait_ready():
    from common.voice_service_capabilities import require_current_voice,source_fingerprint
    deployment=read('services_deployment.json')
    deadline=datetime.datetime.fromisoformat(deployment['startup_deadline_utc'].replace('Z','+00:00')).timestamp()
    model=json.loads((A/'config/board_dialogue_model.json').read_text())['model']
    fingerprint=source_fingerprint(A);last=''
    while time.time()<deadline:
        try:
            voice=http(8792);hub=http(8812,'127.0.0.1')
            require_current_voice(voice,model,fingerprint)
            assert not voice['busy'] and hub['speaker_ready']
            assert voice['visual_processing']['semantic_model_enabled'] is False
            assert hub['visual_processing']['image_upload_enabled'] is False
            assert hub['automatic_profile_access'] is False
            with socket.socket() as probe:
                probe.settimeout(.3);assert probe.connect_ex(('127.0.0.1',8810))!=0
            current=owners();old=read('baseline.json')['owners']
            changed={8792,8812,8810}
            def stable_ports(rows):
                return sorted((r['LocalAddress'],r['LocalPort'],r['OwningProcess']) for r in rows if r['LocalPort'] not in changed)
            assert stable_ports(current['listeners'])==stable_ports(old['listeners']),'Unrelated listener changed'
            value=dict(status='READY',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       voice=voice,hub=hub,owners=current,retired_port_closed=True,
                       unrelated_listener_owners_preserved=True,source_fingerprint=fingerprint)
            save('services_ready.json',value)
            print(json.dumps({'status':'READY','revision':voice['service_revision'],'visual':voice['visual_processing']}))
            return
        except Exception as exc:
            last=type(exc).__name__+': '+str(exc)
            save('readiness_progress.json',{'status':'WAITING','last_error':last})
            time.sleep(1)
    save('services_ready.json',{'status':'FAILED','error':last})
    raise RuntimeError('Original 300-second readiness budget expired: '+last)

if __name__ == '__main__':
    if sys.argv[1:] == ['baseline']: baseline()
    elif sys.argv[1:] == ['guard']:
        same(read('baseline.json')['board'],capture())
        print('BOARD_IDLE_AND_UNCHANGED')
    elif sys.argv[1:] == ['wait-ready']:wait_ready()
    else: raise SystemExit('Use an explicit supported phase')
