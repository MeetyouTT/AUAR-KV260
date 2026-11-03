"""If the cold source run reaches a measured timing-only failure, try two current-run recovery routes."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys,time
home=Path.home();ops=Path(__file__).resolve().parent;base=ops.parent;q=base/'verification';pkg=base/'auar_xuefei';cold=q/'run01';recovery=q/'timing-recovery01';dl=home/'下载/AUAR_方案A源码交付_9a4f_20261103';viv=home/'Xilinx_2022.2/Vivado/2022.2';vit=home/'Xilinx_2022.2/Vitis/2022.2';dt=home/'kv260-dpu41-control-20261001/dependencies/dtc-1.7.2'
def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def note(status,phase,**extras):
 v=dict(status=status,phase=phase,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**extras)
 tmp=q/'timing-recovery.state.tmp';save(tmp,v);os.replace(str(tmp),str(q/'release_state.json'));print(v,flush=True)
def invoke(label,cmd,env=None):
 with (q/(label+'.log')).open('xb') as f:r=subprocess.run([str(x) for x in cmd],cwd=str(base),stdout=f,stderr=subprocess.STDOUT,env=env)
 if r.returncode:raise RuntimeError(label+' exited '+str(r.returncode))
rec=cold/'implement.receipt.json'
while not rec.is_file():
 if not Path('/proc/638107').is_dir():sys.exit('Cold run ended without a receipt')
 time.sleep(30)
first=read(rec)
if first['status']=='PASS':
 print('Cold route passed; normal publication supervisor owns the release',flush=True);sys.exit(0)
measure=cold/'hardware/reports/implementation.json'
if not measure.is_file():sys.exit('New failure lacks timing report; manual investigation needed')
lim=read(measure)
if lim['drc_errors'] or min(lim['wns_ns'],lim['whs_ns'])>=0 or 'AUAR_BUILD_FAILED: Implementation timing/DRC failed' not in (cold/'implement.console.log').read_text(errors='replace'):
 sys.exit('Failure outside the timing-only recovery eligibility')
# Allow the primary supervisor to persist the original failure first.
for i in range(60):
 if read(q/'release_state.json').get('status')=='FAIL':break
 time.sleep(1)
try:
 note('RUNNING','timing_refinement',original_timing=lim)
 for name in ['refine_timing.tcl','refine_timing.py']:
  target=pkg/'build'/name
  if target.exists() and target.read_bytes()!=(ops/name).read_bytes():raise RuntimeError('Conflicting release file '+name)
  shutil.copyfile(str(ops/name),str(target))
 invoke('timing_refinement_driver',[sys.executable,'-B',pkg/'build/refine_timing.py','--prior',cold,'--out',recovery,'--vivado',viv/'bin/vivado'])
 note('RUNNING','firmware_from_refined_bit_xsa')
 env=os.environ.copy();env['LD_LIBRARY_PATH']=str(dt/'libfdt')+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
 fw=q/'firmware-recovery01'
 invoke('refined_firmware_driver',[sys.executable,'-B',pkg/'build/export_firmware.py','--out',fw,
  '--bit',recovery/'hardware/auar_source.bit','--xsa',recovery/'hardware/auar_source.xsa','--base-dtb',home/'aura-system-pan-20261028/fresh-base.dtb',
  '--dtc',vit/'bin/dtc','--fdtoverlay',dt/'fdtoverlay','--xclbinutil',vit/'bin/xclbinutil','--bootgen',vit/'bin/bootgen'],env)
 invoke('refined_report_driver',[sys.executable,'-B',ops/'final_report.py','--run',recovery.name,'--firmware',fw.name])
 rep=pkg/'report/validation_summary.md'
 with rep.open('a') as f:
  f.write('\n## 布线时序复收敛\n\n首轮从源码综合和完整布线后，setup WNS 为 %.3f ns，hold WHS 为 %.3f ns，DRC Error 为 %d。首次门禁拒绝导出。后续从同轮产生、已校验 SHA 的 placed 和 synth 检查点继续物理优化，保留器件时钟和时序门槛。上表记录最终通过的路线。附加命令、原始检查点哈希与首轮失败回执的哈希见 evidence/implementation_receipt.json。\n' % (lim['wns_ns'],lim['whs_ns'],lim['drc_errors']))
 with (pkg/'README.md').open('a') as f:
  f.write('\n## 首次完整布线仅在时序上未通过时\n\n保留冷启动输出 $OUT，确认 reports 与两份检查点仍在，运行以下已验证的补充入口。完成后固件导出的 --bit 与 --xsa 改取同一 $RECOVER/hardware 目录。此流程先核对源码指纹、四台 RTL、首轮失败回执、日志及检查点，再执行物理优化，完整应用相同的 timing、routing 和 DRC 门禁。\n\n')
  f.write(chr(96)*3+'sh\nexport RECOVER="$HOME/auar-route-recovery"\npython3 -B build/refine_timing.py --prior "$OUT" --out "$RECOVER" --vivado "$VIV/bin/vivado"\n'+chr(96)*3+'\n')
 note('RUNNING','rar_pack_extract_regression')
 rar=home/'auar-engineering-delivery-XpV7MC/rar-tool/usr/bin/rar'
 invoke('refined_archive_driver',[sys.executable,'-B',base/'final_roundtrip.py',pkg,q,dl,rar,viv,vit])
 r=read(dl/'archive_verification.json');note('PASS','published',path=str(dl),rar_bytes=r['bytes'],sha256=r['sha256'])
except Exception as e:
 note('FAIL','refinement_action_required',error=str(e));raise
