from pathlib import Path
import hashlib,json,zipfile
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');basis=json.loads((phase/'board_source/manifest.json').read_text())
name='tools/native_pixels.cpp';path=Path(basis['runtime'])/'aura'/name;data=path.read_bytes()
assert hashlib.sha256(data).hexdigest()==basis['component_pins'][name]
with zipfile.ZipFile(phase/'paired_ab/fresh-native-source.zip','w',zipfile.ZIP_DEFLATED) as out:out.writestr(name,data)
print(json.dumps(dict(source=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))))
