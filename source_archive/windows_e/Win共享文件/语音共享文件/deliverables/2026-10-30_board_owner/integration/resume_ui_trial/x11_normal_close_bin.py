"""Inspect one proven GTK top-level owner; optionally request WM_DELETE_WINDOW.

Default is read-only X11/proc/systemd metadata inspection. The only optional
mutation is one normal WM_DELETE_WINDOW ClientMessage to the reviewed window.
No process signal, XDestroyWindow, service action, keyboard or pointer event.
"""
import argparse
import ctypes as C
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time

ORIGINAL = '/home/root/aura-board-vision-20261030/06391079cfddb734-r3-ubuntu'
CANDIDATE = '/home/root/aura-board-owner-candidate-20261030'
UNIT = 'aura-avatar-ui.service'
LAUNCHER_SHA = '5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03'
I, U, L, UL, P = C.c_int32, C.c_uint32, C.c_int64, C.c_uint64, C.c_void_p


class Data(C.Union):
    _fields_ = [('b', C.c_char*20), ('s', C.c_int16*10), ('l', L*5)]


class ClientMessage(C.Structure):
    _fields_ = [('type',I),('serial',UL),('send_event',I),('display',P),
                ('window',UL),('message_type',UL),('format',I),('data',Data)]


class Event(C.Union):
    _fields_ = [('xclient',ClientMessage),('pad',L*24)]


class Attributes(C.Structure):
    _fields_ = [(k,I) for k in ('x','y','width','height','border_width','depth')]+[
        ('visual',P),('root',UL),('window_class',I),('bit_gravity',I),('win_gravity',I),('backing_store',I),
        ('backing_planes',UL),('backing_pixel',UL),('save_under',I),('colormap',UL),('map_installed',I),
        ('map_state',I),('all_event_masks',L),('your_event_mask',L),('do_not_propagate_mask',L),
        ('override_redirect',I),('screen',P)]


class ErrorEvent(C.Structure):
    _fields_ = [('type',I),('display',P),('resourceid',UL),('serial',UL),
                ('error_code',C.c_ubyte),('request_code',C.c_ubyte),('minor_code',C.c_ubyte)]


class Refused(ValueError):
    pass


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def allowed_path(path):
    value = PurePosixPath(path)
    return (value.is_absolute() and '..' not in value.parts and
            (value.is_relative_to(ORIGINAL) or value.is_relative_to(CANDIDATE)))


def load_plan(path, expected):
    raw = Path(path).read_bytes()
    if len(raw)>262144 or sha(raw)!=expected: raise Refused('plan_fingerprint')
    value = json.loads(raw)
    if (value.get('schema_version')!=1 or value.get('display')!=':0' or
            value.get('unit')!=UNIT or value.get('supervisor',{}).get('pid')!=1296):
        raise Refused('plan_schema')
    for owner in (value['owner'],value['supervisor']):
        argv=owner['argv']
        if (type(owner['pid']) is not int or owner['pid']<2 or
                not re.fullmatch(r'[0-9]+',owner['birth']) or
                not re.fullmatch(r'[0-9a-f]{64}',owner['cmdline_sha256']) or
                len(argv)<3 or argv[:2]!=['/usr/bin/python3','-B'] or not allowed_path(argv[2]) or
                sha(('\0'.join(argv)+'\0').encode())!=owner['cmdline_sha256']):
            raise Refused('owner_plan')
    script=value['owner']['argv'][2]
    if script.startswith(ORIGINAL+'/') and script!=ORIGINAL+'/runtime/aura/tools/board_avatar_pan.py':
        raise Refused('original_entry')
    if script.startswith(CANDIDATE+'/') and not script.endswith(('/aura/tools/board_avatar_gtk.py','/aura/tools/board_avatar_pan.py')):
        raise Refused('candidate_entry')
    if (value['supervisor']['argv'][2]!=ORIGINAL+'/startup/launcher.py' or
            value['sources'].get(ORIGINAL+'/startup/launcher.py')!=LAUNCHER_SHA or
            script not in value['sources'] or not 2<=len(value['sources'])<=512):
        raise Refused('source_plan')
    if any(not allowed_path(k) or not re.fullmatch(r'[0-9a-f]{64}',v) for k,v in value['sources'].items()):
        raise Refused('source_plan')
    return value


