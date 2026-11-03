"""Install a verified new release beside the old one. Never programs the FPGA."""
import argparse,gzip,hashlib,io,json,os,re,tarfile,uuid
from pathlib import Path,PurePosixPath
APP='aura-visual-servo-b4096-wide-v1';BASE=Path('/home/root/aura-pan-wide-20261028')
FW=Path('/lib/firmware/xilinx')/APP
def sha(b):return hashlib.sha256(b).hexdigest()
def local_name(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts or str(p)!=name:raise ValueError('Unsafe archive path')
    return p
def unpack(blob):
    if len(blob)>16000000:raise ValueError('Transfer archive too large')
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as f:raw=f.read(33000001)
    if len(raw)>33000000:raise ValueError('Expanded transfer too large')
    files={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as z:
        for m in z.getmembers():
            local_name(m.name)
            if not m.isfile() or m.name in files or m.size>9000000:raise ValueError('Unexpected archive member')
            files[m.name]=z.extractfile(m).read()
    t=json.loads(files['transfer.json'])
    if t.get('schema')!='aura-wide-transfer-1' or t.get('app')!=APP or t.get('build_id')!=0x10282601:raise ValueError('Transfer target differs')
    if set(files)!=set(t['files'])|{'transfer.json'}:raise ValueError('Unexpected or missing transfer files')
    for name,record in t['files'].items():
        if len(files[name])!=record['bytes'] or sha(files[name])!=record['sha256']:raise ValueError('Transfer content changed')
    return t,files
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('--sha256',required=True);p.add_argument('--boot',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    blob=a.archive.read_bytes()
    if sha(blob)!=a.sha256:raise ValueError('Archive hash differs')
    t,files=unpack(blob)
    manifest_raw=files['release/candidate-manifest.json'];manifest=json.loads(manifest_raw)
    if sha(manifest_raw)!=t['manifest_sha256'] or manifest['build_id']!=0x10282601 or manifest['app']!=APP:raise ValueError('Manifest differs')
    release=BASE/('release-'+t['manifest_sha256'][:16]);control=BASE/'control-10282601'
    if t['release_root']!=str(release) or t['controller_root']!=str(control):raise ValueError('Release destination differs')
    if not a.execute:
        print(json.dumps({'validated_archive':True,'files':len(files),'programmed_hardware':False,'installed':False,'release':str(release)}));return
    if os.uname().machine!='aarch64' or os.geteuid()!=0:raise RuntimeError('Board root only')
    if not re.fullmatch(r'[0-9a-f-]{36}',a.boot) or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=a.boot:raise RuntimeError('Current boot differs')
    writes={};base_pins={}
    expected={str(FW/(APP+ext)) for ext in ['.bit.bin','.dtbo','.xclbin']}|{str(FW/'shell.json')}
    if set(manifest['runtime_files'])!=expected or {i['path'] for i in t['firmware']}!=expected:raise ValueError('Unexpected firmware destinations')
    for item in t['firmware']:
        data=files[item['archive_file']]
        if item['encoding']=='xor':
            source=Path('/lib/firmware/xilinx/aura-visual-servo-b4096-v2/aura-visual-servo-b4096-v2.bit.bin')
            if item['base_path']!=str(source):raise ValueError('Unexpected XOR base')
            old=source.read_bytes()
            if sha(old)!=item['base_sha256'] or len(old)!=len(data):raise ValueError('Old firmware differs; no reconstruction')
            base_pins[str(source)]=sha(old);data=bytes(x^y for x,y in zip(old,data))
        elif item['encoding']!='raw':raise ValueError('Unknown transfer encoding')
        if len(data)!=item['target_bytes'] or sha(data)!=item['target_sha256'] or sha(data)!=manifest['runtime_files'][item['path']]:raise ValueError('Reconstructed firmware differs')
        writes[Path(item['path'])]=data
    for name,data in files.items():
        local_name(name)
        if name.startswith('release/'):target=release/name[len('release/'):]
        elif name.startswith('controller/'):target=control/name[len('controller/'):]
        elif name.startswith('gui_patch/'):target=release/name
        elif name=='rated_range_trial.py':target=release/name
        else:continue
        writes[target]=data
    for root in [BASE,release,control,FW]:
        if root.is_symlink():raise ValueError('Release directory must not be a symlink')
    for target,data in writes.items():
        if target.is_symlink() or target.exists() and target.read_bytes()!=data:raise ValueError('Existing file differs; original retained')
    for target,data in writes.items():
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():continue
        temp=target.with_name(target.name+'.partial-'+uuid.uuid4().hex)
        try:
            with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
            os.chmod(temp,0o644);os.link(temp,target)
        finally:
            if temp.exists():temp.unlink()
    if any(sha(p.read_bytes())!=sha(b) for p,b in writes.items()):raise RuntimeError('Readback verification failed')
    if any(sha(Path(p).read_bytes())!=h for p,h in base_pins.items()):raise RuntimeError('Original firmware changed')
    result={'status':'INSTALLED_VERIFIED_NOT_LOADED','boot_id':a.boot,'release':str(release),'controller':str(control),'manifest_sha256':t['manifest_sha256'],'verified_files':len(writes),'programmed_hardware':False,'motion_commands':0,'services_changed':False,'old_firmware_unchanged':True}
    receipt=release/('install-receipt-'+a.boot+'.json')
    if not receipt.exists():
        with receipt.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
if __name__=='__main__':main()
