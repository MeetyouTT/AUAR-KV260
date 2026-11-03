from common import *
remote='/home/ghmd/auar-engineering-delivery-XpV7MC'
def send(paths):
    with subprocess.Popen(['ssh','aura-ubuntu','mkdir -p '+remote+'/xir && tar -xf - -C '+remote+'/xir'],stdin=subprocess.PIPE) as p:
        with tarfile.open(fileobj=p.stdin,mode='w|')as tar:
            for n in paths:tar.add(ROOT/n,arcname=n)
        p.stdin.close()
        if p.wait():raise RuntimeError('transfer')
send(['models/dpu','build/scripts/inspect_xmodel.py'])
cmd="docker run --rm --network none --read-only --tmpfs /tmp -v "+remote+"/xir:/project:ro --entrypoint /opt/vitis_ai/conda/envs/vitis-ai-pytorch/bin/python xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106 -B /project/build/scripts/inspect_xmodel.py /project/models/dpu/yolox_nano_person.xmodel /project/models/dpu/yunet_public_int8.xmodel /project/models/dpu/sface_public_int8.xmodel"
r=subprocess.run(['ssh','-o','BatchMode=yes','aura-ubuntu',cmd],capture_output=True)
(QA/'xir_stderr.txt').write_bytes(r.stderr)
if r.returncode:print(r.stderr.decode(errors='replace')[:650]);sys.exit(r.returncode)
j=json.loads(r.stdout)
for row in j['models']:
    p=ROOT/'models/dpu'/Path(row.get('path',row.get('file',''))).name
    print(list(row)[:8])
    parts=row['partitions']; assert sum(s['device']=='DPU' for s in parts)==1
    print(row.get('sha256'),[(s['device'],s['fingerprint']) for s in parts])
save(ROOT/'data/results/xir_three_models.json',j)