class HostProof:
    def process(self,pid):
        root=Path('/proc')/str(pid)
        try:
            stat=root.joinpath('stat').read_text()
            raw=root.joinpath('cmdline').read_bytes()
        except FileNotFoundError: return None
        fields=stat.rsplit(')',1)[1].split()
        if fields[0]=='Z': return None
        if not raw or len(raw)>1048576 or not raw.endswith(b'\0'): raise Refused('process_cmdline')
        return dict(pid=pid,birth=fields[19],cmdline_sha256=sha(raw),ppid=int(fields[1]))

    def static(self,plan):
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if boot!=plan['boot_id']: raise Refused('boot_changed')
        total=0
        for name,expected in plan['sources'].items():
            path=Path(name)
            if path.is_symlink() or path.resolve(strict=True)!=path or not path.is_file(): raise Refused('source_path')
            size=path.stat().st_size; total+=size
            if size>16777216 or total>67108864 or sha(path.read_bytes())!=expected: raise Refused('source_changed')
        command=['/bin/systemctl','show',UNIT,'--no-pager',
                 '--property=MainPID,Restart,SendSIGKILL,TimeoutStopUSec,Job']
        result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                              timeout=3,check=False,text=True)
        if result.returncode or len(result.stdout)>65536: raise Refused('unit_read')
        props=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
        if props.get('MainPID') not in ('0','1296') or props.get('Job',''): raise Refused('unit_owner_or_job')
        if props['MainPID']=='1296': self.verify_owner(plan['supervisor'])
        return dict(boot_id=boot,sources_sha256=sha(canonical(plan['sources'])),unit=props)

    def verify_owner(self,expected):
        actual=self.process(expected['pid'])
        if actual is None or any(actual[k]!=expected[k] for k in ('pid','birth','cmdline_sha256')):
            raise Refused('owner_changed')
        if 'parent_pid' in expected and actual['ppid']!=expected['parent_pid']: raise Refused('parent_changed')
        return {k:actual[k] for k in ('pid','birth','cmdline_sha256')}


def guarded(proof):
    unit=proof['unit']
    return (unit.get('Restart')=='no' and unit.get('SendSIGKILL')=='no' and
            unit.get('TimeoutStopUSec')=='infinity' and unit.get('MainPID') in ('0','1296') and
            not unit.get('Job',''))


