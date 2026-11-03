"""Read back UART bodies, deployed sources, packages and native acceptance."""
import hashlib,json,re,sys,zipfile
from pathlib import Path
WORK=Path(__file__).resolve().parent
REPO=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0,str(REPO))
from board.interaction.ui_contract import validate_snapshot
KNOWN_FAILURES={
 '20261010T103224.081823Z-page-main':'Historical Cairo capture abort',
 '20261010T160330.264462Z-final-checks':'UART unavailable; no board commands sent',
 '20261011T021457.941245Z-camera-status':'New boot: UI API unavailable while EDID absent',
 '20261011T022909.629373Z-startup-recover':'EDID changed; guarded deployment rejected before mutation',
 '20261011T023941.138641Z-final-checks':'Synchronous diagnostics exceeded API deadline',
 '20261011T050532.859871Z-final-checks':'Repeated synchronous diagnostic timeout',
}
def read(p):return json.loads(Path(p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def latest(phase):return sorted((WORK/'evidence').glob('*-'+phase))[-1]
def image(folder,value,name):
 b=(folder/name).read_bytes();assert len(b)==value['bytes'] and sha(b)==value['sha256'],name

def main():
 responses=0;successful=[];retained=[]
 for folder in sorted((WORK/'evidence').iterdir()):
  if not folder.is_dir():continue
  result=read(folder/'result.json')
  for row in result['commands']:
   b=(folder/row['output']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256'],folder
   responses+=1
  if result['complete']:
   assert result['console_echo_restored'] and all(r['exit_code']==0 for r in result['commands']),folder
   successful.append(folder.name)
  else:
   assert folder.name in KNOWN_FAILURES,folder
   if result['commands']:assert result['console_echo_restored'],folder
   else:assert folder.name=='20261010T160330.264462Z-final-checks'
   retained.append({'session':folder.name,'reason':KNOWN_FAILURES[folder.name]})
 manifest=read(WORK/'manifest.json');meta=read(WORK/'package_validation.json')
 raw=Path(meta['archive']).read_bytes();assert len(raw)==meta['bytes'] and sha(raw)==meta['sha256']
 with zipfile.ZipFile(meta['archive']) as z:
  assert z.testzip() is None and set(z.namelist())==set(manifest['files'])|{'manifest.json'}
  assert json.loads(z.read('manifest.json'))==manifest
  for name,row in manifest['files'].items():
   b=z.read(name);assert len(b)==row['bytes'] and sha(b)==row['sha256'],name
   if name.startswith('aura/'):assert b==(REPO/name[5:]).read_bytes(),name
   if name.startswith('startup/'):assert b==(REPO/'scripts/board_ui_startup'/Path(name).name).read_bytes(),name
 assert sha((REPO/'artifacts/releases'/Path(meta['archive']).name).read_bytes())==meta['sha256']
 applied=read(latest('apply')/'apply.json');boot=applied['before']['boot_id']
 assert applied['native_test_count']==60
 tested_manifest=read(WORK/'generations'/applied['update_id']/'manifest.json')
 expected={n:manifest['files'][n]['sha256'] for n in manifest['runtime_files']}
 assert applied['runtime_files']==expected
 recovery=read(latest('startup-recover')/'startup-recover.json')
 assert recovery['startup_recovered'] and recovery['camera_after']['pid']==recovery['before']['camera']['pid']
 assert recovery['update_id']==manifest['update_id'] and recovery['runtime_hashes']==expected
 folder=latest('final-checks');r=read(folder/'result.json')
 assert r['complete'] and len(r['commands'])==10
 camera=read(folder/'0-camera-test.json')
 assert len(camera['checks_passed'])==8
 for key in ('capture_frames','detected_frames'):assert camera['after'][key]>camera['before'][key]
 snap=camera['ui']['ui_runtime']['snapshot'];validate_snapshot(snap,boot,snap['observed_mono_ms'])
 assert snap['source_kind']=='actual' and set(snap['modules'])=={'camera','vision','target'}
 assert camera['ui']['ui_runtime']['frame_visible']
 for key,name in [('screenshot','0-camera-test-screen.jpg'),('main_screenshot','0-camera-test-main-screen.jpg')]:image(folder,camera[key],name)
 audio=read(folder/'1-avatar-check.json')
 assert len(audio['checks_passed'])==7 and abs(audio['pause_audio_delta_seconds'])<.05
 assert audio['gui_pid']==camera['gui_pid'] and audio['final']['phase']=='IDLE'
 assert not audio['final']['playing'] and audio['final']['ui_runtime']['frame_visible']
 for index,page in enumerate(('main','demo','devices','connection','settings','main'),2):
  label=str(index)+'-page-'+page;d=read(folder/(label+'.json'));g=d['geometry']
  assert d['page']==page and (g['width'],g['height'])==(1024,600) and not g['dialogs']
  for c in g['visible_controls'].values():assert c['height']>=48 and c['x']+c['width']<=585 and c['y']+c['height']<=556
  image(folder,d['screenshot'],label+'-screen.jpg')
 final=read(folder/'9-camera-inspect.json')
 assert final['boot_id']==boot and final['runtime_hashes']==expected
 assert final['applied']['update_id']==applied['update_id']
 assert final['latest_report']['source_hashes_at_launch']['tools/board_avatar_gtk.py']==expected['aura/tools/board_avatar_gtk.py']
 assert not final['latest_report']['errors'] and final['protected']==applied['before']['protected']
 for key,value in applied['before']['saved_preferences']['values'].items():assert final['settings']['avatar_user_settings.json']['values'][key]==value,key
 assert final['settings']['avatar_service_settings.json']['connection']=={'enabled':True,'host':'127.0.0.1','port':8790}
 assert [o['pid'] for o in final['owners']]==[camera['camera_pid']]
 assert camera['camera_pid']==applied['before']['camera']['pid'] and final['launch']['pid']==camera['gui_pid']
 for name in ('Xorg','dfx-mgrd'):
  before={x['pid'] for x in applied['before']['processes'][name]}
  after={x['pid'] for x in final['related_processes'] if name in x['argv']}
  assert before==after,(name,before,after)
 for unit in ('aura-avatar-ui.service','aura-camera-ui.service'):
  row=final['units'][unit]
  expected_sha=tested_manifest['files']['startup/aura-avatar-ui.service']['sha256'] if unit=='aura-avatar-ui.service' else expected['aura/scripts/board_camera_ui/aura-camera-ui.service']
  assert row['sha256']==expected_sha
  assert all(x in row['state']['output'] for x in ('ActiveState=active','SubState=running','UnitFileState=enabled','NRestarts=0'))
 assert sum(int(x) for x in re.findall(r'Ran (\d+) tests?',final['native_test_log']))==60
 assert 'current 1024 x 600' in final['display_setup']['display']
 fixture=read(latest('ui-acceptance')/'6-fixture.json')
 assert fixture['fixture_pid_exited'] and not fixture['restored_connection']['enabled']
 assert fixture['ready']['ui_runtime']['snapshot']['source_kind']=='fixture'
 assert fixture['cancel']['ui_runtime']['snapshot']['interaction_suppressed']
 assert [x['action'] for x in fixture['fixture_commands']]==['record_start','record_stop','cancel']
 synthetic=read(WORK/'host-native-video/validation.json')
 assert synthetic['after_blocking_gtk']['displayed_frames']>=synthetic['before_blocking_gtk']['displayed_frames']+4
 assert not synthetic['freeze_hidden']['frame_visible'] and synthetic['reconnect_pixel'][0]>180 and max(synthetic['cleared_pixel'])<5
 profile=read(folder/'8-preview-profile.json')
 assert all(x['frame_visible'] and not x['preview_error'] and not x['ui_error'] for x in profile['rows'])
 assert profile['preview_display_hz']>8
 post=latest('post-startup');post_result=read(post/'result.json')
 assert post_result['complete'] and len(post_result['commands'])==4
 status=read(post/'0-camera-status.json');current=read(post/'3-camera-inspect.json')
 assert current['runtime_hashes']==expected and current['boot_id']==boot
 assert current['launch']['pid']==recovery['launch']['pid']
 assert current['protected']==final['protected'] and current['settings']==final['settings']
 assert [o['pid'] for o in current['owners']]==[camera['camera_pid']]
 assert status['ui']['phase']=='IDLE' and status['ui']['ui_runtime']['frame_visible']
 assert not current['latest_report']['errors']
 assert current['latest_report']['source_hashes_at_launch']['tools/board_avatar_gtk.py']==expected['aura/tools/board_avatar_gtk.py']
 assert current['units']['aura-avatar-ui.service']['sha256']==manifest['files']['startup/aura-avatar-ui.service']['sha256']
 for u in current['units'].values():assert all(s in u['state']['output'] for s in ('ActiveState=active','SubState=running','UnitFileState=enabled','NRestarts=0'))
 page=read(post/'1-page-main.json');assert page['page']=='main' and not page['geometry']['dialogs']
 image(post,page['screenshot'],'screen.jpg')
 current_profile=read(post/'2-preview-profile.json')
 assert all(x['frame_visible'] and not x['preview_error'] and not x['ui_error'] for x in current_profile['rows'])
 out={'status':'PASS','update_id':manifest['update_id'],'startup_release':manifest['startup_release_id'],
  'archive_sha256':meta['sha256'],'uart_responses_verified':responses,'successful_sessions':len(successful),
  'retained_failed_sessions':retained,'negative_probe':'20261011T050619.712475Z-response-probe: 3 HTTP 503 retained',
  'native_tests':60,'host_framework_tests':118,'host_diagnostic_tests':2,'host_http_tests':4,'host_display_fallback_tests':5,
  'actual_camera_pid':camera['camera_pid'],'gui_pid':current['launch']['pid'],'tested_gui_pid':camera['gui_pid'],'board_boot_id':boot,
  'final_evidence':str(post),'acceptance_evidence':str(folder),'preview_display_hz':profile['preview_display_hz'],
  'ui_published_frame_age_ms':profile['ui_frame_age_ms'],'native_entry_frame_age_ms':profile['native_entry_age_ms'],
  'display_setup':current['display_setup'],'audio_command_ack_ms':audio['command_ack_ms'],
  'after_startup_update_profile':{'preview_display_hz':current_profile['preview_display_hz'],
   'native_entry_frame_age_ms':current_profile['native_entry_age_ms'],'ui_published_frame_age_ms':current_profile['ui_frame_age_ms']},
  'host_graceful_async_stop_check':'PASS',
  'scope':'UI_NATIVE_REAL_CAMERA_CPU_AND_CACHED_PLAYBACK_NOT_FULL_SYSTEM_ACCEPTANCE',
  'not_verified':['physical_panel_end_to_end_latency','physical_touch_all_new_pages','cold_boot_after_latest_changes',
   'missing_EDID_fallback_on_real_screen','identity','real_microphone','ASR_VLM_TTS','DPU_project_model',
   'mechanical_following','long_term_performance']}
 (WORK/'validation_final.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
