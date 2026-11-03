import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042210Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2bba8ba30eb7f559edbf337aeaabc4c6e1a04ff5c988fbc6872fc36974fa9b2d'
exec(compile(s,str(p),'exec'))
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096-m3');manager_guard(True)
subprocess.run(['env','XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin','/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification','resnet18','/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'],cwd='/home/root/kv260-test-20261001',check=True)
