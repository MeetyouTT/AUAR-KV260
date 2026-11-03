import json,os,subprocess,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=4) as r:h=json.load(r)
lock=Path('/run/aura-person-dpu.lock').resolve();owners=[]
for folder in Path('/proc').iterdir():
 if not folder.name.isdigit():continue
 try:
  if any(os.path.realpath(str(fd))==str(lock) for fd in (folder/'fd').iterdir()):owners.append(int(folder.name))
 except OSError:pass
assert owners==[h['pid']],owners
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'sole_dpu_owner_pids':owners,
 'frame_progress':h['detected_frames'],'native_primary_deferred':h.get('native_primary_deferred'),
 'state':json.loads(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/state.json').read_text()),
 'current_camera_command':(Path('/proc')/str(h['pid'])/'cmdline').read_bytes().replace(bytes([0]),b' ').decode(),
 'candidate_library_mapped':any('libaura_native_v2_candidate.so' in row for row in (Path('/proc')/str(h['pid'])/'maps').read_text().splitlines()),
 'gui_state':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ActiveState','-p','MainPID'],text=True)}))
