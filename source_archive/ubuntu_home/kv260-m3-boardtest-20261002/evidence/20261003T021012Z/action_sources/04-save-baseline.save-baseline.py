import hashlib
from pathlib import Path
p=Path('/home/root/kv260-zocl-repair-20261003T005805Z/baseline/board_guard.py')
G=p.read_bytes()
assert hashlib.sha256(G).hexdigest()=='99c1fc5c842a026c05531eb637080717e44aaa199220d8ab942fbfe430814a6e','Guard source changed'
exec(compile(G,str(p),'exec'))
WORK=Path('/home/root/kv260-m3-boardtest-20261003T021012Z')
guard('0991D1B457855C8987936E6','kv260-benchmark-b4096')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
assert not Path('/lib/firmware/xilinx/kv260-benchmark-b4096-m3').exists()
WORK.mkdir(exist_ok=False);b=WORK/'baseline';b.mkdir()
for src,name in [('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko','original-zocl.ko'),('/proc/config.gz','config.gz'),('/etc/vart.conf','vart.conf'),('/sys/firmware/fdt','boot-fdt.dtb')]:
 (b/name).write_bytes(Path(src).read_bytes())
(b/'guard_reference.py').write_bytes(G)
(b/'runtime-hashes.json').write_text('{"/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification": "322dd07736f409cba02416782475c0dc2b5951435ddbb6d0671d3cda8fac0c0e", "/home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification": "b9f52e4fd21d6526a8ac1e73b6e839b28308368451c4bb30e845a9f96343f1b4", "/home/root/kv260-test-20261001/baseline-backup/baseline-files.tar.gz": "964c04afac0d7de7e36b78d6bdd87f5f4a656bb47b3b7e1a7169510f5dfaa371", "/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg": "f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a", "/home/root/kv260-test-20261001/samoyed.list": "bf02d74370fbfdd8d008c7916109a14be3a5b33bd6057522fbb14e95ac2e9caa", "/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.bit.bin": "7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f", "/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.dtbo": "36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35", "/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin": "fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac", "/lib/firmware/xilinx/kv260-benchmark-b4096/shell.json": "2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777", "/usr/share/vitis_ai_library/models/resnet18/resnet18.prototxt": "691c393b15ae87976060a125067534334bd034c3a5193a96f6f5db3f4da3729c", "/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel": "4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef"}')
(b/'dmesg-before.output').write_bytes(subprocess.check_output(['dmesg']))
(b/'state.json').write_text(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'parameters':PARAMS,'active':active_packages(),'uptime':Path('/proc/uptime').read_text().strip()},indent=2))
candidate=Path('/home/root/kv260-zocl-repair-20261003T005805Z/candidate-stage/zocl.ko')
assert digest(candidate)=='5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412'
(WORK/'repaired-zocl.ko').write_bytes(candidate.read_bytes())
assert digest(WORK/'repaired-zocl.ko')=='5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412'
print(json.dumps({'backup':str(b),'original_module_sha256':digest(b/'original-zocl.ko'),'candidate_sha256':digest(WORK/'repaired-zocl.ko')},indent=2))
