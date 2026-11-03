"""Copy only public runtime source for an isolated integration candidate."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
root=Path('/home/root/aura-yuki-validation-20261030')
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
args=Path('/proc',pid,'cmdline').read_bytes().split(b'\0')
config_path=Path(args[args.index(b'--config')+1].decode())
config=json.loads(config_path.read_text())
print('CONFIG_FIELDS',json.dumps(list(config)))
for key in ('runtime','runtime_root','entry','entrypoint','script','source_root'):
    if key in config:print(key,json.dumps(config[key]))
runtime=config_path.parent.parent/'runtime'
assert runtime.is_dir() and not runtime.is_symlink()
files=['aura/tools/board_avatar_gtk.py','aura/tools/board_avatar_worker.py','aura/tools/realtime_controller.py',
       'aura/tools/streaming_controller.py','aura/tools/gstreamer_audio.py','aura/tools/realtime_audio.py',
       'aura/tools/gstreamer_audio_engine.py','aura/tools/gstreamer_persistent_engine.py',
       'aura/tools/check_gstreamer_clock.py']
manifest={}
with zipfile.ZipFile(root/'native_integration/board-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in files:
        p=runtime/name
        if not p.exists():p=runtime/name.removeprefix('aura/')
        assert p.is_file(),name
        data=p.read_bytes();archive.writestr(name,data);manifest[name]=hashlib.sha256(data).hexdigest()
    archive.writestr('manifest.json',json.dumps({'runtime':str(runtime),'pid':pid,'hashes':manifest},indent=2))
print(json.dumps({'source_files':len(manifest),'runtime':str(runtime),'pid':pid,'archive':'native_integration/board-source.zip'}))
