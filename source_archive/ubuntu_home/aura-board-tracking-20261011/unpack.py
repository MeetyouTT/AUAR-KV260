import base64,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
root=Path(STAGE)
data=base64.b64decode((root/'data.b64').read_bytes(),validate=True)
assert hashlib.sha256(data).hexdigest()==SHA
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    manifest=json.loads(archive.read('manifest.json'))
    assert archive.testzip() is None and set(archive.namelist())<=set(manifest['files'])|{'manifest.json'}
    for name in list(manifest['files'])+['manifest.json']:
        rel=PurePosixPath(name)
        assert not rel.is_absolute() and '..' not in rel.parts
        blob=archive.read(name) if name in archive.namelist() else Path(manifest['verified_board_seeds'][name]).read_bytes()
        if name!='manifest.json':
            row=manifest['files'][name]
            assert len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],name
        if name.endswith('.py'):compile(blob,name,'exec')
        p=root/'payload'/name;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():assert p.read_bytes()==blob
        else:p.write_bytes(blob)
print(json.dumps({'status':'PASS','verified_payloads':len(manifest['files'])}))
