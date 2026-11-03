from pathlib import Path
import subprocess,json,sys,shutil,hashlib
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
remote='/home/ghmd/auar-techdoc-01a1a1a5'
subprocess.run(['ssh','aura-ubuntu','mkdir -p '+remote+'/data '+remote+'/figures'],check=True)
for f in ['live_resources.csv','live_rtt.csv']:
 subprocess.run(['scp',str(R/'data'/f),'aura-ubuntu:'+remote+'/data/'+f],check=True,capture_output=True)
script=Path(__file__).parent/'ubuntu_charts.py';shutil.copy2(script,R/'tools/ubuntu_charts.py')
subprocess.run(['scp',str(script),'aura-ubuntu:'+remote+'/ubuntu_charts.py'],check=True,capture_output=True)
cmd='docker run --rm --network none --read-only --tmpfs /tmp --cpus 2 --memory 2g -e MPLCONFIGDIR=/tmp/matplotlib -v '+remote+':/out --entrypoint /opt/vitis_ai/conda/envs/vitis-ai-pytorch/bin/python xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106 /out/ubuntu_charts.py'
r=subprocess.run(['ssh','aura-ubuntu',cmd],capture_output=True)
print(r.stdout.decode());print(r.stderr.decode()[-500:])
if r.returncode:sys.exit(r.returncode)
(R/'evidence/ubuntu_plot_receipt.json').write_bytes(r.stdout)
for stem in ['live_resources','live_network_rtt','live_vision_age']:
 for ext in ['png','svg']:
  subprocess.run(['scp','aura-ubuntu:'+remote+'/figures/'+stem+'.'+ext,str(R/'figures')],check=True,capture_output=True)
# Reuse the archived historical curves as exact images with their original captions.
src=Path(r'E:\Win共享文件\协作任务\2026-11-02_性能曲线与原生截图_01a19c53\性能曲线')
for n,stem in [('01','history_yunet'),('02','history_rates'),('05','history_sface_groups'),('07','history_sface_roc'),('09','history_model_latency'),('11','history_dialogue')]:
 for ext in ['png','svg']:
  p=next(src.glob(n+'_*.'+ext));shutil.copy2(p,R/'figures'/(stem+'.'+ext))
