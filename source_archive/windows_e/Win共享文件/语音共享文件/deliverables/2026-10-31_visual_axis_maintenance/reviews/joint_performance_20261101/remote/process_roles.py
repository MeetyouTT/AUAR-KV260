"""Classify observed children without exporting full arguments or environment."""
import re
current_guard()
v=get_json(8783,'/api/state');safe=assert_safe(v)
rows=[]
for pid in (430894,496785,496789,496791,496818,496871,574018):
    path=Path('/proc')/str(pid)
    try:
        argv=(path/'cmdline').read_bytes().decode('utf-8','replace').split('\0')
        scripts=[Path(arg).name for arg in argv[:8] if arg.startswith('/home/root/') and re.fullmatch('[A-Za-z0-9_.-]+[.]py',Path(arg).name)]
        kind='other'
        for name in ('multiprocessing.resource_tracker','multiprocessing.spawn','multiprocessing.forkserver'):
            if any(arg.startswith('from '+name+' import ') for arg in argv):kind=name
        rows.append(dict(fingerprint=fingerprint(pid),executable=Path(argv[0]).name,script_basenames=scripts,
                         python_subprocess_kind=kind))
    except OSError:rows.append(dict(pid=pid,available=False))
print(json.dumps(dict(state=safe,processes=rows,full_argv_or_environment_exported=False)))
