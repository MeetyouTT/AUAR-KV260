"""Probe or cycle only the identified display's USB port using USB hub requests."""
import ctypes as C
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BOOT='975f931a-927b-4a06-b784-ebda8463177f'
CID='0353445345333247805558c00401a100'
SYS=Path('/sys/bus/usb/devices')
TARGET='1-1.1'
OTHER={'1-1.2':('17ef','a03b'),'1-1.3':('0c45','6341')}

def identity(name):
    p=SYS/name
    if not p.exists():return None
    return {k:(p/k).read_text().strip() for k in ['idVendor','idProduct','busnum','devnum','product'] if (p/k).exists()}

class USB:
    def __init__(self):
        self.lib=C.CDLL('/lib/libusb-1.0.so.0')
        signatures={
            'libusb_init':([C.POINTER(C.c_void_p)],C.c_int),
            'libusb_exit':([C.c_void_p],None),
            'libusb_open_device_with_vid_pid':([C.c_void_p,C.c_uint16,C.c_uint16],C.c_void_p),
            'libusb_close':([C.c_void_p],None),
            'libusb_get_device':([C.c_void_p],C.c_void_p),
            'libusb_get_bus_number':([C.c_void_p],C.c_uint8),
            'libusb_get_device_address':([C.c_void_p],C.c_uint8),
            'libusb_get_port_numbers':([C.c_void_p,C.POINTER(C.c_uint8),C.c_int],C.c_int),
            'libusb_control_transfer':([C.c_void_p,C.c_uint8,C.c_uint8,C.c_uint16,C.c_uint16,C.c_void_p,C.c_uint16,C.c_uint],C.c_int),
        }
        for name,(args,result) in signatures.items():
            f=getattr(self.lib,name);f.argtypes=args;f.restype=result
        self.context=C.c_void_p()
        assert self.lib.libusb_init(C.byref(self.context))==0
        self.hubs=[]
    def close(self):
        for h in self.hubs:self.lib.libusb_close(h.handle)
        self.lib.libusb_exit(self.context)

class Hub:
    def __init__(self,usb,path,pid,ss):
        self.usb=usb;self.path=path;self.ss=ss;self.trace=[]
        ident=identity(path)
        assert ident and ident['idVendor']=='0424' and ident['idProduct']==format(pid,'04x')
        self.handle=usb.lib.libusb_open_device_with_vid_pid(usb.context,0x0424,pid)
        assert self.handle,'Cannot open identified USB hub'
        usb.hubs.append(self)
        dev=usb.lib.libusb_get_device(self.handle)
        ports=(C.c_uint8*8)()
        n=usb.lib.libusb_get_port_numbers(dev,ports,8)
        assert n==1 and ports[0]==1
        assert usb.lib.libusb_get_bus_number(dev)==int(ident['busnum'])
        assert usb.lib.libusb_get_device_address(dev)==int(ident['devnum'])
        self.descriptor=self.transfer(0xa0,6,(0x2a if ss else 0x29)<<8,0,12)
        assert len(self.descriptor)>=9 and self.descriptor[2]==4
        assert (int.from_bytes(self.descriptor[3:5],'little')&3)==1,'Individual port power is not supported'
        self.power_mask=0x200 if ss else 0x100
    def transfer(self,kind,request,value,index,length=0):
        data=(C.c_uint8*length)() if length else None
        rc=self.usb.lib.libusb_control_transfer(self.handle,kind,request,value,index,data,length,1000)
        assert rc>=0,'USB control transfer failed: '+str(rc)
        return bytes(data[:rc]) if length else rc
    def status(self,port=1):
        raw=self.transfer(0xa3,0,0,port,4)
        assert len(raw)==4
        return {'status':int.from_bytes(raw[:2],'little'),'change':int.from_bytes(raw[2:],'little')}
    def power(self,on):
        # USB hub class SET/CLEAR_FEATURE(PORT_POWER), recipient port 1 only.
        rc=self.transfer(0x23,3 if on else 1,8,1)
        self.trace.append({'on':bool(on),'port':1,'rc':rc,'monotonic':time.monotonic()})

def restore_all(hubs):
    errors=[]
    for h in hubs:
        try:h.power(True)
        except Exception as exc:errors.append({'hub':h.path,'error':str(exc)})
    return errors

