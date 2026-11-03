"""Stop the currently recorded owned fixture only after PID-creation validation."""
from pathlib import Path
import datetime,json,os
from fixture_identity import terminate_verified

ab=Path(__file__).parent
state=json.loads((ab/'isolated-host-state.json').read_text(encoding='utf-8'))
script=ab/'isolated_portrait_server.py'
assert os.path.normcase(str(script)) in [os.path.normcase(x) for x in state['command']]
assert str(ab/'windows_fixture') in state['ready_file']
assert state['identity']['pid']==state['pid']
assert os.path.normcase(state['identity']['executable'])==os.path.normcase(state['command'][0])
ready_path=Path(state['ready_file'])
if ready_path.exists():
    ready=json.loads(ready_path.read_text());assert ready['pid']==state['pid']
    assert ready['isolated_port'] not in (8796,ready['production_port'])
result=terminate_verified(state['identity'])
result.update(at_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),production_stopped=False,
              ready_file=str(ready_path),scope='independently launched character benchmark portrait fixture only')
target=ab/('fixture-cleanup-'+str(state['identity']['creation_filetime'])+'.json')
target.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
