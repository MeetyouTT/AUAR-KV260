from common import *
def write(path,body):
    dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((body.strip()+'\n').encode())
write('build/scripts/reproduce.py',r'''
"""Verify one extracted release on a single CPU. The report must be outside the release."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args()
    out=args.out.resolve()
    if out==ROOT or ROOT in out.parents:
        ap.error('choose a new --out outside the release')
    out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    py=[sys.executable,'-B']
    steps=[
        ('release',ROOT,py+['build/scripts/verify.py']),
        ('fpga_inputs',ROOT,py+['build/scripts/fpga.py','check']),
        ('motion_fixture',ROOT/'sim/motion',py+['run_pure_suite.py']),
        ('skill_a',ROOT/'skill/command_guard_validation',py+['scripts/run_checks.py']),
        ('skill_b',ROOT/'skill/perception_freshness_benchmark',py+['-m','unittest','discover','-s','tests','-v']),
        ('skill_b_measured',ROOT/'skill/perception_freshness_benchmark',py+['scripts/analyze_counters.py','examples/public_counters.json']),
        ('skill_c',ROOT/'skill/llm_voice_runtime_optimization',py+['scripts/check.py']),
        ('pynq_unit',ROOT/'skill/pynq_contract_testgen',py+['-m','unittest','discover','-s','tests','-v']),
        ('pynq_examples',ROOT/'skill/pynq_contract_testgen',py+['scripts/reproduce.py','--out',str(out/'pynq')]),
    ]
    result={'python':platform.python_version(),'platform':platform.platform(),'cpu_affinity_count':len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,'board_or_gpu_used':False,'steps':[]}
    for name,cwd,cmd in steps:
        t=time.monotonic()
        with (out/(name+'.log')).open('wb') as f:
            r=subprocess.run(cmd,cwd=str(cwd),env=env,stdout=f,stderr=subprocess.STDOUT)
        result['steps'].append(dict(name=name,exit_code=r.returncode,elapsed_seconds=round(time.monotonic()-t,3)))
        result['status']='FAIL' if r.returncode else 'RUNNING'
        (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        print(name,result['steps'][-1]['exit_code'],flush=True)
        if r.returncode:raise SystemExit('Failed, see '+str(out/(name+'.log')))
    result['status']='PASS'
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS',out/'summary.json')

if __name__=='__main__':main()
''')
write('build/scripts/native_build.sh',r'''
#!/bin/sh
# Explicit native AArch64 build. Only writes to a new output directory.
set -eu
if [ "$#" -ne 1 ]; then echo "usage: sh native_build.sh NEW_OUTPUT" >&2; exit 2; fi
case "$(uname -m)" in aarch64|arm64) ;; *) echo "AArch64 build environment required" >&2; exit 2;; esac
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
case "$1" in /*) out="$1";; *) out="$(pwd)/$1";; esac
mkdir "$out"
cc -Wall -Wextra -std=c11 -O2 -fPIC -shared "$root/src/fpga/native/vsrv_mmio.c" -o "$out/libvsrv.so"
cc -Wall -Wextra -std=c11 -O2 -fPIC -shared "$root/src/motion/mmio_src/vsrv_mmio.c" -o "$out/libvsrv_batch.so"
c++ -std=c++17 -O3 -fPIC -shared -pthread "$root/src/software/tools/native_pixels.cpp" -o "$out/libaura_pixels.so"
python3 -B "$root/src/software/board/vision/native/build_yolox.py" --output "$out/libaura_yolox.so"
c++ -shared -Wl,-z,defs -pthread "$root/src/camera/native_operator/native_bridge.operator.aarch64.o" -o "$out/libaura_native_operator.so" -lvart-runner -lxir -ldl
cmake -S "$root/src/avatar/native_integration/host" -B "$out/yuki-build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$out/yuki-build" --target aura_yuki --parallel 1
''')
write('skill/readme.md',r'''
# 三个项目技能与通用 PYNQ 补充

| 目录 | 工作对象 | 可在低核 Linux 上检查的内容 |
| --- | --- | --- |
| command_guard_validation | A，运动命令保护 | 命令重放、越界、租约、STOP 与 QUIESCE。附同版 4 套 RTL 测试台及实际 XSim 日志。 |
| perception_freshness_benchmark | B，三模型服务率和感知时效 | 原始窗口计数回放、时钟和过期反例、三份 XIR 元数据。声纹 ECAPA 保留在 ARM CPU。 |
| llm_voice_runtime_optimization | C，LLM/TTS 交互运行优化 | 按次复算 RPC、解码速度和实时率，验证过期播放确认和记忆撤销。 |
| pynq_contract_testgen | 通用补充 | 用契约和合成 HWH 为加法器、CRC 生成可执行桩并与软件参考比对。 |

每个目录的 readme.md 含输入格式、运行入口、具体失败案例、证据和适用范围。在工程根目录执行 build/scripts/reproduce.py 可串行复跑。第四项沿用 Ubuntu 已完成的独立离线工具，PYNQ 真板和跨板复用属于单独验证范围。
''')
copy(CO/'2026-11-02_作品概述_AMD实跑_01a19c53/vivado_reports/design_metrics.tsv',ROOT/'build/reports/design_metrics.tsv')
# Keep bootgen filename regression trace alongside its corrected receipt.
p=ROOT/'build/reports/clean_directory_validation.json';j=load(p);assert j['firmware_files_byte_identical']
j.update(configuration_payload_sha256='f05c1b8df625e06d97b197ef8dd0ae1ba8c2ab0b81d5c32e731d72a9a9658dba',first_export_attempt='The first bootgen used paired.bit. Only a 28-byte header name region differed. Restoring original BIF input name visual_servo_paired.bit yielded all four deployment SHA256s exactly.')
save(p,j)
