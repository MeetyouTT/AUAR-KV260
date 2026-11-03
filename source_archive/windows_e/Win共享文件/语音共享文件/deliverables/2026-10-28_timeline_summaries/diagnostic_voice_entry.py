"""One startup stack trace per 90s; cancel as soon as the real r2 is ready."""
import faulthandler,http.client,json,runpy,sys,threading,time
from pathlib import Path
H=Path(__file__).resolve().parent
assert sys.argv[1]=='--script';script=Path(sys.argv[2]);sys.argv=[str(script)]+sys.argv[3:]
output=(H/'voice_startup_stacks.log').open('a',encoding='utf-8')
faulthandler.dump_traceback_later(90,repeat=True,file=output)
stop=threading.Event()
def monitor():
    until=time.monotonic()+330
    while not stop.wait(2) and time.monotonic()<until:
        connection=http.client.HTTPConnection('192.168.50.1',8792,timeout=1)
        try:
            connection.request('GET','/health');response=connection.getresponse();health=json.loads(response.read())
            if health.get('ready') and health.get('service_revision')=='voice-timeline-20261028-r2':
                faulthandler.cancel_dump_traceback_later();return
        except (OSError,ValueError,http.client.HTTPException):pass
        finally:connection.close()
threading.Thread(target=monitor,name='startup-stack-watch',daemon=True).start()
try:runpy.run_path(str(script),run_name='__main__')
finally:stop.set();faulthandler.cancel_dump_traceback_later();output.close()
