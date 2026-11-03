import json,subprocess
from pathlib import Path
p=Path('/home/root/aura-bytetrack-20261011/update-ea926df36eb116cd')/'payload/board_apply.py'
result=subprocess.run(['python3','-B',str(p),'--phase','rollback'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
assert result.returncode==0,result.stdout
print(result.stdout)
