# USE_SESSION_COMMON
"""Read the original public control configuration and current GUI state, without motion."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='FIRST_FACE_TEST_STOPPED'
config=BUSINESS/'runtime/aura/config'
manual=document(config/'pan_manual.local.json')
face=document(config/'pan_face.local.json')
zone=Path(face['arguments']['zone-settings'])
release=Path(manual['release_manifest'])
g=get_json(8783,'/api/state')
print(json.dumps(dict(status='ORIGINAL_ENTRY_INSPECTED_NO_MOTION',manual=manual,face=face,
    zone=dict(path=str(zone),sha256=digest(zone),value=document(zone)),manual_release=document(release),
    gui_manual_pan=g.get('manual_pan'),current_stopped_readback=j['current_stopped_readback'],
    camera_owner_current=dict(pid=j['restored_camera_pid'],birth=j['restored_camera_birth']),
    original_controller_manifest_sha256=digest(Path(face['release_root'])/'deployment-manifest.json'))))
