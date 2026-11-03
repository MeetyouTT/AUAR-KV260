import base64,gzip,hashlib,json,sqlite3,urllib.request
from pathlib import Path
ROOT=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-slot-wait-81e6463c3747-298300')
UNIT='048ee59cf4f01d84f0442825926b38ae0940e3c566a005449385d34536734e2f'
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()==UNIT
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(route):
 with op.open('http://127.0.0.1:8790'+route,timeout=3) as f:return json.load(f)
h=get('/health');status=get('/v1/ui/status')
config=json.loads((ROOT/'board_camera_ui.json').read_text());identity_path=Path(config['identity']['config'])
identity=json.loads(identity_path.read_text())
out={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'release':str(ROOT),
 'unit_sha256':UNIT,'camera_pid':h['pid'],'camera_config':config,'identity_config':identity,
 'identity_config_path':str(identity_path),'identity_config_sha256':hashlib.sha256(identity_path.read_bytes()).hexdigest(),
 'face_count':status.get('modules',{}).get('identity',{}).get('face_count'),
 'face_backend':h['identity']['face_targets']['backend'],'identity_backend':h['identity'].get('backend'),'files':{}}
names=['board/vision/dpu_sface.py','board/identity/model_store.py','board/identity/sface_shadow.py',
 'board/identity/sface_producer.py','board/identity/sface_calibration.py','board/identity/calibration_http.py',
 'board/identity/live.py','board/identity/deferred.py','board/vision/reference_faces.py',
 'board/identity/store.py','board/identity/sampling.py','board/identity/photo_archive.py']
for name in names:
 path=ROOT/'aura'/name;raw=path.read_bytes()
 out['files'][name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'base64':base64.b64encode(raw).decode()}
db=Path(identity['database']);out['old_database_exists']=db.is_file()
if db.is_file():
 con=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
 try:
  out['old_database_counts']={name:con.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
   for name in ('persons','templates') if con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone()}
 finally:con.close()
photos=identity.get('enrollment_photos') or {};archive=Path(photos.get('directory','/nonexistent'))
out['old_archive_enabled']=photos.get('enabled',False)
out['old_archive_file_counts']={suffix:sum(1 for _ in archive.rglob('*'+suffix)) for suffix in ('.json','.png','.jpg')} if archive.is_dir() else {}
raw=json.dumps(out,separators=(',',':')).encode()
print(json.dumps({'files':len(names),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
