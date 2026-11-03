from common import *
import base64,datetime,io,wave
requested=load(ROOT/'board/config/image_inputs.json')['files']
snap=load(ROOT/'board/config/startup.snapshot.json')
gui_path=snap['runtime']+'/aura/config/board_avatar_gtk.json'
gui_hash=snap['component_sha256']['config/board_avatar_gtk.json']
public=load(ROOT/'data/reference/public_feedback.json')
assert len(requested)==12 and len(public['assets'])==3
board_reader="""import base64,hashlib,json,os,stat
from pathlib import Path
spec=SPEC
rows={}
for canonical,digest in spec.items():
    p=Path(canonical)
    row={}
    try:
        real=p.resolve(strict=True)
        if real != p and not (p.name==real.name and p.parent==Path('/etc/systemd/system') and real.parent in (Path('/usr/lib/systemd/system'),Path('/lib/systemd/system'))):
            raise ValueError('unapproved symlink target')
        fd=os.open(real,os.O_RDONLY|os.O_NOATIME|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as f:
            m=os.fstat(f.fileno())
            if not stat.S_ISREG(m.st_mode) or m.st_size>2*1024*1024:raise ValueError('not a sized regular file')
            content=f.read(2*1024*1024+1)
        if len(content)!=m.st_size:raise ValueError('size changed')
        h=hashlib.sha256(content).hexdigest()
        row={'state':'match' if h==digest else 'digest_differs','bytes':len(content),'sha256':h}
        if h==digest and canonical!=GUI:row['data']=base64.b64encode(content).decode('ascii')
        if canonical==GUI:
            g=json.loads(content);b=g['board_business']
            row['cue_bindings']=[{'path':g['formal_static_cues']['path'],'sha256':g['formal_static_cues']['sha256']},{'path':b['feedback_manifest'],'sha256':b['feedback_manifest_sha256']}]
    except (ValueError,OSError,KeyError) as e:
        row={'state':type(e).__name__}
    rows[canonical]=row
print(json.dumps(rows))
""".replace('SPEC',repr({**requested,gui_path:gui_hash})).replace('GUI',repr(gui_path))
cmd=['ssh','-b','192.168.50.1','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','BatchMode=yes','-o','RequestTTY=no','aura-kv260','python3 -I -B -']
p=subprocess.run(cmd,input=board_reader.encode(),capture_output=True,check=True,timeout=50)
reply=json.loads(p.stdout)
assert set(reply)==set(requested)|{gui_path}
gui=reply.pop(gui_path);expect_cue={'path':public['manifest'],'sha256':public['manifest_sha256']}
if gui.get('state')!='match' or gui['cue_bindings']!=[expect_cue,expect_cue]:
    print('public GUI configuration differs from the archived GUI:',{k:v for k,v in gui.items() if k!='data'})
blobdir=W/'public_kv260_copy';blobdir.mkdir(exist_ok=True)
cue_paths={x['path'] for x in public['assets']}|{public['manifest']}
records=[]
for n,d in reply.items():
    data=d.pop('data',None)
    entry=dict(destination=n,expected_sha256=requested[n],**d)
    if data is not None:
        buf=base64.b64decode(data,validate=True)
        assert d['state']=='match' and hashlib.sha256(buf).hexdigest()==requested[n] and len(buf)==d['bytes']
        (blobdir/requested[n]).write_bytes(buf)
        if n.endswith('.wav'):
            a=next(a for a in public['assets'] if a['path']==n)
            with wave.open(io.BytesIO(buf),'rb') as wav:
                assert (wav.getframerate(),wav.getnchannels(),wav.getsampwidth(),wav.getcomptype(),wav.getnframes())==(24000,1,2,'NONE',a['samples'])
                entry.update(samples=wav.getnframes(),hz=wav.getframerate(),channels=wav.getnchannels(),sample_width_bytes=wav.getsampwidth())
    records.append(entry);print(d['state'],n, d.get('bytes',''))
rec=dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),method='Pinned SSH host key, named public files opened O_RDONLY|O_NOATIME; matched SHA-256 before export',scope='Public configuration, original compiled camera libraries and three public fixed synthetic cue files only',gui_path=gui_path,gui_expected_sha256=gui_hash,gui_observation=gui,files=records)
save(W/'public_board_read_receipt.json',rec)
assert all(d['state']=='match' for n,d in reply.items() if n in cue_paths)
print('3 cue WAVs plus original manifest copied; binding',gui.get('state'))