def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=6)
    return {'rc':p.returncode,'text':p.stdout[-5000:]}

def check_other(before):
    assert all(identity(name)==expected for name,expected in before.items()),'Another USB peripheral changed; restore immediately'

def main(action):
    assert action in ['probe','cycle','restore']
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()==CID
    usb=USB()
    try:
        hubs=[Hub(usb,'2-1',0x5744,True),Hub(usb,'1-1',0x2744,False)]
        report={'boot_id':BOOT,'action':action,'before':{h.path:{'descriptor_hex':h.descriptor.hex(),'ports':{str(p):h.status(p) for p in [1,2,3,4]}} for h in hubs}}
        if action=='restore':
            report['restore_errors']=restore_all(hubs)
            report['after']={h.path:h.status() for h in hubs}
            print(json.dumps(report),flush=True)
            assert not report['restore_errors']
            return
        target=identity(TARGET)
        assert target and (target['idVendor'],target['idProduct'])==('0eef','0005') and target.get('product')=='WS170120'
        assert not (SYS/'2-1.1').exists(),'Unexpected device on companion port'
        others={name:identity(name) for name in OTHER}
        for name,ids in OTHER.items():
            assert others[name] and (others[name]['idVendor'],others[name]['idProduct'])==ids
        assert {p.name for p in SYS.glob('1-1.*') if (p/'idVendor').exists()}=={TARGET,*OTHER}
        report.update(target=target,other_devices=others,edid_bytes_before=len(Path('/sys/class/drm/card0-DP-1/edid').read_bytes()))
        if action=='probe':
            report['usb_power_writes']=0
            print(json.dumps(report),flush=True)
            return
        op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:ui=json.load(r)
        assert ui['phase']=='IDLE' and not ui.get('playing'),'Application busy'
        assert report['edid_bytes_before']==0,'Failure state changed; do not cycle a recovered screen'
        root=Path('/run/aura-screen-port-cycle-20261021')/BOOT
        root.mkdir(parents=True,exist_ok=False)
        script=root/'control.py';script.write_bytes(Path(main.__code__.co_filename).read_bytes())
        timer='aura-screen-power-restore-'+BOOT[:8]
        watchdog=run(['systemd-run','--unit='+timer,'--on-active=15','--property=RuntimeMaxSec=8','/usr/bin/python3','-B',str(script),'restore'])
        assert watchdog['rc']==0,watchdog
        armed=run(['systemctl','is-active',timer+'.timer'])
        assert armed['rc']==0 and armed['text'].strip()=='active','Independent power restoration is not armed'
        report['watchdog']=watchdog;report['off_samples']=[]
        try:
            for h in hubs:h.power(False)
            start=time.monotonic()
            while time.monotonic()-start<5:
                check_other(others)
                states={h.path:h.status() for h in hubs}
                assert all(not (states[h.path]['status']&h.power_mask) for h in hubs),'Port power did not turn off'
                report['off_samples'].append({'elapsed':round(time.monotonic()-start,3),'port_states':states,'touch_present':identity(TARGET) is not None})
                time.sleep(.25)
            report['off_seconds']=round(time.monotonic()-start,3)
        finally:
            report['restore_errors']=restore_all(hubs)
            report['port_states_after_restore']={h.path:h.status() for h in hubs}
            report['control_trace']={h.path:h.trace for h in hubs}
            (root/'control-result.json').write_text(json.dumps(report,indent=2)+'\n')
            # Keep the independent timer armed unless both logical ports are on.
            if not report['restore_errors'] and all(report['port_states_after_restore'][h.path]['status']&h.power_mask for h in hubs):
                report['watchdog_cancel']=run(['systemctl','stop',timer+'.timer'])
        assert not report['restore_errors']
        time.sleep(4)
        check_other(others)
        report['touch_after']=identity(TARGET)
        report['query']=run(['env','DISPLAY=:0','xrandr','--verbose'])
        raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
        report['edid_bytes_after']=len(raw);report['edid_sha256_after']=hashlib.sha256(raw).hexdigest()
        report['units']=run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'])
        report['other_devices_unchanged']=True
        report['movement_commands_sent']=0;report['mode_control_commands_sent']=0;report['physical_fix_verified']=False
        (root/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
    finally:
        usb.close()

if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else 'probe')
