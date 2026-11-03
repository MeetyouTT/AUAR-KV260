from common import *
def main():
    h=load(HERE/'DEVICE_HANDOFF_R4.json');f=load(HERE/'validation/FINAL_DEVICE_READY_R4.json')
    live=load(HERE/'validation/LIVE_AFTER_R4.json');m=load(HERE/'release/MANIFEST.json')
    assert f['status']=='FRESH_READY_NO_ANIMATION_HELPERS_OR_PENDING_COMMANDS' and f['motion_control_live']
    assert f['startup_sha256']==m['startup_after'] and f['all_380_pins_match']
    assert f['component_sha256']==load(HERE/'release/startup.after.json')['component_sha256']
    assert live['gui_owner']==f['gui_owner'] and live['camera_owner']==f['camera_owner']
    assert not f['animation_helpers_remaining'] and not f['temporary_animation_guards']
    receipt=dict(schema='aura-dialogue-state-animation-R4-device-return-1',
      status='R4_LOADED_VERIFIED_DEVICE_MAINTENANCE_RETURNED',handoff_id=h['handoff_id'],
      returned_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      returning_thread_id='01a19efd-bb40-7f32-a6e4-a5f0cb59ffe8',receiving_thread_id=h['releasing_thread_id'],
      handoff_file=str(HERE/'DEVICE_HANDOFF_R4.json'),handoff_sha256=sha(HERE/'DEVICE_HANDOFF_R4.json'),
      permission_active_for_animation=False,maintenance_holder_after_return=h['releasing_thread_id'],
      root_pending_SSH=0,root_pending_HTTP=0,root_active_observers=0,root_pending_control_transactions=0,
      root_unsettled_device_operations=0,root_animation_helper_processes=0,
      final_fresh_receipt='validation/FINAL_DEVICE_READY_R4.json',final_fresh_receipt_sha256=sha(HERE/'validation/FINAL_DEVICE_READY_R4.json'),
      actual_state=f,loaded_into_original_GUI=True,loaded_GUI_swap_fps=live['native_swap_fps'],
      actual_listening_and_GUI_properties_restored=True,normal_GUI_stop_count=1,normal_GUI_start_count=1,
      camera_restarts=0,axis_commands=0,model_service_requests_or_restarts=0,DFX_boot_changes=0,private_store_operations=0,
      changed_runtime_files=list(m['components']),other_runtime_components_preserved=375,
      parallel_voice_overlap_files_changed=[],R2_R3_artifacts_and_engineering_baseline_preserved=True,
      human_screen_acceptance=False,live_human_dialogue_test_performed=False,
      remaining_work='Local archive finalization only; future voice maintenance rebases on this exact R4 source map',
      full_source_map='release/startup.after.json')
    p=HERE/'DEVICE_RETURN_R4.json';assert not p.exists();save(p,receipt)
    print(json.dumps(dict(status=receipt['status'],return_sha256=sha(p),startup=f['startup_sha256'],pending_device_operations=0)))
if __name__=='__main__':main()
