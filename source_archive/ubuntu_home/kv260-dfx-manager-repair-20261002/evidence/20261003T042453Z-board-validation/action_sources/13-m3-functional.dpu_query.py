import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042453Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2052fe46637f6a7c5f5a67ecdc46439e849057b4a75aad4d1ccbf2ed74d38b37'
exec(compile(s,str(p),'exec'))
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096-m3');manager_guard(True)
subprocess.run(['env','XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin','xdputil','query'],check=True)
