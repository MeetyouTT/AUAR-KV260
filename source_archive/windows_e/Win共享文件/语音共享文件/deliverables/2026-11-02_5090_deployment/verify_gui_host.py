"""Collect reviewed, filtered startup evidence after the one normal start request."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
assert (HERE/'gui_start_request.json').is_file()
assert not (HERE/'gui_start_and_verify.json').exists()
transport=HERE.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('root_verify_gui_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def collect(source,output,timeout=45):
    before=datetime.datetime.now(datetime.timezone.utc).isoformat()
    data=source.read_bytes()
    value=json.loads(module.ssh('python3 -B -',data.decode('utf-8'),timeout=timeout))
    receipt={'host_start_utc':before,'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':hashlib.sha256(data).hexdigest(),'board_result':value}
    with output.open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,ensure_ascii=False,indent=2);stream.write('\n')
    return receipt

collect(HERE/'wait_for_gui_ready.py',HERE/'gui_ready_wait.json',timeout=50)
source=HERE/'parallel_platform/gui_startup_review/collect_gui_post_start_metadata.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='654fa4eaee282d7c85b60d66a89df4ed732e5fe8cc60b7c584c50e6e12575824'
data=source.read_bytes()
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
metadata=json.loads(module.ssh('python3 -B -',data.decode('utf-8'),timeout=45))
ready=(metadata['status']=='GUI_SOFTWARE_READY_PAUSED_PLATFORM_LOCKED' and all(metadata['checks'].values()))
receipt={'schema':'aura-5090-gui-root-acceptance-1','host_start_utc':started,
    'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_sha256':hashlib.sha256(data).hexdigest(),'software_ready':ready,
    'physical_page_visibility':'AWAITING_USER_OBSERVATION','board_result':metadata}
with (HERE/'gui_start_and_verify.json').open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2);stream.write('\n')
if ready:
    collect(HERE/'read_display_after_gui.py',HERE/'display_state_after_gui.json')
print(json.dumps({'output':str(HERE/'gui_start_and_verify.json'),'software_ready':ready,
    'checks':metadata['checks'],'owners':metadata['owners']}))
