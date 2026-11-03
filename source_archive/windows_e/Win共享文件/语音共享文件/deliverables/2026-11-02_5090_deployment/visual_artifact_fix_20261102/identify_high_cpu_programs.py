import json,hashlib,os
from pathlib import Path
rows=[]
for pid in (394769,394740,418429):
 p=Path('/proc')/str(pid)
 if not p.is_dir():continue
 cmd=p.joinpath('cmdline').read_bytes();args=[v.decode(errors='replace') for v in cmd.rstrip(b'\0').split(b'\0')];paths=[]
 for v in args:
  q=Path(v)
  if v.startswith(('/home/root/','/usr/bin/','/bin/')) and q.suffix in ('.py','.so') and q.is_file():paths.append(v)
 rows.append({'pid':pid,'exe':str(p.joinpath('exe').resolve()),'command_sha256':hashlib.sha256(cmd).hexdigest(),'public_program_paths':paths,'argument_count':len(args),'public_flag_names':[v for v in args if v.startswith('--') and '=' not in v and len(v)<80]})
print(json.dumps({'read_only':True,'programs':rows,'raw_arguments_or_private_data_exported':False}))
