from pathlib import Path
HERE=Path(__file__).resolve().parent
path=HERE/'prepare.py';raw=path.read_text(encoding='utf-8')
raw=raw.replace("names=['aura/board/identity/spoken_query.py'", "names=['aura/board/identity/photo_archive.py','aura/tests/framework/test_enrollment_photos.py','aura/board/identity/spoken_query.py'")
raw=raw.replace("identity['feature_backend']={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}",
 "identity['feature_backend']={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}\nidentity['enrollment_photos']={'enabled':True,'directory':'~/.local/share/aura/enrollment_photos','max_images_per_session':192}")
raw=raw.replace("modules=['test_simple_enrollment'", "modules=['test_enrollment_photos','test_simple_enrollment'")
path.write_text(raw,encoding='utf-8')
path=HERE/'preflight.py';raw=path.read_text(encoding='utf-8')
raw=raw.replace('from board.identity.live import IdentityService',
 'from board.identity.live import IdentityService\nfrom board.identity.photo_archive import EnrollmentPhotoArchive')
raw=raw.replace(" config['database']=str(Path(directory)/'public.sqlite');path=Path(directory)/'identity.json';path.write_text(json.dumps(config))",
 " config['database']=str(Path(directory)/'public.sqlite')\n config['enrollment_photos']={'enabled':True,'directory':str(Path(directory)/'photos'),'max_images_per_session':192}\n path=Path(directory)/'identity.json';path.write_text(json.dumps(config))")
raw=raw.replace(" cfg=config_for(root,path);extractor=CameraFaceExtractor(cfg,face_targets=True)",
 " cfg=config_for(root,path);extractor=CameraFaceExtractor(cfg,face_targets=True);photos=EnrollmentPhotoArchive(cfg['enrollment_photos'])")
raw=raw.replace("multi_frame=True,backend='WINDOWS_CPU_SFACE_ORT')", "multi_frame=True,backend='WINDOWS_CPU_SFACE_ORT',photo_archive=photos)")
raw=raw.replace("  assert flow.public()['stage']=='idle'", "  assert flow.public()['stage']=='idle'\n  archive=json.loads((photos.root/photos.health()['latest_session']/'manifest.json').read_text())\n  assert archive['outcome']=='committed' and archive['database_revision_after']==1\n  assert len(archive['images'])==27 and len(archive['validation_frame_ids'])==5\n  assert archive['selected']['frame_id'] not in archive['validation_frame_ids']\n  assert not photos.health()['error']\n  for row in archive['images']:\n   assert cv2.imread(str(photos.root/archive['session_id']/row['filename'])).shape==(112,112,3)")
raw=raw.replace("'user_database_opened':False,'camera_opened':False,'photos_saved':False", "'user_database_opened':False,'camera_opened':False,'user_photos_saved':False,'public_test_photos_temporary':27,'all_saved_sizes':[112,112],'selected_and_five_later_validation_photos_labeled':True")
path.write_text(raw,encoding='utf-8')
path=HERE/'activate_camera.py';raw=path.read_text(encoding='utf-8')
raw=raw.replace("assert old_identity==new_identity and new_identity['threshold']==.8 and new_identity['ambiguity_margin']==.1",
 "assert {k:v for k,v in old_identity.items() if k!='enrollment_photos'}=={k:v for k,v in new_identity.items() if k!='enrollment_photos'}\nassert new_identity['threshold']==.8 and new_identity['ambiguity_margin']==.1\nassert new_identity['enrollment_photos']=={'enabled':True,'directory':'~/.local/share/aura/enrollment_photos','max_images_per_session':192}")
raw=raw.replace("and camera['identity']['sampling_diagnostics'].get('template_policy')=='frontal_medoid_v1'", "and camera['identity']['sampling_diagnostics'].get('template_policy')=='frontal_medoid_v1'\n       and camera['identity'].get('enrollment_photos',{}).get('ready')")
raw=raw.replace('FRONTAL_TEMPLATE_POLICY_LOADED_EXISTING_IDENTITY_PRESERVED','ENROLLMENT_PHOTO_ARCHIVE_ENABLED_EXISTING_IDENTITY_PRESERVED')
path.write_text(raw,encoding='utf-8')
path=HERE/'verify.py';raw=path.read_text(encoding='utf-8')
raw=raw.replace("assert h['identity']['sampling_diagnostics']['template_policy']=='frontal_medoid_v1'", "assert h['identity']['sampling_diagnostics']['template_policy']=='frontal_medoid_v1'\nphotos=h['identity']['enrollment_photos'];assert photos['enabled'] and photos['ready'] and not photos['error']\nassert Path(photos['directory']).is_dir() and Path(photos['directory']).stat().st_mode&0o777==0o700")
raw=raw.replace("'camera_policy':h['identity']['sampling_diagnostics']['template_policy'],", "'camera_policy':h['identity']['sampling_diagnostics']['template_policy'],'enrollment_photos':photos,")
raw=raw.replace("('camera_policy','database','threshold','ui_phase')", "('camera_policy','enrollment_photos','database','threshold','ui_phase')")
path.write_text(raw,encoding='utf-8')
print('Prepared isolated photo archive, real-model temporary photo checks and camera-only activation.')
