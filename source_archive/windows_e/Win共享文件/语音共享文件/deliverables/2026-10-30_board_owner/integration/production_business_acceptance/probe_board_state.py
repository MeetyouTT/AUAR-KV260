"""Bounded read-only board probe; returns operating metadata, never identities/text."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import hashlib,http.client,json,pathlib,subprocess
root=pathlib.Path(ROOT)
raw=(root/'startup/config.json').read_bytes();cfg=json.loads(raw)
unit=subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecStart','-p','DropInPaths','-p','Restart','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True)
u=dict(line.split('=',1) for line in unit.splitlines() if '=' in line)
conn=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
try:
 conn.request('GET','/api/state');res=conn.getresponse();body=res.read(1048577)
 assert res.status==200 and len(body)<=1048576
 v=json.loads(body)
finally:conn.close()
def selected(obj,names):return {k:obj[k] for k in names if k in obj}
hands=v.get('handsfree_dialogue',{});pan=v.get('manual_pan',{})
display=v.get('avatar_display',{});business=v.get('board_business',{})
out=dict(boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),startup_sha256=hashlib.sha256(raw).hexdigest(),component_pins=len(cfg['component_sha256']),runtime=cfg['runtime'],unit=u,
 phase=v.get('phase'),playing=v.get('playing'),handsfree=selected(hands,('enabled','microphone_open','state','capture_mode','busy')),
 pan=selected(pan,('state','pulse_us','automatic_following')),
 display=selected(display,('kind','frames','visible','target_fps','fps','state')),
 character=selected(v.get('character_pair',{}),('state','profile_version','production_selected','prompt_sha256')),
 business=selected(business,('mode','production_cutover','started','closed','close_complete','speaker_analysis_error')),
 state_sections=list(v))
print(json.dumps(out,ensure_ascii=True))
'''

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root', default='/home/root/aura-character-xuefei-20261030/f94fca2c94288acb')
    p.add_argument('--output',default='latest_board_state.json')
    args=p.parse_args()
    assert args.root.startswith('/home/root/aura-') and '..' not in Path(args.root).parts
    value=json.loads(ssh('python3 -B -','ROOT='+repr(args.root)+'\n'+REMOTE,timeout=15))
    out=HERE/args.output
    out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value,ensure_ascii=True))

if __name__=='__main__':main()
