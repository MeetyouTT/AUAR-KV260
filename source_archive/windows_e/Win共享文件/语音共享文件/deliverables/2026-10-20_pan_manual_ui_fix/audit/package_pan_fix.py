"""Freeze the process-isolation correction and stage without live mutations."""
import base64,gzip,hashlib,json
from pathlib import Path
J=Path(__file__).parent;A=Path('/home/ghmd/Win共享文件/语音共享文件/aura');D=A.parent/'deliverables/2026-10-20_pan_manual_ui_fix';D.mkdir(exist_ok=True)
prior=json.loads((D.parent/'2026-10-20_pan_manual_ui/deployment-plan.json').read_text())
src=Path(json.loads((J/'latest-axis-manual-ui-startup.json').read_text())['evidence'])
c=json.loads((src/'current-startup-config.json').read_text());c['gui_sha256']=prior['new_files']['tools/board_avatar_pan.py'];c['component_sha256'].update(prior['new_files']);c['display_retrain_off_seconds']=2
oldconfig=(json.dumps(c,indent=2)+'\n').encode();sha=lambda b:hashlib.sha256(b).hexdigest()
files={}
names=['board/motion/manual.py','board/motion/manual_vsrv.py','board/motion/manual_process.py','tools/board_avatar_pan.py','tools/pan_controls.py','tests/framework/test_manual_pan.py','tests/framework/test_manual_pan_process.py']
for rel in names:
 raw=(A/rel).read_bytes();compile(raw,rel,'exec');files[rel]={'base64':base64.b64encode(raw).decode(),'sha256':sha(raw)}
 p=D/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
for rel in ['tools/package_board_avatar.py','docs/BOARD_PAN_MANUAL.md']:
 p=D/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((A/rel).read_bytes())
payload={'baseline':{'boot_id':prior['baseline']['boot_id'],'aura_root':prior['baseline']['aura_root'],'startup':'/home/root/aura-pan-manual-ui-20261020/staged-v1/startup','startup_config_sha256':sha(oldconfig)},'old_files':prior['new_files'],'files':files}
raw=json.dumps(payload,ensure_ascii=False,indent=2).encode();deploy=(J/'board_pan_fix_deploy.py').read_bytes();remote='/home/root/aura-pan-manual-ui-20261020/fix-v2'
stage='''"""Stage fix files only; no service changes or MMIO."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r
p=Path(%r);p.mkdir(parents=True,exist_ok=False)
for name,packed,expected in %r:
 raw=gzip.decompress(base64.b64decode(packed));assert hashlib.sha256(raw).hexdigest()==expected
 with (p/name).open('xb') as out:out.write(raw)
print(json.dumps({'status':'STAGED_FIX_NO_ACTUATION','path':str(p)}),flush=True)
'''%(payload['baseline']['boot_id'],remote,[(n,base64.b64encode(gzip.compress(v,mtime=0)).decode(),sha(v)) for n,v in [('payload.json',raw),('deploy.py',deploy)]])
(J/'board_pan_fix_stage.py').write_text(stage)
launch=(J/'board_pan_ui_activate.py').read_text().replace('/staged-v1','/fix-v2').replace('1f604698af21788bf4ecc17d1f12bdad45a6f78ade0a7d7afd1dbf5e6e13cb3e',sha(deploy))
(J/'board_pan_fix_activate.py').write_text(launch)
plan={'baseline':payload['baseline'],'files':{r:v['sha256'] for r,v in files.items()},'lease_ms':100,'gui_core_preserved':True,'automatic_replay':False,'initial_reported_fault':'ACK mismatch after3 accepted commands;241ms;output off;last1450'}
(D/'deployment-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'staged_source_files':len(files),'remote':remote,'config_expected_sha256':sha(oldconfig),'deployment_sha256':sha(deploy)}))
