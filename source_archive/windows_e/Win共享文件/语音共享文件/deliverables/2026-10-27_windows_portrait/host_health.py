import json,socket,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'aura'))
from common import portrait_wire as wire
def check():
    with socket.create_connection(('192.168.50.1',8796),timeout=2) as connection:
        wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'});value,data=wire.receive(connection,0)
    assert not data and value['ready'] and value['revision']==json.loads((HERE/'snapshot_verification.json').read_text(encoding='utf-8'))['revision']
    print(json.dumps(value))
if __name__=='__main__':
    try:check()
    except (OSError,EOFError,ValueError,KeyError,AssertionError):
        if '--quiet' in sys.argv:raise SystemExit(2)
        raise
