CONTROLLER='/home/root/aura-post-power-20261022/helpers/474b8ce39ba29123/source.py'
PIN='474b8ce39ba291233d23c25a2581d773b7b99809f9f1c37df5263789138d2221'
import hashlib,json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
assert hashlib.sha256(Path(CONTROLLER).read_bytes()).hexdigest()==PIN
out=subprocess.check_output(['/usr/bin/python3','-B',CONTROLLER,'--launch-once','--boot','89d53e38-4726-4c94-b958-53f2dfb3bd4e','--camera-pid','1291'],text=True,timeout=12)
print(json.dumps(json.loads(out)))
