"""Local page-change channel. A hide ACK follows GTK unmapping, not polling."""
import fcntl,json,os,socket,stat,threading,time,uuid
from pathlib import Path

ADDRESS='/run/aura-face-zone-visibility-v1.sock'
STATUS='/run/aura-face-zone-last-page.json'

def identity():
    return {'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'pid':os.getpid(),'birth':int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])}

class PageGate:
    def __init__(self,boot):
        self.boot=boot;self.page=None;self.owner_birth=-1;self.owner_pid=None;self.sequence=-1;self.revision=0;self.lock=threading.Lock()
    def accept(self,value):
        if (not isinstance(value,dict) or value.get('version')!=1 or value.get('boot')!=self.boot
                or type(value.get('pid')) is not int or type(value.get('birth')) is not int
                or value['pid']<=0 or value['birth']<0
                or type(value.get('sequence')) is not int or value['sequence']<0
                or not isinstance(value.get('request'),str) or not 1<=len(value['request'])<=64
                or not isinstance(value.get('page'),str) or len(value['page'])>32):return None
        with self.lock:
            birth,pid,seq=value['birth'],value['pid'],value['sequence']
            if birth<self.owner_birth:return None
            if birth==self.owner_birth and (pid!=self.owner_pid or seq<=self.sequence):return None
            self.owner_birth,self.owner_pid,self.sequence=birth,pid,seq;self.page=value['page'];self.revision+=1
            return self.revision
    def snapshot(self):
        with self.lock:return {'page':self.page,'revision':self.revision,'sequence':self.sequence,'owner_pid':self.owner_pid}
    def allows_overlay(self):
        with self.lock:return self.page in (None,'vision')

class VisibilityClient:
    def __init__(self,address=ADDRESS,status_path=STATUS,who=None,timeout=.200):
        self.address=address;self.status_path=status_path;self.who=who or identity();self.sequence=0;self.timeout=timeout
    def send(self,page,wait=True):
        self.sequence+=1;packet=dict(self.who,version=1,page=page,sequence=self.sequence,request=uuid.uuid4().hex)
        began=time.monotonic();ok=False
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.timeout);sock.bind('\0aura-nav-'+packet['request'])
                sock.sendto(json.dumps(packet,separators=(',',':')).encode(),self.address)
                if wait:
                    answer=json.loads(sock.recv(2048));ok=answer.get('request')==packet['request'] and answer.get('applied') is True
                else:ok=True
        except (OSError,ValueError):pass
        result={'page':page,'sequence':self.sequence,'acknowledged':ok,'waited_for_hide':wait,
                'elapsed_ms':round((time.monotonic()-began)*1000,3),'gui_pid':self.who['pid'],'boot':self.who['boot']}
        if self.status_path:
            path=Path(self.status_path);temp=path.with_name(path.name+'.'+str(os.getpid()))
            try:temp.write_text(json.dumps(result)+'\n');os.replace(temp,path)
            except OSError:pass
        return result

_client=None
def before_page_change(page):
    global _client
    if _client is None:_client=VisibilityClient()
    if page!='vision':return _client.send(page,wait=True)
def after_page_change(page):
    global _client
    if _client is None:_client=VisibilityClient()
    if page=='vision':return _client.send(page,wait=False)

class VisibilityServer:
    def __init__(self,dispatch,apply,address=ADDRESS,boot=None):
        self.address=address;self.dispatch=dispatch;self.apply=apply;self.gate=PageGate(boot or identity()['boot']);self.closed=threading.Event()
        self.lock_file=open(address+'.lock','a+');fcntl.flock(self.lock_file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=Path(address)
        if path.exists():
            if not stat.S_ISSOCK(path.lstat().st_mode):raise RuntimeError('Visibility path is not a socket')
            path.unlink()
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);self.sock.bind(address);os.chmod(address,0o600);self.sock.settimeout(.2)
        self.inode=path.lstat().st_ino;self.last_delivery={};self.thread=threading.Thread(target=self.receive,name='face-zone-page-events',daemon=True);self.thread.start()
    def receive(self):
        while not self.closed.is_set():
            try:
                raw,peer=self.sock.recvfrom(2048);packet=json.loads(raw);revision=self.gate.accept(packet)
                if revision is not None:packet['_received_at']=time.monotonic()
                if revision is not None:self.dispatch(self.deliver,revision,packet,peer)
            except socket.timeout:continue
            except (OSError,ValueError,TypeError):continue
    def deliver(self,revision,packet,peer):
        applied=False;started=time.monotonic();error=None
        if not self.closed.is_set() and self.gate.snapshot()['revision']==revision:
            self.apply(packet['page']);applied=True
        finished=time.monotonic()
        try:self.sock.sendto(json.dumps({'request':packet['request'],'applied':applied}).encode(),peer)
        except OSError as e:error=e.errno
        self.last_delivery={'page':packet['page'],'sequence':packet['sequence'],'applied':applied,'queue_ms':round((started-packet['_received_at'])*1000,3),'apply_ms':round((finished-started)*1000,3),'ack_error':error}
        return False
    def close(self):
        self.closed.set();self.sock.close();self.thread.join(.4)
        p=Path(self.address)
        if p.exists() and p.lstat().st_ino==self.inode:p.unlink()
        self.lock_file.close()
