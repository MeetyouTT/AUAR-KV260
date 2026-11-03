from pathlib import Path
import subprocess,datetime,json,hashlib
out=Path(__file__).resolve().parent
status={'stage':'RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'board_accessed':False,'new_synthesis':False,'new_routing':False,'firmware_generated_or_loaded':False}
def save():
 (out/'RUN_STATUS.json').write_text(json.dumps(status,indent=2)+'\n')
save()
try:
 with (out/'vivado_console.log').open('w') as log:
  proc=subprocess.run(['/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/vivado','-mode','batch','-nojournal','-log',str(out/'vivado.log'),'-source',str(out/'rerun_reports.tcl')],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=900)
 status['vivado_exit_code']=proc.returncode
 status['vivado_complete_marker']='AUAR_FRESH_REPORTS_COMPLETE' in (out/'vivado_console.log').read_text(errors='replace')
 status['stage']='VIVADO_COMPLETE' if proc.returncode==0 and status['vivado_complete_marker'] else 'VIVADO_FAILED'
except Exception as exc:
 status['stage']='FAILED';status['error']=type(exc).__name__+': '+str(exc)
status['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
save()
