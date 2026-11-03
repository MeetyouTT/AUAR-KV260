"""Read-only audio transport and service metadata; no audio samples or transcripts."""
import collections,json,os,subprocess,time,urllib.request
from pathlib import Path

def read(p,limit=12000):
    try:return Path(p).read_text()[:limit].strip()
    except OSError:return None
def command(args):
    try:return subprocess.check_output(args,timeout=4).decode(errors='replace').strip()
    except (OSError,subprocess.SubprocessError) as e:return type(e).__name__
def health():
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8790/health',timeout=2) as r:s=json.load(r)
        return {k:s.get(k) for k in ('pid','detected_frames','capture_hz','detection_hz','camera_error','detector_error','observation_age_ms','dpu_schedule')}
    except Exception as e:return {'error':type(e).__name__}
def journal():
    raw=command(['journalctl','-b','-n','800','-o','json','--no-pager'])
    records=[]
    for line in raw.splitlines():
        try:records.append(json.loads(line))
        except ValueError:pass
    counts=collections.Counter(str(r.get('SYSLOG_IDENTIFIER','?')) for r in records)
    warns=[r for r in records if "HC couldn't access mem fast enough" in str(r.get('MESSAGE',''))]
    timestamps=[int(r['__MONOTONIC_TIMESTAMP']) for r in records if '__MONOTONIC_TIMESTAMP' in r]
    span=(max(timestamps)-min(timestamps))/1e6 if len(timestamps)>1 else None
    return {'count':len(records),'identifier_counts':dict(counts),'span_seconds':span,
            'xhci_warning_count':len(warns),'xhci_warning_messages':dict(collections.Counter(str(r.get('MESSAGE')) for r in warns)),
            'last_monotonic_us':max(timestamps) if timestamps else None}
def cpu():
    s=read('/proc/stat').splitlines()[0].split()[1:];v=list(map(int,s))
    return sum(v[:8]),v[3]+v[4]

out={'boot_id':read('/proc/sys/kernel/random/boot_id'),'uptime':read('/proc/uptime'),
     'kernel':command(['uname','-r']),'camera_before':health(),'journal_before':journal(),'units':{},'usb_audio':[]}
for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service','systemd-journald.service'):
    out['units'][name]=command(['systemctl','show',name,'-p','MainPID','-p','NRestarts','-p','ActiveState'])
for p in Path('/sys/bus/usb/devices').glob('*'):
    if read(p/'idVendor')!='17ef' or read(p/'idProduct')!='a03b':continue
    item={'path':p.name,'devnum':read(p/'devnum'),'speed':read(p/'speed'),'interfaces':[]}
    for interface in sorted(Path('/sys/bus/usb/devices').glob(p.name+':*')):
        desc={'name':interface.name,'altsetting':read(interface/'bAlternateSetting'),'interface_class':read(interface/'bInterfaceClass'),'endpoints':[]}
        for endpoint in sorted(interface.glob('ep_*')):
            desc['endpoints'].append({n:read(endpoint/n) for n in ('bEndpointAddress','bmAttributes','wMaxPacketSize','bInterval','direction','type','interval')})
        item['interfaces'].append(desc)
    out['usb_audio'].append(item)
out['alsa']={str(p):read(p) for p in Path('/proc/asound').glob('card*/stream*')}
out['pcm_status']={str(p):read(p) for p in Path('/proc/asound').glob('card*/pcm*/sub*/status')}
out['xhci_contexts']={}
for p in Path('/sys/kernel/debug/usb/xhci').glob('*/devices/*'):
    context=read(p/'slot-context')
    if context and 'Addr 4' in context:
        out['xhci_contexts'][str(p)]={'slot':context,'children':sorted(x.name for x in p.iterdir()),'ep_context':read(p/'ep-context',10000)}
a=cpu();start=time.monotonic();time.sleep(3);b=cpu()
out['sample_seconds']=time.monotonic()-start
out['cpu_total_pct']=100*(1-(b[1]-a[1])/float(b[0]-a[0]))
out['camera_after']=health();out['journal_after']=journal()
print(json.dumps(out))
