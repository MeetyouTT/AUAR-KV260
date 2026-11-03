import os;from pathlib import Path;assert os.uname().machine=='aarch64';assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100';assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='4365d744-ddef-4325-a264-e7bb57cc9bb8';
import subprocess,json
release='/home/root/aura-realtime-vision-20261007/releases/68bd0def762cc3cf'
for command in [["python3","-m","unittest","-v","test_motion_service.py","test_vision_core.py"],["python3","motion_replay.py"],["python3","realtime_vision.py","--preflight"]]:
 p=subprocess.run(command,cwd=release,capture_output=True,text=True,timeout=35)
 print(p.stdout+p.stderr)
 assert p.returncode==0
