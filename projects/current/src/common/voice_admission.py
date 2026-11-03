"""Short, cancellation-aware turn handoff; bounded RAM diagnostics contain no speech."""
from collections import Counter,deque
import select
import socket
import threading
import time

MAX_WAIT_SECONDS=5.0
POLL_SECONDS=.025

def disconnected(connection):
    try:
        if not select.select([connection],[],[],0)[0]:return False
        return not connection.recv(1,socket.MSG_PEEK)
    except (OSError,ValueError):return True

def acquire_turn(lock,connection,deadline,*,max_wait=MAX_WAIT_SECONDS,poll=POLL_SECONDS):
    """Never preempt another owner or replay a request; retain the original deadline."""
    began=time.monotonic();until=min(deadline,began+max_wait)
    while True:
        if disconnected(connection):return 'cancelled',(time.monotonic()-began)*1000
        now=time.monotonic()
        if now>=deadline:return 'expired',(now-began)*1000
        if lock.acquire(blocking=False):
            if disconnected(connection) or time.monotonic()>=deadline:
                lock.release()
                return ('cancelled' if disconnected(connection) else 'expired'),(time.monotonic()-began)*1000
            return 'acquired',(time.monotonic()-began)*1000
        remaining=until-time.monotonic()
        if remaining<=0:return ('expired' if time.monotonic()>=deadline else 'busy'),(time.monotonic()-began)*1000
        # Event.wait avoids spinning while still detecting a closed peer promptly.
        threading.Event().wait(min(poll,remaining))

class RequestDiagnostics:
    def __init__(self):
        self.lock=threading.Lock();self.counts=Counter();self.recent=deque(maxlen=16)
    def record(self,meta,outcome,*,entry='',characters=None,wait_ms=None):
        row={'request_id':meta['request_id'],'generation':meta['generation'],
             'outcome':outcome,'entry':entry,'at':time.monotonic()}
        if characters is not None:row['recognized_characters']=characters
        if wait_ms is not None:row['admission_wait_ms']=round(wait_ms,2)
        with self.lock:
            self.counts[outcome]+=1;self.recent.append(row)
    def public(self):
        with self.lock:
            now=time.monotonic()
            rows=[{**{k:v for k,v in row.items() if k!='at'},'age_seconds':round(now-row['at'],2)} for row in self.recent]
            return {'version':1,'admission_wait_max_ms':int(MAX_WAIT_SECONDS*1000),
                    'speech_stored':False,'scope':'bounded_process_ram','counts':dict(self.counts),'recent':rows}
