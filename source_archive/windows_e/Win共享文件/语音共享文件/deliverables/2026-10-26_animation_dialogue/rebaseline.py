"""Re-check a changed board boot without modifying hardware identity or pins."""
import hashlib, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
expected=json.loads((HERE.parent/'2026-10-26_profile_memory/board_candidate.json').read_text(encoding='utf-8'))['base']['sha256']
expected['tools/motion_queue.py']=json.loads((HERE/'runtime_before.json').read_text(encoding='utf-8'))['sha256']['tools/motion_queue.py']
script=r'''
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;expected=EXPECTED;stage=Path(c['stage']);source=Path(c['source_runtime'])
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
def semantic(value):
    return re.search(r'argv\[\]=(.*?);',value).group(1).strip(), next(line for line in value.splitlines() if line.startswith('DropInPaths='))
assert semantic(effective)==semantic(c['baseline_effective'])
for rel,digest in expected.items():assert hashlib.sha256((source/'aura'/rel).read_text().encode()).hexdigest()==digest,rel
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as f:state=json.load(f)
assert state['phase']=='IDLE' and state['audio_output_state']=='IDLE_READY' and not state.get('error')
assert state['handsfree_dialogue']['enabled'] is False and not state['handsfree_dialogue'].get('microphone_open')
assert state.get('manual_pan',{}).get('state') not in ('MOVING','STOPPING')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
value={'previous_boot':c['boot'],'current_boot':boot,'boot_changed':c['boot']!=boot,
       'runtime_entry_unchanged':True,'patched_base_source_unchanged':True,
       'hardware_config_modified':False,'phase':state['phase'],'audio_output_state':state['audio_output_state'],
       'manual_pan':{k:state.get('manual_pan',{}).get(k) for k in ('state','error','mechanical_reference_calibrated','automatic_following')},
       'visual_bound':state['handsfree_dialogue'].get('visual_bound'),
       'ui_pid':int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)),
       'baseline_effective':effective}
(stage/'rebaseline.json').write_text(json.dumps(value,indent=2))
print(json.dumps(value))
'''.replace('CANDIDATE',repr(c)).replace('EXPECTED',repr(expected))
value=json.loads(ssh('python3 -B -',script,timeout=20))
original=HERE/'candidate.initial.json'
if not original.exists():original.write_bytes((HERE/'candidate.json').read_bytes())
c.update(boot=value['current_boot'],baseline_effective=value['baseline_effective'],baseline_ui_pid=value['ui_pid'])
(HERE/'candidate.json').write_text(json.dumps(c,indent=2),encoding='utf-8')
(HERE/'rebaseline.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='baseline_effective'}))
