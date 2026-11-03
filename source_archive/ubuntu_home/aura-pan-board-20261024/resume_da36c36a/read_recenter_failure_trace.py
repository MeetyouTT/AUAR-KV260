import json
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v11r1')
p=F/'runs/ui-43494385970069/trial.json';d=json.loads(p.read_text());r=d.get('result') or {}
rows=[]
for n in ('/sys/kernel/debug/clk/clk_summary','/sys/kernel/debug/clk/clk_dump'):
 try:
  for x in Path(n).read_text().splitlines():
   if any(k in x.lower() for k in ('fclk0','s_axi_aclk','aura_m3','pl0_ref','clk_wiz')):rows.append(x.strip())
 except OSError:pass
print(json.dumps({'report_path':str(p),'status':d['status'],'result':{k:r.get(k) for k in ('reason','fatal','pulse_us','elapsed_s','commands_accepted','motion_target_changes','segments','events','command_trace','stopped')},
 'control_parameters':d.get('control_parameters'),'input_summary':d.get('input_summary'),'clock_rows':rows[:80]},ensure_ascii=False))
