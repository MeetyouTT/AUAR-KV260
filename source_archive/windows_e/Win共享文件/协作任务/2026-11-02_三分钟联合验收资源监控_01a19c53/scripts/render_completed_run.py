"""Copy a finished numeric window and render on development Ubuntu only."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,shlex,sys,os

ROOT=Path(__file__).resolve().parent.parent
SHARED=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment/joint_acceptance_180s_20261102')
REMOTE='/home/ghmd/auar-resource-report-01a19c53'
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','aura-ubuntu']

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,**kw):
 r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=kw.pop('timeout',40),**kw)
 if r.returncode:raise RuntimeError('Command failed: '+str(args[0])+'\n'+r.stderr.decode(errors='replace')[-2200:])
 return r

def main():
 status=json.loads((ROOT/'RESOURCE_OBSERVER_STATUS.json').read_text(encoding='utf-8'))
 if status.get('collector_active') or status.get('phase')!='COLLECTED_WAIT_MAIN_WINDOW_SAMPLES':
  raise RuntimeError('Resource observation must complete normally before rendering')
 formal=ROOT/'data'/'acceptance_board_numeric.jsonl'
 records=[json.loads(x) for x in formal.read_text(encoding='utf-8').splitlines() if x.strip()]
 assert any(r.get('event')=='end' for r in records),'Missing resource end marker'
 assert sum(r.get('event')=='sample' for r in records)>=2,'Too few actual resource samples'
 functional=SHARED/'functional_events.jsonl'
 functional_status=json.loads((SHARED/'FUNCTIONAL_OBSERVER_STATUS.json').read_text(encoding='utf-8'))
 assert functional_status.get('phase')=='FINISHED','Main observer and Windows writer have not both closed'
 functions=[json.loads(x) for x in functional.read_text(encoding='utf-8').splitlines() if x.strip()]
 baseline=next((r for r in functions if r.get('event')=='BASELINE'),None)
 assert baseline and any(r.get('event')=='FINISHED' for r in functions),'Main window has not completed'
 start=next(r for r in records if r.get('event')=='start')
 assert start['boot_id']==baseline['boot_id'],'Different board boot IDs cannot share an axis'
 provenance=[]
 for source,target in [('functional_events.jsonl','main_functional_events.jsonl'),('windows_models.jsonl','main_windows_models.jsonl')]:
  src=SHARED/source
  if not src.is_file():continue
  raw=src.read_bytes();dest=ROOT/'data'/target;dest.write_bytes(raw)
  provenance.append({'source_path':str(src),'local_copy':'data/'+target,'sha256':digest(dest),'bytes':len(raw)})
 (ROOT/'data'/'MAIN_DATA_COPY_PROVENANCE.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
 prepare='from pathlib import Path\np=Path('+repr(REMOTE)+')\n(p/"data").mkdir(parents=True,exist_ok=True)\n(p/"figures").mkdir(exist_ok=True)\nprint(p)\n'
 run(SSH+['python3 -'],input=prepare.encode())
 renderer=ROOT/'scripts'/'generate_resource_figures.py'
 run(['scp','-q',str(renderer),'aura-ubuntu:'+REMOTE+'/generate_resource_figures.py'])
 names=['acceptance_board_numeric.jsonl','used_START_GATE.json','used_handoff_metadata.json','main_functional_events.jsonl','main_windows_models.jsonl','MAIN_DATA_COPY_PROVENANCE.json','MODEL_LAYOUT_EVIDENCE.json']
 copied=[ROOT/'data'/n for n in names if (ROOT/'data'/n).is_file()]
 run(['scp','-q',*[str(p) for p in copied],'aura-ubuntu:'+REMOTE+'/data/'])
 command=['docker','run','--rm','--network','none','--read-only','--tmpfs','/tmp','--cpus','2','--memory','2g','--user','1000:1000','-e','MPLCONFIGDIR=/tmp/matplotlib','-v',REMOTE+':/out','-v','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:/fonts/NotoSansCJK-Regular.ttc:ro','--entrypoint','/opt/vitis_ai/conda/envs/vitis-ai-pytorch/bin/python','xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106','/out/generate_resource_figures.py']
 script='import subprocess,json,hashlib\nfrom pathlib import Path\nfrom datetime import datetime,timezone\np=Path('+repr(REMOTE)+')\ncommand='+repr(command)+'\nr=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240)\n(p/"plot_stdout.log").write_bytes(r.stdout)\n(p/"plot_stderr.log").write_bytes(r.stderr)\nreceipt={"utc":datetime.now(timezone.utc).isoformat(),"exit_code":r.returncode,"command":command,"renderer_sha256":hashlib.sha256((p/"generate_resource_figures.py").read_bytes()).hexdigest(),"board_accessed_for_plotting":False,"model_inference_triggered":False}\n(p/"RENDER_RECEIPT.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")\nprint(r.stdout.decode(errors="replace"));print(r.stderr.decode(errors="replace")[-1800:]);raise SystemExit(r.returncode)\n'
 plotted=run(SSH+['python3 -'],input=script.encode(),timeout=270)
 print(plotted.stdout.decode('utf-8',errors='replace'))
 run(['scp','-q','-r','aura-ubuntu:'+REMOTE+'/figures/.',str(ROOT/'figures')],timeout=90)
 for name in ['RESOURCE_SUMMARY.json','资源采样汇总.csv','DPU任务频率.csv']:
  run(['scp','-q','aura-ubuntu:'+REMOTE+'/data/'+name,str(ROOT/'data'/name)])
 for name in ['FIGURE_SOURCES.json','RENDER_RECEIPT.json','plot_stdout.log','plot_stderr.log']:
  run(['scp','-q','aura-ubuntu:'+REMOTE+'/'+name,str(ROOT/name)])
 sources=json.loads((ROOT/'FIGURE_SOURCES.json').read_text(encoding='utf-8'))
 for figure,filename in [('14_本轮对话软件计时','本轮对话软件计时.csv'),('15_头像界面软件帧计数速率','头像软件帧计数速率.csv')]:
  if any(r['name']==figure for r in sources['figures']):run(['scp','-q','aura-ubuntu:'+REMOTE+'/data/'+filename,str(ROOT/'data'/filename)])
 print(json.dumps({'render_completed':True,'figures':len(list((ROOT/'figures').glob('*.png'))),'board_controls':0,'output':str(ROOT)},ensure_ascii=False))

if __name__=='__main__':main()
