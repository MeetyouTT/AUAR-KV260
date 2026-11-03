from common import *
remote='/home/ghmd/auar-engineering-delivery-XpV7MC'
with subprocess.Popen(['ssh','-o','BatchMode=yes','aura-ubuntu',"mkdir -p "+remote+"/fpga_inputs && tar -xf - -C "+remote+"/fpga_inputs"],stdin=subprocess.PIPE) as p:
    with tarfile.open(fileobj=p.stdin,mode='w|') as t:
        for n in ['src/fpga','build/original','build/reports/ubuntu_inputs.json','build/scripts','sim/rtl']:
            t.add(ROOT/n,arcname=n)
    p.stdin.close()
    if p.wait():raise RuntimeError('transfer')
print('Separate clean input directory transferred.',flush=True)
def job(kind,command):
    with (QA/('vivado_'+kind+'.txt')).open('wb') as f:
        rc=subprocess.call(['ssh','-o','BatchMode=yes','aura-ubuntu','cd '+remote+'/fpga_inputs && '+command],stdout=f,stderr=subprocess.STDOUT)
    save(QA/('vivado_'+kind+'.json'),{'action':kind,'exit_code':rc,'source':'separate copy on Ubuntu 20.04, Vivado 2022.2','fresh_synth_route':False})
    print(kind,rc,flush=True)
import concurrent.futures
env='XILINX_VITIS=/home/ghmd/Xilinx_2022.2/Vitis/2022.2 VIVADO_BIN=/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/vivado OMP_NUM_THREADS=1 '
with concurrent.futures.ThreadPoolExecutor(2) as ex:
    fs=[ex.submit(job,'prepare',env+'python3 build/scripts/fpga.py prepare --out '+remote+'/clean_project'),
        ex.submit(job,'export',env+'python3 build/scripts/fpga.py export --out '+remote+'/clean_export --checkpoint /home/ghmd/aura-pan-wide-20261028/implementation/source_routed.dcp')]
    for f in fs:f.result()