class X11:
    def __init__(self,display):
        if sys.platform!='linux' or C.sizeof(C.c_long)!=8 or C.sizeof(P)!=8: raise Refused('linux_lp64_required')
        self.lib=C.CDLL('libX11.so.6'); self.display=None; self.error=0; self.atoms={}
        declarations={
            'XOpenDisplay':(P,[C.c_char_p]),'XCloseDisplay':(I,[P]),'XDefaultRootWindow':(UL,[P]),
            'XInternAtom':(UL,[P,C.c_char_p,I]),'XFree':(I,[P]),'XSync':(I,[P,I]),
            'XGetWindowAttributes':(I,[P,UL,C.POINTER(Attributes)]),
            'XGetWindowProperty':(I,[P,UL,UL,L,L,I,UL,C.POINTER(UL),C.POINTER(I),C.POINTER(UL),C.POINTER(UL),C.POINTER(P)]),
            'XQueryTree':(I,[P,UL,C.POINTER(UL),C.POINTER(UL),C.POINTER(C.POINTER(UL)),C.POINTER(U)]),
            'XSendEvent':(I,[P,UL,I,L,C.POINTER(Event)]),'XSetErrorHandler':(P,[P])}
        for name,(result,args) in declarations.items():
            fn=getattr(self.lib,name);fn.restype=result;fn.argtypes=args
        self.callback=C.CFUNCTYPE(I,P,C.POINTER(ErrorEvent))(self._error)
        self.previous=self.lib.XSetErrorHandler(C.cast(self.callback,P))
        self.display=self.lib.XOpenDisplay(display.encode())
        if not self.display: self.close(); raise Refused('display_unavailable')
        self.root=self.lib.XDefaultRootWindow(self.display)

    def _error(self,display,event): self.error=int(event.contents.error_code); return 0
    def sync(self):
        self.lib.XSync(self.display,0)
        if self.error: raise Refused('x11_window_changed')
    def atom(self,name):
        if name not in self.atoms:
            # only_if_exists: default inspect never creates an X atom.
            self.atoms[name]=int(self.lib.XInternAtom(self.display,name.encode(),1))
        return self.atoms[name]
    def property(self,window,name,kind,maximum=4096):
        atom=self.atom(name)
        if not atom: return None
        actual=UL();fmt=I();count=UL();remaining=UL();data=P()
        status=self.lib.XGetWindowProperty(self.display,window,atom,0,(maximum+3)//4,0,0,
            C.byref(actual),C.byref(fmt),C.byref(count),C.byref(remaining),C.byref(data))
        try:
            self.sync()
            if status or remaining.value: raise Refused('x11_property_bound')
            if actual.value==0: return None
            expected={'_NET_CLIENT_LIST':('WINDOW',),'WM_TRANSIENT_FOR':('WINDOW',),
                '_NET_WM_PID':('CARDINAL',),'_NET_WM_WINDOW_TYPE':('ATOM',),
                'WM_PROTOCOLS':('ATOM',),'_NET_WM_NAME':('UTF8_STRING',),
                'WM_NAME':('STRING','COMPOUND_TEXT','UTF8_STRING')}
            if name in expected and actual.value not in tuple(self.atom(v) for v in expected[name]):
                raise Refused('x11_property_type')
            if fmt.value!=kind or count.value>(maximum if kind==8 else maximum//4): raise Refused('x11_property_format')
            if count.value and not data: raise Refused('x11_property_empty_pointer')
            if kind==8: return C.string_at(data,count.value) if count.value else b''
            return tuple(int(v)&0xffffffff for v in C.cast(data,C.POINTER(UL))[:count.value])
        finally:
            if data: self.lib.XFree(data)
    def children(self,window):
        root=UL();parent=UL();children=C.POINTER(UL)();count=U()
        status=self.lib.XQueryTree(self.display,window,C.byref(root),C.byref(parent),C.byref(children),C.byref(count))
        try:
            self.sync()
            if not status or count.value>512: raise Refused('x11_tree_bound')
            return tuple(int(v) for v in children[:count.value])
        finally:
            if children: self.lib.XFree(children)
    def windows(self,pid):
        clients=self.property(self.root,'_NET_CLIENT_LIST',32,2048)
        if clients is None:
            clients=[];pending=[(self.root,0)];seen=set()
            while pending:
                node,depth=pending.pop()
                if node in seen: continue
                seen.add(node)
                if len(seen)>512: raise Refused('x11_tree_bound')
                if node!=self.root: clients.append(node)
                if depth<4: pending.extend((child,depth+1) for child in self.children(node))
        result=[]
        for window in dict.fromkeys(clients):
            if self.property(window,'_NET_WM_PID',32,4)!=(pid,): continue
            attr=Attributes()
            if not self.lib.XGetWindowAttributes(self.display,window,C.byref(attr)): raise Refused('x11_window_changed')
            self.sync()
            kinds=self.property(window,'_NET_WM_WINDOW_TYPE',32,128)
            transient=self.property(window,'WM_TRANSIENT_FOR',32,4)
            protocols=self.property(window,'WM_PROTOCOLS',32,128) or ()
            normal=(bool(self.atom('_NET_WM_WINDOW_TYPE_NORMAL')) and kinds==(self.atom('_NET_WM_WINDOW_TYPE_NORMAL'),) and
                    not transient and not attr.override_redirect and attr.map_state==2)
            title=self.property(window,'_NET_WM_NAME',8) or self.property(window,'WM_NAME',8) or b''
            result.append(dict(window_id=int(window),title_sha256=sha(title),normal=normal,
                               delete_supported=bool(self.atom('WM_DELETE_WINDOW')) and self.atom('WM_DELETE_WINDOW') in protocols))
        return result
    def send_delete(self,window):
        event=Event();event.xclient.type=33;event.xclient.send_event=1
        event.xclient.display=self.display;event.xclient.window=window
        event.xclient.message_type=self.atom('WM_PROTOCOLS');event.xclient.format=32
        event.xclient.data.l[0]=self.atom('WM_DELETE_WINDOW');event.xclient.data.l[1]=0
        if not self.lib.XSendEvent(self.display,window,0,0,C.byref(event)): raise Refused('wm_delete_not_sent')
        self.sync()
    def close(self):
        if self.display: self.lib.XCloseDisplay(self.display); self.display=None
        if hasattr(self,'previous'): self.lib.XSetErrorHandler(self.previous)


def inspect(plan,plan_sha,host,x11):
    before=host.static(plan);owner=host.verify_owner(plan['owner'])
    windows=x11.windows(owner['pid'])
    if len(windows)!=1 or not windows[0]['normal'] or not windows[0]['delete_supported']:
        raise Refused('dialog_ambiguous_or_unsupported_window')
    after=host.static(plan);second=host.verify_owner(plan['owner'])
    if before!=after or owner!=second: raise Refused('proof_changed_during_inspect')
    window={k:windows[0][k] for k in ('window_id','title_sha256')}
    proof=dict(plan_sha256=plan_sha,owner=owner,window=window,static=after)
    return dict(status='INSPECTED',window=window,owner=owner,review_token=sha(canonical(proof)),
                close_guard_ready=guarded(after),source_proof_sha256=after['sources_sha256']),proof


def request_close(plan,plan_sha,host,x11,token,window_id,*,clock=time.monotonic,wait=time.sleep,observe_seconds=20.):
    result,proof=inspect(plan,plan_sha,host,x11)
    if not guarded(proof['static']): raise Refused('effective_service_guards_required')
    if token!=result['review_token'] or window_id!=result['window']['window_id']: raise Refused('review_token_or_window')
    # Recheck the exact window/PID/title and source/owner immediately before
    # sending, rather than trusting a stale inspect result from another call.
    repeated,again=inspect(plan,plan_sha,host,x11)
    if again!=proof: raise Refused('proof_changed_before_send')
    x11.send_delete(window_id)
    deadline=clock()+min(20.,max(0.,observe_seconds))
    exited=False
    while True:
        current=host.process(plan['owner']['pid'])
        if current is None or current['birth']!=plan['owner']['birth']:
            exited=True;break
        if current['cmdline_sha256']!=plan['owner']['cmdline_sha256']: break
        if clock()>=deadline: break
        wait(min(.1,max(0.,deadline-clock())))
    after=host.static(plan)
    result.update(status='WM_DELETE_SENT_OWNER_EXITED' if exited else 'WM_DELETE_SENT_OWNER_STILL_PRESENT',
                  owner_exited=exited,source_proof_unchanged=after['sources_sha256']==proof['static']['sources_sha256'],
                  effective_guards_after=guarded(after),forced_action=False)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--request-close',action='store_true')
    parser.add_argument('--review-token');parser.add_argument('--window-id',type=lambda v:int(v,0))
    args=parser.parse_args();x11=None
    try:
        plan=load_plan(args.plan,args.plan_sha256)
        if args.request_close and (not args.review_token or args.window_id is None): raise Refused('explicit_close_proof_required')
        x11=X11(plan['display']);host=HostProof()
        result=(request_close(plan,args.plan_sha256,host,x11,args.review_token,args.window_id) if args.request_close else
                inspect(plan,args.plan_sha256,host,x11)[0])
        print(json.dumps(result,sort_keys=True));return 0 if not args.request_close or result['owner_exited'] else 3
    except Exception as exc:
        # No command line, environment, title, exception repr or screenshots.
        print(json.dumps(dict(status='REFUSED',error=str(exc) if isinstance(exc,Refused) else type(exc).__name__,forced_action=False)))
        return 2
    finally:
        if x11 is not None: x11.close()


if __name__=='__main__': raise SystemExit(main())
