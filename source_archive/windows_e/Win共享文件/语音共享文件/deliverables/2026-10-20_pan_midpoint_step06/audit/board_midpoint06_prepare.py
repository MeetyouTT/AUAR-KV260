"""Prepare finite correction from reviewed previous launcher; no hardware IO."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='3e1add36-b917-4289-91dc-699348528782'
old=Path('/home/root/aura-pan-follow-20261020/prepared-midpoint-05/execute.py').read_text()
assert hashlib.sha256(old.encode()).hexdigest()=='94a843513215de9fde852f2f509e807c69c0cb23a5b8bc9895704650eed7de8a'
w=old;marker="RAW=gzip.decompress(base64.b64decode('"
i=w.index(marker)+len(marker);e=w.index("'))",i)
s=gzip.decompress(base64.b64decode(w[i:e])).decode()
for a,b in [('1470 us is an initialization', '1450 us is an initialization'), ("'initial_pulse_us': 1470", "'initial_pulse_us': 1450"), ('for pulse in (1450,)', 'for pulse in (1430,)'), ('One finite 1450us step from initial 1470us', 'One finite 1430us step from initial 1450us'), ('MIDPOINT1450-2S', 'MIDPOINT1430-2S'), ("initial['ack_seq'] == 46 and initial['epoch'] == 6 and initial['width_us'] == 1470", "initial['ack_seq'] == 46 and initial['epoch'] == 7 and initial['width_us'] == 1450"), ("initial['reference_us'] == 1490 and initial['target_us'] == 1470", "initial['reference_us'] == 1470 and initial['target_us'] == 1450"), ('session, epoch = 0x20261020, 7', 'session, epoch = 0x20261020, 8'), ('io.write(0x3c, 1470)', 'io.write(0x3c, 1450)'), ("state['reference_us'] == 1470 and state['width_us'] == 1470", "state['reference_us'] == 1450 and state['width_us'] == 1450")]:
 assert a in s,a
 s=s.replace(a,b)
bench=s.encode();assert hashlib.sha256(bench).hexdigest()=='34801a6c61d335b47f52a47b5e4fdb0e37d4c9d8fe5bcfecfbdd65bf4d574bb4'
packed=bytearray(gzip.compress(bench,mtime=0));packed[9]=255
w=w[:i]+base64.b64encode(packed).decode()+w[e:]
for a,b in [('midpoint-step-05', 'midpoint-step-06'), ('d0a83fabfc1a66825fe2425ac54f292945941da934a8bd1a9b58526a58c1ddee', '34801a6c61d335b47f52a47b5e4fdb0e37d4c9d8fe5bcfecfbdd65bf4d574bb4'), ('one 1450us hold for2s from1470us', 'one 1430us hold for2s from1450us'), ('MIDPOINT1450-2S', 'MIDPOINT1430-2S'), ('还是朝右', '还有点偏右'), ("'previous_test_point_us':1470", "'previous_test_point_us':1450"), ('finite 1450us correction', 'finite 1430us correction')]:
 assert a in w,a
 w=w.replace(a,b)
raw=w.encode();assert hashlib.sha256(raw).hexdigest()=='24a20e84d75e90499721d7d75258177ef0bce24e2b8347c202b8d60b8cd79770'
compile(raw,'execute.py','exec')
p=Path('/home/root/aura-pan-follow-20261020/prepared-midpoint-06/execute.py');p.parent.mkdir(parents=True,exist_ok=False)
with p.open('xb') as stream:stream.write(raw)
print(json.dumps({'status':'PREPARED_NO_ACTUATION','sha256':'24a20e84d75e90499721d7d75258177ef0bce24e2b8347c202b8d60b8cd79770','bench_sha256':'34801a6c61d335b47f52a47b5e4fdb0e37d4c9d8fe5bcfecfbdd65bf4d574bb4'}),flush=True)
