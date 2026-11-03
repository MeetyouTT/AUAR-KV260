"""Record the user's direct panel observation separately from software evidence."""
import datetime
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
receipt=HERE/'physical_page_observation.json'
assert not receipt.exists()
observation={'schema':'aura-page-user-observation-1',
    'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'question':'板卡连接的显示屏现在能看到角色主页面了吗？',
    'user_answer':'已看到角色主页面','status':'USER_CONFIRMED_ROLE_MAIN_PAGE',
    'scope':'physical role main page visibility only; no speech or axis acceptance inferred'}
receipt.write_text(json.dumps(observation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=HERE/'gui_start_and_verify.json'
value=json.loads(path.read_text(encoding='utf-8'));assert value['software_ready'] is True
backup=HERE/'gui_start_and_verify.before_user_confirmation.json';assert not backup.exists()
shutil.copy2(path,backup)
value.update(physical_page_visibility=observation['status'],physical_page_observation=str(receipt))
path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
context_path=HERE/'CONNECTION_CONTEXT.json'
context=json.loads(context_path.read_text(encoding='utf-8'))
backup_context=HERE/'before/connection_context_before_page_confirmation.json';assert not backup_context.exists()
shutil.copy2(context_path,backup_context)
context.update(board_model_link_verified=True,gui_software_ready=True,physical_role_main_page_user_confirmed=True,
    gui_supervisor=value['board_result']['owners']['supervisor'],gui_gtk=value['board_result']['owners']['gtk'],
    current_boot_motion_explicitly_authorized=False,updated_utc=observation['recorded_utc'])
context_path.write_text(json.dumps(context,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'recorded':str(receipt),'physical_page_visibility':observation['status']}))
