"""Promote the real later READY observation, preserving the earlier initializing sample."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
source=HERE/'parallel_platform/gui_startup_review/gui_post_start_ready_01.json'
observation=json.loads(source.read_text(encoding='utf-8'))
assert observation['script_sha256']=='654fa4eaee282d7c85b60d66a89df4ed732e5fe8cc60b7c584c50e6e12575824'
value=observation['board_result']
assert value['status']=='GUI_SOFTWARE_READY_PAUSED_PLATFORM_LOCKED' and len(value['checks'])==16 and all(value['checks'].values())
assert value['owners']['supervisor']['pid']==16314 and value['owners']['gtk']['pid']==16318
assert value['startup_sha256']=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
assert value['selected_source_files_verified']==24 and value['components_verified']==380
canonical=HERE/'gui_start_and_verify.json'
backup=HERE/'gui_start_observation_initializing.json'
assert not backup.exists()
old=json.loads(canonical.read_text(encoding='utf-8'))
assert old['software_ready'] is False and old['board_result']['gui_unit_final']['active_state']=='activating'
shutil.copy2(canonical,backup)
assert backup.read_bytes()==canonical.read_bytes()
receipt={'schema':'aura-5090-gui-root-acceptance-1',
    'host_start_utc':observation['host_observed_start_utc'],
    'host_end_utc':observation['host_observed_end_utc'],
    'accepted_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_sha256':observation['script_sha256'],'observation_source':str(source),
    'observation_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'software_ready':True,'physical_page_visibility':'AWAITING_USER_OBSERVATION',
    'earlier_initializing_observation':str(backup),'board_result':value}
temporary=HERE/'gui_start_and_verify.accepted.part'
with temporary.open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2);stream.write('\n')
temporary.replace(canonical)

transport=HERE.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('root_display_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
display_source=HERE/'read_display_after_gui.py'
data=display_source.read_bytes()
display=json.loads(module.ssh('python3 -B -',data.decode('utf-8'),timeout=25))
with (HERE/'display_state_after_gui.json').open('x',encoding='utf-8') as stream:
    json.dump({'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':hashlib.sha256(data).hexdigest(),'board_result':display},stream,indent=2);stream.write('\n')
print(json.dumps({'software_ready':True,'checks_passed':16,'monitor_power':display['monitor_power'],
    'dpms_enabled':display['dpms_enabled'],'screensaver_timeout_seconds':display['screensaver_timeout_seconds']}))
