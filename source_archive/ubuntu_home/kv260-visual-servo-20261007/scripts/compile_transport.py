"""Build audited AArch64 full-word accessors, no hardware access."""
import hashlib,json,re,subprocess,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'evidence'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-transport')
out.mkdir()
tool=Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin')
source=root/'native/vsrv_mmio.c';binary=out/'libvsrv.so'
def run(label,argv):
 p=subprocess.run(list(map(str,argv)),capture_output=True,text=True,timeout=60)
 (out/(label+'.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
 return p.stdout
run('compile',[tool/'aarch64-linux-gnu-gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',source,'-o',binary])
d=run('disassembly',[tool/'aarch64-linux-gnu-objdump','-d',binary])
r=d.split('<mmio_read32>:',1)[1].split('\n\n',1)[0]
w=d.split('<mmio_write32>:',1)[1].split('\n\n',1)[0]
assert re.search(r'\bldr\s+w0,\s*\[x0\]',r) and re.search(r'\bstr\s+w1,\s*\[x0\]',w)
assert r.count('dsb\tsy')==1 and w.count('dsb\tsy')==2
assert not re.search(r'\b(?:strb|strh|stp)\b',w)
e=run('elf',[tool/'aarch64-linux-gnu-readelf','-h','-V',binary]);assert 'AArch64' in e
state={'passed':True,'board_verified':False,'evidence':str(out),'library':str(binary),
 'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'word_access':'ldr w0 / str w1','barrier':'dsb sy','exclusive_lock':'/run/aura-vsrv.lock'}
(root/'CURRENT_TRANSPORT_BUILD.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(state))
