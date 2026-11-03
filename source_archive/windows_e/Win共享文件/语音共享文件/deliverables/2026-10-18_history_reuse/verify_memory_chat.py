"""Observe two fresh, actually played UI turns; never synthesize playback ACKs."""
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
    existing_path = HERE / 'live_turns.json'
    existing = json.loads(existing_path.read_text(encoding='utf-8')) if existing_path.is_file() else []
    config = {'seconds': args.seconds, 'existing': existing,
              'previous_request': baseline['transcription'].get('request_id'),
              'camera_pid': baseline['camera']['pid'], 'board_boot_id': baseline['camera']['board_boot_id']}
    script = 'config=' + repr(config) + '\n' + r'''
import json,time,urllib.request
def get(port,path,host='127.0.0.1'):
    with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=3) as r:return json.load(r)
health=get(8792,'/health','192.168.50.1')
assert health['ready'] and health['latency_options']['reuse_history']
turns=config['existing'];seen={t['playback_ack']['request_id'] for t in turns}
deadline=time.monotonic()+config['seconds']
while len(turns)<2 and time.monotonic()<deadline:
    state=get(8783,'/api/state');tr=state['local_transcription'];request=tr.get('request_id')
    raw=tr.get('text') or ''
    target='绿' in raw if not turns else ('喜欢' in raw and '颜色' in raw)
    if target and request and request!=config['previous_request'] and request not in seen:
        assert not state.get('error') and not tr.get('error'),(state.get('error'),tr.get('error'))
        ack=tr['service'].get('last_playback_ack') or {}
        if tr['state']=='ANSWERED' and ack.get('committed') and ack.get('request_id')==request:
            turn=state['turns'][-1];capture=state['local_recording']['result']
            assert capture['capture_id']==tr['capture_id'] and turn['audio_complete']
            assert turn['thinking_mode']=='chat' and not turn['thinking_feedback']
            assert turn['server_metrics']['clauses']==1
            camera=get(8790,'/health')
            assert camera['pid']==config['camera_pid'] and camera['board_boot_id']==config['board_boot_id']
            turns.append({'transcript':raw,'capture':capture,'turn':turn,'playback_ack':ack,
                          'camera_pid':camera['pid'],'board_boot_id':camera['board_boot_id'],
                          'camera_preserved':True,'acoustic_onset_measured':False})
            seen.add(request)
    time.sleep(.15)
status='WAITING_FOR_TWO_FRESH_MEMORY_TURNS'
if len(turns)>=2:
    assert turns[-1]['turn']['server_metrics']['timing']['history_format']=='exact_json'
    assert turns[-1]['turn']['server_metrics']['timing']['history_messages']>=2
    assert '绿' in turns[-1]['turn']['text'],turns[-1]['turn']['text']
    status='PASS_TWO_FRESH_MEMORY_TURNS_EXACT_HISTORY'
print(json.dumps({'status':status,'host_health':health,'turns':turns,'user_listening_accepted':None}))
'''
    report = json.loads(ssh('python3 -', script, timeout=args.seconds + 8))
    existing_path.write_text(json.dumps(report['turns'], ensure_ascii=False, indent=2), encoding='utf-8')
    name = 'live_memory.json' if report['status'].startswith('PASS_') else 'live_pending.json'
    (HERE / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
