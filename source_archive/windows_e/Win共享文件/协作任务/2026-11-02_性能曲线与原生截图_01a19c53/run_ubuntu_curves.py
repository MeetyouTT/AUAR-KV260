from pathlib import Path
import subprocess,json,hashlib
from datetime import datetime,timezone

root=Path('/home/ghmd/Win共享文件/协作任务/2026-11-02_性能曲线与原生截图_01a19c53')
command=['docker','run','--rm','--network','none','--read-only','--tmpfs','/tmp','--cpus','2','--memory','2g',
 '-e','MPLCONFIGDIR=/tmp/matplotlib',
 '-v',str(root)+':/out',
 '-v','/home/ghmd/aura-dpu-vision-20261021/work/public-faces:/public:ro',
 '-v','/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_live_baseline/evidence:/evidence:ro',
 '-v','/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start/evidence:/public_report:ro',
 '-v','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:/fonts/NotoSansCJK-Regular.ttc:ro',
 '--entrypoint','/opt/vitis_ai/conda/envs/vitis-ai-pytorch/bin/python',
 'xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106','/out/generate_curves.py']
run=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240)
(root/'ubuntu_plot_stdout.json').write_bytes(run.stdout)
(root/'ubuntu_plot_stderr.log').write_bytes(run.stderr)
receipt={'utc':datetime.now(timezone.utc).isoformat(),'command':command,'exit_code':run.returncode,'script_sha256':hashlib.sha256((root/'generate_curves.py').read_bytes()).hexdigest(),'board_accessed':False,'new_model_inference':False}
(root/'UBUNTU_CURVE_RUN_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False));print(run.stdout.decode('utf-8',errors='replace'));print(run.stderr.decode('utf-8',errors='replace')[-2500:])
raise SystemExit(run.returncode)
