from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import json

task=Path('/home/ghmd/Win共享文件/协作任务/2026-11-02_全套性能表与材料清单_01a19c53')
receipt=json.loads((task/'PACKAGE_RECEIPT.json').read_text(encoding='utf-8'))
package=task/'技术文档性能表与图像材料包.zip'
actual=sha256(package.read_bytes()).hexdigest()
assert actual==receipt['sha256']
with ZipFile(package) as z:
    assert z.testzip() is None
    for name in ['技术文档材料清单与性能表.xlsx','材料使用说明.txt']:
        assert (task/name).read_bytes()==z.read(name)
entry=(task/'ubuntu_daily_entry.txt').read_text(encoding='utf-8')
daily=Path('/home/ghmd/AMD_Smart/logs/daily/2026-11-02.md')
marker='## Windows对话：全套性能表、模板材料清单与Vitis AI模型核查'
if marker not in daily.read_text(encoding='utf-8'):
    with daily.open('a',encoding='utf-8') as f:f.write(entry)
    result='appended'
else:result='already_present'
proof={'remote_package_sha256':actual,'remote_package_bytes':package.stat().st_size,'xlsx_and_guide_match_zip':True,'daily_log':result}
(task/'REMOTE_DELIVERY_VERIFIED.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(proof,ensure_ascii=False))
