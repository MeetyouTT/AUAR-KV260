"""Bounded one-frame-at-a-time RGB transfer; no native sink or UI switch."""
import json,math,queue,socket,struct,subprocess,sys,threading,time,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'2026-10-18_board_dialogue'))
from board_ssh import KEY
raw=(HERE/'sample_rgb.bin').read_bytes();assert len(raw)==555822
crc=zlib.crc32(raw);count=64;rates=(12,16,24);total=count*len(rates)
remote=r'''
import json,socket,struct,time,zlib
N=TOTAL;SIZE=SIZE_TOKEN
def exact(connection,n):
    data=bytearray(n);view=memoryview(data);offset=0
    while offset<n:
        amount=connection.recv_into(view[offset:])
        if not amount:raise EOFError('Connection ended')
        offset+=amount
    return data
with socket.socket() as server:
    server.bind(('192.168.50.2',0));server.listen(1);server.settimeout(15)
    print(json.dumps({'port':server.getsockname()[1],'native_video':False}),flush=True)
    connection,address=server.accept();assert address[0]=='192.168.50.1'
    with connection:
        connection.settimeout(8);connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        started=time.monotonic();cpu=time.process_time();received=0
        for expected in range(N):
            seq,length=struct.unpack('!II',exact(connection,8));assert seq==expected and length==SIZE
            frame=exact(connection,length);received+=len(frame)
            connection.sendall(struct.pack('!II',seq,zlib.crc32(frame)))
        print(json.dumps({'frames':N,'bytes':received,'cpu_seconds':time.process_time()-cpu,
            'elapsed_seconds':time.monotonic()-started,'display_created':False,'physical_audio':False,'microphone':False}),flush=True)
'''.replace('TOTAL',str(total)).replace('SIZE_TOKEN',str(len(raw)))
cmd=['C:/Windows/System32/OpenSSH/ssh.exe','-i',str(KEY),'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
     '-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4','root@192.168.50.2','python3 -B -']
process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
process.stdin.write(remote);process.stdin.close()
lines=queue.Queue()
def reader():
    for line in process.stdout:lines.put(line)
threading.Thread(target=reader,daemon=True).start()
def exact(connection,n):
    data=bytearray()
    while len(data)<n:
        part=connection.recv(n-len(data))
        if not part:raise EOFError('No frame acknowledgement')
        data.extend(part)
    return data
try:
    ready=json.loads(lines.get(timeout=20));assert ready['native_video'] is False
    records=[];sequence=0
    with socket.create_connection(('192.168.50.2',ready['port']),timeout=5) as connection:
        connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        for fps in rates:
            stamps=[];latencies=[];late=0;begin=time.perf_counter()
            for index in range(count):
                due=begin+index/fps;remaining=due-time.perf_counter()
                if remaining>0:time.sleep(remaining)
                started=time.perf_counter();stamps.append(started)
                if started-due>1/fps:late+=1
                connection.sendall(struct.pack('!II',sequence,len(raw)));connection.sendall(raw)
                got,checksum=struct.unpack('!II',exact(connection,8));assert got==sequence and checksum==crc
                latencies.append((time.perf_counter()-started)*1000);sequence+=1
            ordered=sorted(latencies)
            records.append({'target_fps':fps,'frames':count,'effective_send_fps':(count-1)/(stamps[-1]-stamps[0]),
                'rtt_p95_ms':ordered[math.ceil(count*.95)-1],'rtt_max_ms':max(ordered),'missed_send_deadlines':late,
                'crc_verified_frames':count,'rgb_Mbps_at_target':len(raw)*fps*8/1e6})
    receiver=json.loads(lines.get(timeout=15));code=process.wait(timeout=10)
    assert code==0 and receiver['frames']==total
    value={'status':'PASS','scope':'real wired raw RGB receive + CRC + acknowledgement; no decode or display',
        'records':records,'receiver':receiver,'max_inflight_frames':1,'listener_closed':True,
        'pixel_bytes':len(raw),'production_ui_changed':False,'physical_screen_fps_tested':False}
    (HERE/'wire_transport.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value))
finally:
    if process.poll() is None:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
