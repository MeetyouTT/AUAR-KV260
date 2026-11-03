"""Read the sleep state and preserve the unpowered observation as invalid baseline."""
import json,subprocess
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
root=Path('/run/aura-hdmi-physical-hotplug-20261021')/boot
if root.exists() and not (root/'result.json').exists():
 (root/'finish').write_text('Baseline output was disabled/DPMS Off; no physical HDMI action requested.\n')
v={'boot_id':boot,'xset':subprocess.run(['env','DISPLAY=:0','xset','q'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5).stdout,'display_control_writes':0}
v['clock_rows']=[s.strip() for s in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines() if s.split() and s.split()[0] in ['dp_video_ref','dpdma_ref','dp_aclk']]
v['drm_state']=Path('/sys/kernel/debug/dri/0/state').read_text()
print(json.dumps(v),flush=True)
