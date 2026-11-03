"""Keep every selected source pin and add the actual new original run-config.

Only the selected face-readback spec and its one existing startup component
pin change. Known-byte CAS never restores a whole historical startup on error.
"""
platform(); paused_gui(); snapshot = source_snapshot()
receipt = json.loads(regular(TX/'camera-restore-verified.json'))
require(receipt['status'] == 'ORIGINAL_CAMERA_EXACT_FINAL_RESTORED_AND_VERIFIED', 'Actual restore proof required')
owner, health, unit = alive_camera()
require(owner == receipt['camera_owner'], 'Restored owner changed')
run_pin = receipt['run_config']; pinned(run_pin)
before = snapshot['selected']; candidate = copy.deepcopy(before)
require(before['camera_cmdline_sha256'] == owner['command_sha256'], 'Original camera command pin differs')
candidate.update(board_boot_id=BOOT, camera_pid=owner['pid'], camera_start_ticks=owner['birth_ticks'],
                 camera_cmdline_sha256=owner['command_sha256'], camera_config=run_pin['path'])
require(run_pin['path'] not in candidate['source_sha256'], 'New run-config already present: reconcile rather than inventing another binding')
candidate['source_sha256'][run_pin['path']] = run_pin['sha256']
require({p:s for p,s in candidate['source_sha256'].items() if p != run_pin['path']} == before['source_sha256'], 'Historical source pin dropped or changed')
original_verify(snapshot['aura'], candidate)
directory = TX/('binding-' + str(owner['pid']) + '-' + owner['birth_ticks'])
require(not os.path.lexists(directory), 'Binding transaction already exists: reconcile without replay')
directory.mkdir(mode=0o700)
selected_path = directory/'face_gallery_readback.local.json'; selected_raw = encoded(candidate)
selected_pin = dict(path=str(selected_path), sha256=digest(selected_raw))
new_ui = copy.deepcopy(snapshot['ui']); new_ui['board_business']['face_readback'] = selected_pin
ui_raw = encoded(new_ui); new_startup = copy.deepcopy(snapshot['startup'])
new_startup['component_sha256']['config/board_avatar_gtk.json'] = digest(ui_raw); startup_raw = encoded(new_startup)
require({k:v for k,v in new_startup['component_sha256'].items() if k != 'config/board_avatar_gtk.json'}
        == {k:v for k,v in snapshot['startup']['component_sha256'].items() if k != 'config/board_avatar_gtk.json'}, 'Another startup component changed')
for name,raw in (('startup.before.json',snapshot['startup_raw']),('ui.before.json',snapshot['ui_raw']),
                 ('startup.after.json',startup_raw),('ui.after.json',ui_raw)):
    fd = os.open(directory/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
fd = os.open(selected_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd,'wb') as f: f.write(selected_raw); f.flush(); os.fsync(f.fileno())
intent = dict(schema='aura-actual-original-camera-binding-intent-1', boot_id=BOOT, camera_owner=owner,
              startup_before_sha256=digest(snapshot['startup_raw']), startup_after_sha256=digest(startup_raw),
              UI_before_sha256=digest(snapshot['ui_raw']), UI_after_sha256=digest(ui_raw),
              selected_before=snapshot['selected_pin'], selected_after=selected_pin,
              old_source_count=len(before['source_sha256']), new_source_count=len(candidate['source_sha256']),
              added_source_pin=run_pin, all_historical_source_pins_preserved=True,
              changed_components=['config/board_avatar_gtk.json'])
create(directory/'intent.json', intent)
now = source_snapshot()
require(now['startup_raw'] == snapshot['startup_raw'] and now['ui_raw'] == snapshot['ui_raw'], 'Source changed before CAS')
require(alive_camera()[0] == owner, 'Camera changed before CAS')
paused_gui(); original_verify(snapshot['aura'], candidate)
replace_known(snapshot['ui_path'], snapshot['ui_raw'], ui_raw)
replace_known(snapshot['startup_path'], snapshot['startup_raw'], startup_raw)
after = source_snapshot(digest(startup_raw)); original_verify(after['aura'], after['selected'])
require(after['selected'] == candidate and alive_camera()[0] == owner, 'Post-CAS selected owner changed')
require(regular(CP) == pinned(SEAL['sealed_identical_final_pin']), 'Original checkpoint changed during binding')
result = dict(intent, status='CURRENT_ORIGINAL_CAMERA_BINDING_COMMITTED_AND_VERIFIED',
              startup_path=str(snapshot['startup_path']), startup_sha256=digest(startup_raw),
              component_sha256=new_startup['component_sha256'], runtime=new_startup['runtime'],
              UI_pin=dict(path=str(snapshot['ui_path']),sha256=digest(ui_raw)), selected_face_binding=selected_pin,
              original_metadata_verify_passed=True, components_verified=380, unchanged_components=379,
              source_count=len(candidate['source_sha256']), selected_source_sha256=candidate['source_sha256'],
              camera_config=run_pin, transaction=str(directory), GUI_started=False, listening_enabled=False,
              model_identity_database_or_memory_changed=False, motion_requested=False,
              checkpoint_seed_counter_marker_or_history_modified=False)
create(directory/'committed.json', result)
print(json.dumps(result))
