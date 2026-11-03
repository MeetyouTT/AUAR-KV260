"""Fresh render-only metadata; all live state is filtered on board before export."""
from pathlib import Path
import hashlib,json,subprocess,urllib.request,zipfile
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');out=phase/'paired_ab';out.mkdir(exist_ok=True)
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
args=[x.decode() for x in Path('/proc',pid,'cmdline').read_bytes().split(b'\0') if x]
start_path=Path(args[args.index('--config')+1]);startup=json.loads(start_path.read_text());runtime=Path(startup['runtime']).resolve(strict=True)
assert str(runtime)=='/home/root/aura-board-vision-20261030/06391079cfddb734-r3-ubuntu/runtime'
config_path=runtime/'aura/config/board_avatar_gtk.json';config=json.loads(config_path.read_text(encoding='utf-8-sig'))
keys=('schema_version','backend','tick_ms','native_avatar','native_pixel_threads','native_ui_tick_ms','stable_avatar_fps','cache_sequences','browser_port')
record=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),runtime=str(runtime),supervisor_pid=pid,
  startup_config_sha256=hashlib.sha256(start_path.read_bytes()).hexdigest(),render_config_path=str(config_path),
  render_config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),render_config={k:config[k] for k in keys if k in config})
offload=config.get('portrait_offload',{});record['offload_config']={k:offload[k] for k in ('enabled','selected','fps','target_fps') if k in offload}
try:
    with urllib.request.urlopen('http://127.0.0.1:'+str(config['browser_port'])+'/api/state',timeout=3) as response:state=json.load(response)
    # Do not emit replies, identity IDs, names, fingerprints, templates or arrays.
    portrait=state.get('portrait_offload',{});display=state.get('avatar_display',{});settings=state.get('ui_settings',{})
    record['live_render']={
      'portrait':{k:portrait[k] for k in ('mode','selected','ready','target_fps','fallback_fps','backend') if k in portrait},
      'display':{k:display[k] for k in ('kind','frames','fps','age_ms','target_fps','dropped','late','width','height') if k in display},
      'settings':{k:settings[k] for k in ('economy','fullscreen') if k in settings},
      'playing':bool(state.get('playing',False)),'paused':bool(state.get('paused',False))}
except Exception as error:record['live_render_error']=type(error).__name__+': '+str(error)
names=['tools/native_pixels.py','tools/native_video.py','tools/board_avatar_affine.py','tools/demo_script.py',
  'tools/idle_body_compositor.py','tools/realtime_facials.py','tools/facial_layers.py','tools/render_performance.py',
  'tools/pillow_compat.py','tools/board_avatar_worker.py','tools/board_avatar_gtk.py','tools/gstreamer_audio_worker.py']
hashes={}
with zipfile.ZipFile(out/'fresh-render-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in names:
        path=runtime/'aura'/name
        if not path.is_file():continue
        data=path.read_bytes();hashes[name]=hashlib.sha256(data).hexdigest();archive.writestr(name,data)
    library=runtime/'aura/tools/libaura_pixels.so'
    record['native_pixels_library']=dict(path=str(library),sha256=hashlib.sha256(library.read_bytes()).hexdigest(),bytes=library.stat().st_size)
    record['source_hashes']=hashes;archive.writestr('render-baseline.json',json.dumps(record,indent=2))
record['gpu_readable_candidates']=[]
for path in ('/proc/mali','/proc/mali0','/sys/kernel/debug/mali','/sys/class/misc/mali0','/sys/class/devfreq','/sys/module/mali/parameters'):
    p=Path(path)
    if p.exists():
        record['gpu_readable_candidates'].append(dict(path=path,directory=p.is_dir(),children=[x.name for x in p.iterdir()][:60] if p.is_dir() else None))
(out/'fresh-baseline.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
