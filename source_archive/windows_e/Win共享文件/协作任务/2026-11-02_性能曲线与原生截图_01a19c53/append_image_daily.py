from pathlib import Path
from hashlib import sha256
import json
p=Path('/home/ghmd/Win共享文件/协作任务/2026-11-02_性能曲线与原生截图_01a19c53')
r=json.loads((p/'IMAGE_PACKAGE_RECEIPT.json').read_text(encoding='utf-8'))
z=p/'性能曲线与原生截图_可插入报告.zip'
assert sha256(z.read_bytes()).hexdigest()==r['sha256']
entry=(p/'ubuntu_image_daily_entry.txt').read_text(encoding='utf-8')
daily=Path('/home/ghmd/AMD_Smart/logs/daily/2026-11-02.md')
marker='## Windows对话：按验证报告形式交付性能曲线与原生截图'
if marker not in daily.read_text(encoding='utf-8'):
    with daily.open('a',encoding='utf-8') as f:f.write(entry)
    state='appended'
else:state='already_present'
print(json.dumps({'remote_sha256_verified':r['sha256'],'bytes':z.stat().st_size,'daily_log':state}))
