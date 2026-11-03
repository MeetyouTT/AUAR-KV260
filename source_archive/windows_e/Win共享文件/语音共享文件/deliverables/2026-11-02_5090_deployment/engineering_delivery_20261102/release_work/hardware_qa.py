from common import *
remote='/home/ghmd/auar-engineering-delivery-XpV7MC'
target=remote+'/firmware_inputs'
with subprocess.Popen(['ssh','aura-ubuntu','mkdir -p '+target+' && tar -xf - -C '+target],stdin=subprocess.PIPE)as p:
    with tarfile.open(fileobj=p.stdin,mode='w|')as t:
        for n in ['build/scripts/pack_firmware.py','build/original/bitstream_pairing.py','board/firmware_pairing.json','board/handoff','board/firmware','sim/native','src/fpga/native']:
            t.add(ROOT/n,arcname=n)
    p.stdin.close()
    if p.wait():sys.exit(1)
def shell(s):return subprocess.run(['ssh','aura-ubuntu','cd '+target+' && '+s],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
impl=remote+'/clean_export/implementation'
r=shell('BOOTGEN=/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin/bootgen python3 -B build/scripts/pack_firmware.py --bit '+impl+'/export-resume/visual_servo_source.bit --xsa '+impl+'/visual_servo_source_implemented.xsa --out '+remote+'/regenerated_firmware_v2')
(QA/'regenerated_firmware.txt').write_bytes(r.stdout)
print(r.returncode,r.stdout.decode(errors='replace')[-500:])
if r.returncode:sys.exit(r.returncode)
r=shell('cc -Wall -Wextra -Werror -O2 -std=c11 -Isrc/fpga/native sim/native/test_protocol.c -o '+remote+'/test_protocol && '+remote+'/test_protocol')
(QA/'native_protocol.txt').write_bytes(r.stdout)
if r.returncode:raise RuntimeError(r.stdout)
r=shell('sha256sum '+remote+'/regenerated_firmware_v2/aura-visual-servo-b4096-wide-v1/*')
live=load(ROOT/'board/firmware_pairing.json')
bits={p.rsplit('/',1)[-1]:h for p,h in live['runtime_files'].items()}
result={line.split()[1].split('/')[-1]:line.split()[0] for line in r.stdout.decode().splitlines()}
save(ROOT/'build/reports/clean_directory_validation.json',dict(vivado='2022.2',os='Ubuntu 20.04.4 LTS',cpu_threads_per_vivado=1,prepare=load(QA/'vivado_prepare.json'),checkpoint_export=load(QA/'vivado_export.json'),new_full_synthesis_and_route=False,routed_checkpoint_sha256='933c712d30fd6aa549eb785a21dc6ca360ce179b24b9d3fb76a777d662d96007',paired_reexport_sha256=result,historical_runtime_sha256=bits,firmware_files_byte_identical=(result==bits),native_protocol_result=r'PASS, host C, no MMIO'))
print('firmware recreated, same deployed byte set?',result==bits)
