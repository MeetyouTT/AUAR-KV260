from common import *
remote_collect(r"""
import tarfile,sys,pathlib,hashlib,json,io
from pathlib import Path
home=Path.home()
w=home/'aura-pan-wide-20261028'
sources={}
ip=[Path(x) for x in (w/'platform/repos.txt').read_text().splitlines()]
old=home/'aura-pan-joint-20261023'
def add(src,dest):
    p=Path(src)
    if not p.is_file(): raise FileNotFoundError(src)
    sources[dest]=p
def tree(src,dest,accept=lambda p:True):
    for p in sorted(src.rglob('*')):
        if p.is_file() and accept(p):add(p,dest+'/'+str(p.relative_to(src)))
tree(w/'platform/inputs','src/fpga/inputs')
tree(w/'platform/ip_repo','src/fpga/generated_ip')
for i,key in enumerate(['dpu_ip','platform_ip','platform_cache']):
    tree(ip[i],'src/fpga/vendor/'+key)
for n in ['visual_servo.sv','disabled_audio.sv','pin.xdc']:add(w/'platform'/n,'src/fpga/'+n)
add(w/'platform/platform/platform.srcs/sources_1/bd/bd/kv260_ispMipiRx_vcu_DP.bd','src/fpga/reference/kv260_ispMipiRx_vcu_DP.bd')
add(w/'platform/platform/platform.xpr','src/fpga/reference/platform.xpr')
add(w/'platform/platform_generated.tcl','src/fpga/reference/platform_generated.tcl')
add(old/'implementation/source_routed.dcp','src/fpga/reference/incremental.dcp')
for n in ['prepare.tcl','implement.tcl','export_resume.tcl','build_joint.py','package_wide.py','bitstream_pairing.py','audit-final.tcl']:
    add(w/n,'build/original/'+n)
for n in ['EXPORT_RECOVERY_INPUTS.json','BUILD_STATUS.json','PACKAGE_STATUS.json','OFFLINE_COMPLETION.json','INDEPENDENT_AUDIT.json']:
    add(w/n,'build/reports/history/'+n)
for p in (w/'implementation').glob('*.rpt'):add(p,'build/reports/'+p.name)
add(w/'implementation/implementation.json','build/reports/implementation.json')
add(w/'implementation/visual_servo_source_implemented.xsa','board/handoff/wide.xsa')
tree(w/'bundle/lib/firmware/xilinx','board/firmware')
tree(w/'bundle/driver','board/driver')
add(w/'bundle/candidate-manifest.json','board/firmware_pairing.json')
for p in (w/'candidate/tests').glob('tb_*.sv'):add(p,'sim/rtl/'+p.name)
tree(w/'candidate/native','src/fpga/native')
add(w/'candidate/tests/test_protocol.c','sim/native/test_protocol.c')
add(w/'validation/rtl/result.json','data/reference/xsim_historical.json')
add(old/'bundle/lib/firmware/xilinx/aura-visual-servo-b4096-v2/aura-visual-servo-b4096-v2.dtbo','src/fpga/overlay/base_overlay.dtbo')
add(home/'aura-system-pan-20261028/fresh-base.dtb','src/fpga/overlay/base.dtb')
tree(w/'controller','src/motion/controller',lambda p:p.suffix in ('.py','.so','.h','.c','.cpp') or p.name.startswith('LICENSE'))
tree(w/'ps_trajectory_v1','src/motion/trajectory',lambda p:p.suffix in ('.py','.so','.h','.c','.cpp','.hpp') or p.name.startswith('LICENSE'))
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
    records=[]
    for dest,p in sources.items():
        if p.is_symlink() and not p.resolve().is_file():raise RuntimeError(p)
        b=p.read_bytes(); h=hashlib.sha256(b).hexdigest()
        e=tarfile.TarInfo(dest);e.size=len(b);tar.addfile(e,io.BytesIO(b))
        records.append(dict(path=dest,source=str(p.relative_to(home)),sha256=h,bytes=len(b)))
    b=json.dumps(records,indent=1).encode();e=tarfile.TarInfo('build/reports/ubuntu_inputs.json');e.size=len(b);tar.addfile(e,io.BytesIO(b))
""",ROOT)
rows=load(ROOT/'build/reports/ubuntu_inputs.json')
for r in rows:
    if sha(ROOT/r['path'])!=r['sha256']:raise RuntimeError(r['path'])
print(len(rows),'Ubuntu FPGA/motion inputs verified',flush=True)
