import subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='f7a3ff07-fc20-4804-af12-c314a7a1847a'
raise SystemExit(subprocess.run(['python3','-B','/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked/load.py'],timeout=120).returncode)
