assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='a6d4a069-e9b0-4065-8df7-dc23556b168e'
assert sha(B/'startup/config.json')==EXPECTED
pins=json.loads((B/'startup/config.json').read_bytes())['component_sha256'];assert len(pins)==380 and all(sha(A/n)==v for n,v in pins.items())
face=json.loads((A/'config/pan_face.local.json').read_bytes());assert face['release_root']==str(ROOT) and face['manifest_sha256']==sha(ROOT/'deployment-manifest.json')==MANIFEST
files=json.loads((ROOT/'deployment-manifest.json').read_bytes())['files'];assert len(files)==25 and all(sha(f['destination'])==f['sha256'] for f in files)
before=snap(req());p=before['pan'];rb=p.get('readback') or {}
assert p['state']=='READY' and p['automatic_following'] is False and rb.get('flags')==0 and rb.get('lease_left_ms')==0
assert before['ui_page']=='vision' and before['handsfree']['enabled'] is True and before['handsfree']['microphone_open'] is True
issued=time.monotonic();reply=req('pan_face_follow');after=None;report=None
deadline=time.monotonic()+2.0
while time.monotonic()<deadline:
 after=snap(req());path=after.get('report')
 if path and path!=before.get('report'):
  try:
   report,digest=read_report(path)
   if after['pan']['automatic_following'] is True and report.get('status')=='CONTINUOUS_FACE_ZONE_RUNNING' and report.get('consumer_manifest_sha256')==MANIFEST:break
  except (OSError,ValueError):pass
 time.sleep(.12)
assert after and after['pan']['automatic_following'] is True and report and report.get('consumer_manifest_sha256')==MANIFEST
r=report.get('result') or {};rb=r.get('readback') or after['pan'].get('readback') or {}
print(json.dumps({'status':'ORIGINAL_UI_FOLLOW_ENABLED_FROM_CURRENT_POSITION','command_submitted_once':'pan_face_follow','command_issued_mono_ms':round(issued*1000),'before':before,'after':after,'report':after['report'],'report_sha256_at_start':digest,'protocol_armed_if_observed':rb.get('armed') is True or ((rb.get('flags') or 0)&14)==14,'controller_active_if_observed':r.get('active'),'initialization_submitted':False,'source_config_or_audio_changed':False}))
