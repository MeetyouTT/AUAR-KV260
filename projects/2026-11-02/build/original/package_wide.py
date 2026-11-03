"""Package the matched wide platform only after routed and independent audits."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,subprocess,zipfile
from bitstream_pairing import check_pairing
R=Path(__file__).resolve().parent;APP='aura-visual-servo-b4096-wide-v1';BUILD=0x10282601
V=Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin')
F=Path('/home/ghmd/petalinux/2022.2/components/yocto/buildtools_extended/sysroots/x86_64-petalinux-linux/usr/bin')
D=Path('/home/ghmd/kv260-dpu41-control-20261001/dependencies/dtc-1.7.2')
OLD=Path('/home/ghmd/aura-pan-joint-20261023')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def run(label,args,env=None):
 p=subprocess.run([str(x) for x in args],capture_output=True,env=env)
 (R/'final-audit'/(label+'.log')).write_bytes(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(label+' failed; see audit log')
 return p.stdout
state=json.loads((R/'BUILD_STATUS.json').read_text());assert state['status']=='IMPLEMENTED_PENDING_PAIRING_AND_BOARD'
if state.get('export_recovered'):
    assert 'AURA_WIDE_EXPORT_RESUMED_FROM_ROUTED_CHECKPOINT' in (R/'export-resume-console.txt').read_text()
    recovery=json.loads((R/'EXPORT_RECOVERY_INPUTS.json').read_text())
    assert sha(R/'implementation/source_routed.dcp')==recovery['routed_dcp_sha256']
    assert sha(R/'implementation/visual_servo_source.bit')==recovery['original_bit_sha256']
    assert sha(R/'export_resume.tcl')==recovery['recovery_tcl_sha256']
else:
    assert 'AURA_SOURCE_PLATFORM_IMPLEMENTED' in (R/'implement-console.txt').read_text()
assert all(sha(p)==v for p,v in state['source_sha256'].items())
rtl=json.loads((R/'validation/rtl/result.json').read_text());assert len(rtl)==4 and all(t['passed'] for t in rtl)
assert 'Ran 204 tests' in (R/'validation/controller-tests.log').read_text() and '\nOK\n' in (R/'validation/controller-tests.log').read_text()
native=json.loads((R/'validation/native/native-build.json').read_text());assert sha(R/'validation/native/libvsrv2.so')==native['library_sha256']
assert json.loads((R/'validation/wide_gui_qualification.json').read_text())['passed']==10
handoff=json.loads((R/'handoff-audit.json').read_text());assert handoff['passed'] and all(sha(p)==h for p,h in handoff['source_sha256'].items())
assert 'AURA_VISUAL_SERVO_FINAL_PROPERTIES_VERIFIED' in (R/'final-audit/console.log').read_text()
spec=importlib.util.spec_from_file_location('old_report_parser',OLD/'finalize_offline.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
report=mod.verify_reports(R/'implementation');audit=mod.verify_reports(R/'final-audit');assert report['timing']==audit['timing']
impl=R/'implementation';xsa=impl/'visual_servo_source_implemented.xsa';original=impl/'visual_servo_source.bit'
with zipfile.ZipFile(xsa) as z:
 name,=[n for n in z.namelist() if Path(n).name=='kv260_ispMipiRx_vcu_DP.hwh'];assert z.read(name)==Path(handoff['generated_hwh']).read_bytes()
 name,=[n for n in z.namelist() if n.endswith('.bit')];embedded=z.read(name)
pair=check_pairing(original.read_bytes(),embedded);paired=impl/'visual_servo_paired.bit'
with paired.open('xb') as f:f.write(embedded)
assert not (R/'bundle').exists();bundle=R/'bundle';fw=bundle/'lib/firmware/xilinx'/APP;fw.mkdir(parents=True);driver=bundle/'driver';driver.mkdir()
bif=R/'full-pl.bif';bif.write_text('all:\n{\n [destination_device=pl] '+str(paired)+'\n}\n')
run('bootgen',[V/'bootgen','-arch','zynqmp','-image',bif,'-o',fw/(APP+'.bit.bin')])
oldfw=OLD/'bundle/lib/firmware/xilinx/aura-visual-servo-b4096-v2';overlay=fw/(APP+'.dtbo');shutil.copy2(oldfw/'aura-visual-servo-b4096-v2.dtbo',overlay)
run('overlay-name',[F/'fdtput','-t','s',overlay,'/fragment@0/__overlay__','firmware-name',APP+'.bit.bin'])
oldtext=run('old-overlay',[V/'dtc','-I','dtb','-O','dts',oldfw/'aura-visual-servo-b4096-v2.dtbo'])
newtext=run('new-overlay',[V/'dtc','-I','dtb','-O','dts',overlay]);assert oldtext.replace(b'aura-visual-servo-b4096-v2.bit.bin',(APP+'.bit.bin').encode())==newtext
base=Path('/home/ghmd/aura-system-pan-20261028/fresh-base.dtb');assert sha(base)=='22516e08c2c862dfe3ee999a962ff62ed7830ad8e1183e36432cd22acde77762'
run('fresh-dt-merge',[D/'fdtoverlay','-i',base,'-o',R/'final-audit/merged-wide.dtb',overlay],dict(os.environ,LD_LIBRARY_PATH=str(D/'libfdt')))
shutil.copy2(oldfw/'aura-visual-servo-b4096-v2.xclbin',fw/(APP+'.xclbin'))
assert sha(fw/(APP+'.xclbin'))=='875ca912d87b2c993716f4c353265a9cf403b0c9890442610e64291787caafc3'
(fw/'shell.json').write_text(json.dumps({'shell_type':'XRT_FLAT','num_slots':'1'})+'\n')
shutil.copy2(R/'validation/native/libvsrv2.so',driver/'libvsrv.so')
for n in ['vsrv_driver.py','vsrv_transport.py']:shutil.copy2(R/'candidate/runtime/aura/board/motion'/n,driver/n)
bench=(OLD/'bench_identity_stop.py').read_text().replace('aura-visual-servo-b4096-v2',APP).replace('0x778d2512','0x10282601');(bundle/'bench_identity_stop.py').write_text(bench)
manifest={'schema_version':1,'status':'OFFLINE_VSRV2_BUNDLE_PENDING_BOARD','abi':2,'build_id':BUILD,'app':APP,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pulse_capability_us':[500,2500],'nominal_center_us':1500,'min_lease_ms':4,'frame_us':20000,'step_us':4,'joint_implementation_passed':True,'independent_checkpoint_audit_passed':True,'bitstream_and_handoff_from_same_project':True,'board_accessed':False,'deployable':False,'physical_range_verified':False,'mechanical_angle_measured':False,'external_waveform_verified':False,'report':report,'pairing':pair,'xsa_sha256':sha(xsa),'routed_dcp_sha256':sha(impl/'source_routed.dcp'),'base_fdt_sha256':sha(base),'fresh_merged_fdt_sha256':sha(R/'final-audit/merged-wide.dtb'),'base_boot_id':'5f167a36-a715-4bbb-9186-4dff2bff8ee3','payload_files':{p.name:sha(p) for p in driver.iterdir()},'runtime_files':{'/lib/firmware/xilinx/'+APP+'/'+p.name:sha(p) for p in fw.iterdir()},'bench_sha256':sha(bundle/'bench_identity_stop.py'),'validation':{'rtl_suites':4,'controller_checks':204,'native_fake_checks':18,'gui_range_checks':10}}
save(bundle/'candidate-manifest.json',manifest)
(bundle/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(bundle))+'\n' for p in sorted(bundle.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
save(R/'PACKAGE_STATUS.json',{'status':'PAIRED_OFFLINE_BUNDLE_READY_PENDING_BOARD','manifest_sha256':sha(bundle/'candidate-manifest.json'),'created_utc':manifest['created_utc'],'report':report})
print(json.dumps({'status':'PAIRED_OFFLINE_BUNDLE_READY_PENDING_BOARD','manifest_sha256':sha(bundle/'candidate-manifest.json'),'app':APP,'limits_us':[500,2500]}))
