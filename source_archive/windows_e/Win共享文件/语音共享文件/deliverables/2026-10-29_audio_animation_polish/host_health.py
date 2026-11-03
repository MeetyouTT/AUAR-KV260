import json,socket,sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parents[1]/'aura'))
from common import portrait_wire as wire
def check():
    with socket.create_connection(('192.168.50.1',8796),timeout=2) as connection:
        wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'});v,data=wire.receive(connection,0)
    expected=json.loads((H/'snapshot_verification.json').read_text())['revision']
    assert not data and v['ready'] and v['revision']==expected and v['width']==423 and v['height']==438
    return v
if __name__=='__main__':
    try:print(json.dumps(check()))
    except (OSError,EOFError,ValueError,KeyError,AssertionError):
        if '--quiet' in sys.argv:raise SystemExit(2)
        raise
