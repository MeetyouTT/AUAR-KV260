import hashlib,json,sqlite3
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-slot-wait-81e6463c3747-298300')
config=json.loads((root/'board_camera_ui.json').read_text());identity=json.loads(Path(config['identity']['config']).read_text())
db=Path(identity['database']).expanduser();out={'read_only':True,'database_exists':db.is_file()}
if db.is_file():
 con=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
 try:
  names={row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  out['counts']={name:con.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ('identities','templates') if name in names}
 finally:con.close()
photos=identity.get('enrollment_photos') or {};archive=Path(photos.get('directory','/nonexistent')).expanduser()
out['archive_exists']=archive.is_dir();out['archive_file_counts']={suffix:sum(1 for _ in archive.rglob('*'+suffix)) for suffix in ('.json','.png','.jpg')} if archive.is_dir() else {}
model=Path('/home/root/aura-dpu-vision-20261021/staging/03580d3216661ba0/kit/sface_public_int8.xmodel')
manifest=model.with_name('sface-manifest.json')
out['model']={'path':str(model),'exists':model.is_file(),'sha256':hashlib.sha256(model.read_bytes()).hexdigest() if model.is_file() else None}
out['manifest']={'path':str(manifest),'exists':manifest.is_file(),'sha256':hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None}
print(json.dumps(out))
