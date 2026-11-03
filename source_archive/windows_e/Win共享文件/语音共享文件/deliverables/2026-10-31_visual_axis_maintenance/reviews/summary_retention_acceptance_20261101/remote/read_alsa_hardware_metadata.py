"""Enumerate ALSA kernel metadata without opening playback or capture streams."""
import fcntl,hashlib,json,os,re,time
from pathlib import Path
assert os.geteuid()==0
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
lock=open('/run/lock/aura-axis-takeover-bebd3e7d.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
base=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert hashlib.sha256((base/'startup/config.json').read_bytes()).hexdigest()=='ec12fccfdd3e8446e9c761e161167e00187e6fcf90372aa7e52c9865cc23c56f'
rows=[]
for card in sorted(Path('/proc/asound').glob('card[0-9]*')):
    if not re.fullmatch(r'card[0-9]+',card.name):continue
    label=(card/'id').read_text().strip()
    index=int(card.name[4:])
    endpoints=[]
    for pcm in card.glob('pcm[0-9]*[pc]'):
        if not re.fullmatch(r'pcm[0-9]+[pc]',pcm.name):continue
        endpoints.append(dict(pcm=int(pcm.name[3:-1]),direction='playback' if pcm.name[-1]=='p' else 'capture',
            subdevices=len(list(pcm.glob('sub[0-9]*')))))
    rows.append(dict(card=index,id=label if re.fullmatch(r'[A-Za-z0-9_]{1,64}',label) else 'OTHER',
        target_mcp01=label=='MCP01',endpoints=endpoints))
target=next((row for row in rows if row['target_mcp01']),None)
print(json.dumps(dict(schema='aura-alsa-readonly-hardware-enumeration-1',observed_mono=time.monotonic(),
    cards=rows,target_mcp01_present=target is not None,target_playback_available=bool(target and any(p['direction']=='playback' for p in target['endpoints'])),
    stream_opened=False,audio_or_microphone_commands_sent=False,production_modified=False)))
