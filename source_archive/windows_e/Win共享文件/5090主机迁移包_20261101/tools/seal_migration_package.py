"""Seal completed local exports and refresh only files changed by the handoff pointers."""
import hashlib
import json
from pathlib import Path
import re
import shutil

PACKAGE=Path(__file__).resolve().parents[1]
ROOT=PACKAGE.parent
VERIFY=PACKAGE/'verification'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):
            h.update(block)
    return h.hexdigest()


pins=json.loads((VERIFY/'FINAL_COMPONENT_PINS.json').read_text('utf-8'))
for row in pins:
    base=ROOT if row.get('root')=='workspace' else PACKAGE
    path=base/row['path']
    assert path.resolve().is_relative_to(base.resolve())
    assert digest(path)==row['sha256'], row['path']

# Freeze the earlier root task records without relabelling old runtime readings as fresh.
balance=ROOT/'语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101'
axis_task=balance/'continued_validation_20261101/ROOT_AXIS_PRIORITY.json'
balance_status=balance/'joint_balance_status.json'
updated=[]
for path in (axis_task,balance_status):
    old=path.read_bytes()
    saved=VERIFY/'entry_backups'/path.relative_to(ROOT)
    saved.parent.mkdir(parents=True,exist_ok=True)
    with saved.open('xb') as f: f.write(old)
    value=json.loads(old)
    value['previous_status_at_task_switch']=value['status']
    value['status']='MIGRATION_HANDOFF_FROZEN_DEVICE_CURRENT_STATE_UNCONFIRMED'
    value['migration_package']=str(PACKAGE)
    value['latest_device_handoff']='语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/axis_priority_20261101/HANDOFF_5090.txt'
    value['old_timebox_is_historical']=True
    value['new_device_motion_requested']=False
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    updated.append(str(path.relative_to(ROOT)).replace('\\','/'))

entry_updates=json.loads((VERIFY/'ENTRY_UPDATES.json').read_text('utf-8'))
updated.extend(row['path'].replace('\\','/') for row in entry_updates)
update_set=set(updated)
inventory_path=VERIFY/'WORKSPACE_INVENTORY.json'
inventory=json.loads(inventory_path.read_text('utf-8'))
manifest=VERIFY/'WORKSPACE_FILES.jsonl'
original_sha=digest(manifest)
backup=VERIFY/'WORKSPACE_FILES.before_entry_refresh.jsonl'
shutil.copyfile(manifest,backup)
temporary=VERIFY/'WORKSPACE_FILES.refreshed.jsonl'
refreshed=[]
with manifest.open('r',encoding='utf-8') as source, temporary.open('x',encoding='utf-8') as output:
    for line in source:
        row=json.loads(line)
        relative=row['path'].replace('\\','/')
        if relative in update_set:
            path=ROOT/row['path']
            info=path.stat()
            inventory['counts']['bytes']+=info.st_size-row['bytes']
            if row.get('sha256'):
                inventory['counts']['hashed_bytes']+=info.st_size-row['bytes']
            row.update(bytes=info.st_size,mtime_ns=info.st_mtime_ns,sha256=digest(path))
            refreshed.append(relative)
        output.write(json.dumps(row,ensure_ascii=False)+'\n')
assert set(refreshed)==update_set, sorted(update_set-set(refreshed))
temporary.replace(manifest)
for row in inventory['critical_files']:
    path=ROOT/row['path']
    row.update(bytes=path.stat().st_size,sha256=digest(path))
inventory.update(manifest_sha256=digest(manifest),
    initial_manifest_sha256=original_sha, entries_refreshed_after_handoff_updates=refreshed,
    initial_manifest_preserved=str(backup))
inventory_path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

status=dict(schema='aura-5090-workspace-transfer-status-1',status='LOCAL_TRANSFER_PACKAGE_SEALED_NEW_HOST_SETUP_PENDING',
    workspace_payload_root=str(ROOT),package_root=str(PACKAGE),
    whole_workspace_must_be_copied=True,workspace_file_count=inventory['counts']['files'],
    workspace_payload_bytes=inventory['counts']['bytes'],workspace_scan_errors=inventory['errors'],
    directory_junctions_followed=False,external_dependency_files=111,external_dependency_bytes=2400191989,
    codex_configuration_exported=True,project_history_exported=True,
    general_llm_weights_copied=False,auth_tokens_or_ssh_private_keys_copied=False,
    original_sources_deleted=False,new_host_gpu_runtime_tested=False,new_host_ssh_connected=False,
    board_current_status_confirmed=False,component_pins=pins,
    next_action='Open the complete Win共享文件 on the new host; read 00_先读.md and send 01_给新主机Codex的提示词.txt.')
(PACKAGE/'MIGRATION_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

files=[]
excluded={'PACKAGE_MANIFEST.json','verification/VERIFY_RESULT.json'}
for path in sorted(PACKAGE.rglob('*')):
    if not path.is_file():continue
    relative=path.relative_to(PACKAGE).as_posix()
    if relative in excluded:continue
    assert not path.is_symlink()
    files.append(dict(path=relative,bytes=path.stat().st_size,sha256=digest(path)))
critical={row['path']:row for row in inventory['critical_files']}
for relative in ('README.md','后续任务_先读这里.md','语音共享文件/README.md'):
    path=ROOT/relative
    critical[relative]=dict(path=relative,bytes=path.stat().st_size,sha256=digest(path))
bundle=dict(schema='aura-5090-sealed-transfer-manifest-1',status='SEALED',
    files=files,file_count=len(files),bytes=sum(row['bytes'] for row in files),
    workspace_critical_files=list(critical.values()),
    all_package_files_have_sha256=True,whole_workspace_is_required=True,
    new_host_operation_has_not_been_tested=True)
(PACKAGE/'PACKAGE_MANIFEST.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=bundle['status'],package_files=len(files),package_bytes=bundle['bytes'],
    workspace_files=inventory['counts']['files'],manifest_sha256=digest(PACKAGE/'PACKAGE_MANIFEST.json'))))
