"""Read-only verification of a fresh UI chat after compact internal reply fields.

Requires board_preflight.json from this boot. Never accepts an earlier
turn or interprets service readiness as listening acceptance.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=45)
    args = parser.parse_args()
    assert 1 <= args.seconds <= 50
    baseline = json.loads((HERE / 'board_preflight.json').read_text(encoding='utf-8'))
    config = {'seconds': args.seconds,
              'previous_request': baseline['transcription'].get('request_id'),
              'camera_pid': baseline['camera']['pid'],
              'board_boot_id': baseline['camera']['board_boot_id']}
    script = 'config = ' + repr(config) + '\n' + r'''
import json,time,urllib.request
def get(port,path,host='127.0.0.1'):
    with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=3) as response:
        return json.load(response)
health=get(8792,'/health','192.168.50.1')
assert health['ready'] and health['latency_options']['coalesce_chat']
deadline=time.monotonic()+config['seconds']
report={'status':'WAITING_FOR_NEW_COMPLETED_CHAT','health':health}
while time.monotonic()<deadline:
    state=get(8783,'/api/state')
    tr=state['local_transcription'];request=tr.get('request_id')
    if request and request!=config['previous_request']:
        assert not state.get('error') and not tr.get('error'),(state.get('error'),tr.get('error'))
        ack=tr['service'].get('last_playback_ack') or {}
        if tr['state']=='ANSWERED' and ack.get('committed') and ack.get('request_id')==request:
            turn=state['turns'][-1];capture=state['local_recording']['result']
            assert capture['capture_id']==tr['capture_id']
            assert turn['thinking_mode']=='chat'
            assert turn['thinking_feedback'] is False,'Unexpected cached waiting cue'
            assert turn['audio_complete'] and turn['server_metrics']['clauses']==1
            camera=get(8790,'/health')
            assert camera['pid']==config['camera_pid'] and camera['board_boot_id']==config['board_boot_id']
            report={'status':'PASS_FRESH_CHAT_NO_WAITING_CUE_CONTINUOUS_PLAYBACK',
                    'health':health,'transcript':tr['text'],'capture':capture,
                    'turn':turn,'playback_ack':ack,'camera_preserved':True,
                    'camera_pid':camera['pid'],'board_boot_id':camera['board_boot_id'],
                    'acoustic_onset_measured':False,'user_listening_accepted':None}
            break
    time.sleep(.2)
print(json.dumps(report))
'''
    report = json.loads(ssh('python3 -', script, timeout=args.seconds + 8))
    name = 'live_playback.json' if report['status'].startswith('PASS_') else 'live_pending.json'
    (HERE / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
