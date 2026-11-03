"""Inspect GUI's cached track snapshot without returning coordinates or IDs."""
import json
import time
import urllib.request

op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as r:ui=json.load(r)
with op.open('http://127.0.0.1:8790/health',timeout=3) as r:health=json.load(r)
runtime=ui.get('ui_runtime',{});snap=runtime.get('snapshot',{});preview=snap.get('preview',{})
ref=runtime.get('frame_reference',{});modules=snap.get('modules',{});target=modules.get('target',{})
tracks=target.get('tracks',[]) if isinstance(target,dict) else []
now=time.monotonic()*1000
observed=snap.get('observed_mono_ms');captured=preview.get('captured_mono_ms')
ref_captured=ref.get('captured_mono_ms')
ages={k:(round(now-v,1) if type(v) in (int,float) else None) for k,v in
      [('snapshot_observed',observed),('preview_captured',captured),('frame_reference_captured',ref_captured)]}
print(json.dumps({'gui_phase':ui.get('phase'),'snapshot_present':bool(snap),
 'snapshot_age_ms':ages['snapshot_observed'],'preview_age_ms':ages['preview_captured'],
 'frame_reference_age_ms':ages['frame_reference_captured'],
 'snapshot_preview_frame_matches_runtime_reference':preview.get('frame_id')==ref.get('frame_id') and ref.get('frame_id') is not None,
 'snapshot_frame_matches_camera_observation':preview.get('frame_id')==health.get('observation_frame_id') and preview.get('frame_id') is not None,
 'target_module_keys':sorted(target.keys()) if isinstance(target,dict) else [],
 'track_count':len(tracks) if isinstance(tracks,list) else None,
 'track_shape_keys':sorted(tracks[0].keys()) if tracks and isinstance(tracks[0],dict) else [],
 'track_box_length':len(tracks[0].get('box',[])) if tracks and isinstance(tracks[0],dict) and isinstance(tracks[0].get('box'),list) else None,
 'identity_payload_exported':False},sort_keys=True))
