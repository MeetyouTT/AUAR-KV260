"""Prepare finite correction from reviewed previous launcher; no hardware IO."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='3e1add36-b917-4289-91dc-699348528782'
old=Path('/home/root/aura-pan-follow-20261020/prepared-midpoint-04/execute.py').read_text()
assert hashlib.sha256(old.encode()).hexdigest()=='c4b129b1555889b9678c13cfd3bea16b50e0d0c09cd8e782999e37eaae464111'
w=old;marker="RAW=gzip.decompress(base64.b64decode('"
i=w.index(marker)+len(marker);e=w.index("'))",i)
s=gzip.decompress(base64.b64decode(w[i:e])).decode()
for a,b in [('1490 us is an initialization', '1470 us is an initialization'), ("'initial_pulse_us': 1490", "'initial_pulse_us': 1470"), ('for pulse in (1470,)', 'for pulse in (1450,)'), ('One finite 1470us step from initial 1490us', 'One finite 1450us step from initial 1470us'), ('MIDPOINT1470-2S', 'MIDPOINT1450-2S'), ("initial['ack_seq'] == 208 and initial['epoch'] == 5 and initial['width_us'] == 1490", "initial['ack_seq'] == 46 and initial['epoch'] == 6 and initial['width_us'] == 1470"), ("initial['target_us'] == 1490", "initial['target_us'] == 1470"), ('session, epoch = 0x20261020, 6', 'session, epoch = 0x20261020, 7'), ('io.write(0x3c, 1490)', 'io.write(0x3c, 1470)'), ("state['reference_us'] == 1490 and state['width_us'] == 1490", "state['reference_us'] == 1470 and state['width_us'] == 1470")]:
 assert a in s,a
 s=s.replace(a,b)
bench=s.encode();assert hashlib.sha256(bench).hexdigest()=='d0a83fabfc1a66825fe2425ac54f292945941da934a8bd1a9b58526a58c1ddee'
packed=bytearray(gzip.compress(bench,mtime=0));packed[9]=255
w=w[:i]+base64.b64encode(packed).decode()+w[e:]
for a,b in [('midpoint-step-04', 'midpoint-step-05'), ('9b12dd9c4357b011e202ec2635f81db967ca17ad59f752460c303e3edac0ec88', 'd0a83fabfc1a66825fe2425ac54f292945941da934a8bd1a9b58526a58c1ddee'), ('one 1470us hold for2s from1490us', 'one 1450us hold for2s from1470us'), ('MIDPOINT1470-2S', 'MIDPOINT1450-2S'), ('看清了，现在还有点向右偏转，再转一下', '还是朝右'), ("'previous_test_point_us':1490", "'previous_test_point_us':1470"), ('finite 1470us correction', 'finite 1450us correction')]:
 assert a in w,a
 w=w.replace(a,b)
raw=w.encode();assert hashlib.sha256(raw).hexdigest()=='94a843513215de9fde852f2f509e807c69c0cb23a5b8bc9895704650eed7de8a'
compile(raw,'execute.py','exec')
p=Path('/home/root/aura-pan-follow-20261020/prepared-midpoint-05/execute.py');p.parent.mkdir(parents=True,exist_ok=False)
with p.open('xb') as stream:stream.write(raw)
print(json.dumps({'status':'PREPARED_NO_ACTUATION','sha256':'94a843513215de9fde852f2f509e807c69c0cb23a5b8bc9895704650eed7de8a','bench_sha256':'d0a83fabfc1a66825fe2425ac54f292945941da934a8bd1a9b58526a58c1ddee'}),flush=True)
