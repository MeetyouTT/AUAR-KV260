"""Finish the active local Ubuntu build, firmware export and RAR acceptance without a desktop connection."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time
home=Path.home();here=Path(__file__).resolve().parent;base=here.parent;q=base/'verification';pkg=base/'auar_xuefei'
viv=home/'Xilinx_2022.2/Vivado/2022.2';vit=home/'Xilinx_2022.2/Vitis/2022.2';dt=home/'kv260-dpu41-control-20261001/dependencies/dtc-1.7.2'
run=q/'run01';fw=q/'firmware-fresh01';delivery=home/'下载/AUAR_方案A源码交付_9a4f_20261103'
def note(status,phase,**rest):
 info=dict(status=status,phase=phase,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**rest)
 pending=q/'release_state.tmp';pending.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n');os.replace(str(pending),str(q/'release_state.json'));print(info,flush=True)
def invoke(label,cmd,env=None):
 with (q/(label+'.log')).open('xb') as f:
  p=subprocess.run([str(x) for x in cmd],cwd=str(base),env=env,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(label+' exit '+str(p.returncode))
try:
 note('RUNNING','vivado_implementation')
 receipt=run/'implement.receipt.json'
 while not receipt.is_file():
  if not Path('/proc/638107').is_dir():raise RuntimeError('Vivado driver ended without implementation receipt; inspect driver01.log')
  time.sleep(20)
 info=json.loads(receipt.read_text())
 if info.get('status')!='PASS':raise RuntimeError('Implementation failed; inspect run01/implement.console.log and reports')
 note('RUNNING','fresh_bit_xsa_firmware')
 env=os.environ.copy();env['LD_LIBRARY_PATH']=str(dt/'libfdt')+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
 invoke('fresh_firmware_driver',[sys.executable,'-B',pkg/'build/export_firmware.py','--out',fw,
  '--bit',run/'hardware/auar_source.bit','--xsa',run/'hardware/auar_source.xsa','--base-dtb',home/'aura-system-pan-20261028/fresh-base.dtb',
  '--dtc',vit/'bin/dtc','--fdtoverlay',dt/'fdtoverlay','--xclbinutil',vit/'bin/xclbinutil','--bootgen',vit/'bin/bootgen'],env)
 note('RUNNING','render_measured_report')
 invoke('final_report_driver',[sys.executable,'-B',here/'final_report.py'])
 note('RUNNING','rar_pack_extract_regression')
 rar=home/'auar-engineering-delivery-XpV7MC/rar-tool/usr/bin/rar'
 invoke('final_archive_driver',[sys.executable,'-B',base/'final_roundtrip.py',pkg,q,delivery,rar,viv,vit])
 result=json.loads((delivery/'archive_verification.json').read_text())
 note('PASS','published',path=str(delivery),rar_bytes=result['bytes'],sha256=result['sha256'])
except Exception as exc:
 note('FAIL','action_required',error=str(exc))
 raise
