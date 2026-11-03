from pathlib import Path
import subprocess,os,json
p=Path('/home/ghmd/auar-report-captures-01a19c53')
env=os.environ.copy();env['DISPLAY']=':0'
with (p/'vivado_report_gui_console.log').open('wb') as out:
 proc=subprocess.Popen(['/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/vivado','-mode','gui','-log',str(p/'vivado_report_gui.log'),'-journal',str(p/'vivado_report_gui.jou'),'-source',str(p/'open_dcp_reports.tcl')],cwd=p,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
(p/'report_gui_process.json').write_text(json.dumps({'pid':proc.pid,'board_accessed':False,'scope':'Open existing final DCP; display native resource and timing reports'}))
print(json.dumps({'launcher_pid':proc.pid}))
