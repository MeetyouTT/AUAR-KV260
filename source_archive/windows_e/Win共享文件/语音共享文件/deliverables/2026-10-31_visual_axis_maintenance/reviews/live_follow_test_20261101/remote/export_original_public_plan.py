# USE_SESSION_COMMON
import base64
current_guard();wide_active()
j=state();assert j['phase']=='ORIGINAL_CONFIG_AND_CAMERA_BINDING_PREPARED'
paths={name:Path(j['original_configuration_root'])/name for name in ('pan_manual.local.json','pan_face.local.json','pan_direction.current.json')}
paths['production_source_manifest.json']=BUSINESS/'production_source_manifest.json'
assert digest(paths['production_source_manifest.json'])=='6d9b0ee5c311288e07335841c3c9e42278e8564f8be860f68412f7c2c537d8a2'
print(json.dumps(dict(files={name:dict(sha256=digest(path),data=base64.b64encode(read_regular(path)).decode()) for name,path in paths.items()},
    face_readback=j['camera_readback'],camera_binding_proof_sha256=j['camera_binding_proof_sha256'],
    camera_owner=dict(board_boot_id=BOOT,camera_pid=j['restored_camera_pid'],camera_start_ticks=str(j['restored_camera_birth']),
        camera_cmdline_sha256=j['restored_camera_command_sha256']),database_exported=False)))
