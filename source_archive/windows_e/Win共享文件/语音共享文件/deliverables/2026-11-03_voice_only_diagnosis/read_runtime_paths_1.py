import hashlib,json,shlex,subprocess
from pathlib import Path
OWNER={'pid': 1119898, 'birth_ticks': '7691820', 'command_sha256': 'f99580c6e8ff6bc8eb8c15852b4f4e09c6d17155458707766ebcf6335ba4f6b7'}
path=Path('/proc')/str(OWNER['pid'])
assert path.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==OWNER['birth_ticks']
assert hashlib.sha256(path.joinpath('cmdline').read_bytes()).hexdigest()==OWNER['command_sha256']
values=[row.partition(b'=')[2].decode('utf-8') for row in path.joinpath('environ').read_bytes().split(b'\0') if row.startswith(b'PYTHONPATH=')]
result=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=Environment','--value'],capture_output=True,text=True,timeout=4)
assert result.returncode==0
unit_paths=[row.partition('=')[2] for row in shlex.split(result.stdout) if row.startswith('PYTHONPATH=')]
print(json.dumps(dict(schema='aura-verified-current-GUI-public-python-paths-1',pythonpath=values,unit_pythonpath=unit_paths,controls=0)))
