import csv
from pathlib import Path

aud = Path('/home/ghmd/kv260_readonly_audit_20260927_7sM1wd')
rows = [
    ('system', 'Ubuntu', '20.04.4 LTS / 5.15.0-139-generic', '/', '-', '-', '检查通过（抽样）', 'logs/host.txt;logs/package_verify.txt'),
    ('storage', '/home/ghmd ext4', '22 GB free / 94% used', '/dev/nvme0n1p10', '-', '-', '有风险但尚未证实损坏', 'logs/host.txt'),
    ('tool', 'Vivado', '2022.2 SW 3671981 / IP 3669848', '/home/ghmd/Xilinx/Vivado/2022.2', '-', '-', '可启动；历史后置步骤失败', 'logs/vivado_version.txt;logs/xinstall_poststeps.txt'),
    ('tool', 'Vitis', '2022.2 SW 3671529', '/home/ghmd/Xilinx/Vitis/2022.2', '-', '-', '版本可辨；CLI 标志退出 255', 'logs/vitis_version.txt'),
    ('tool', 'Vitis HLS', '2022.2', '/home/ghmd/Xilinx/Vitis_HLS/2022.2', '-', '-', '存在；未独立运行', 'logs/tool_paths.txt'),
    ('tool', 'PetaLinux', '2022.2', '/home/ghmd/petalinux/2022.2', '-', '-', '安装日志成功；当前 PATH 未加载', 'logs/tool_paths.txt'),
    ('project', '原始 Vivado XPR', '2022.2 / xck26', '/home/ghmd/work/kv260_dpu/kv260_dpu.xpr', '-', '-', '输入引用存在；历史对照', 'logs/source_refs.txt'),
    ('project', 'B2304/URAM Vivado XPR', '2022.2 / DPU v4.1', '/home/ghmd/work/kv260_dpu_b2304_uram/kv260_dpu.xpr', '-', '-', '输入引用存在；历史候选', 'logs/source_refs.txt'),
    ('project', '9/26 clockfix XPR', '2022.2 / DPU v4.1', '/home/ghmd/kv260_clockfix_rebuild_20260926/kv260_dpu.xpr', '-', '-', '输入引用存在；未配套系统验收', 'logs/source_refs.txt'),
    ('project', 'PetaLinux KV260', '2022.2 / xilinx-k26-kv', '/home/ghmd/work/petalinux-kv260-dpu', '-', '-', '曾构建成功；当前引用中期 XSA', 'logs/petalinux_build_excerpt.txt;logs/artifact_hashes.tsv'),
    ('source', 'Vitis AI extracted copy', '3.0 label / commit unknown', '/home/ghmd/work/vitis-ai-source/Vitis-AI-3.0', '-', '-', '来源未验证', 'logs/vitis_ai_source_state.txt'),
    ('tool', 'Docker images', 'unknown', '/var/run/docker.sock', '-', '-', '未检查：避免启动服务', 'logs/docker_state.txt'),
]

labels = {
    'kv260_dpu.bit': ('old bit', '2022.2 / 100 MHz design', '历史对照'),
    'kv260_dpu.xsa': ('old XSA', '2022.2', '历史对照；ZIP 检查通过'),
    'kv260_dpu_clockfix.xsa': ('intermediate clockfix XSA', '2022.2', '当前 PetaLinux 硬件来源'),
    'kv260_dpu_clockfix_rebuilt.bit': ('new 9/26 bit', '2022.2', '实现完成；未集成'),
    'kv260_dpu_clockfix_rebuilt.xsa': ('new 9/26 XSA', '2022.2', 'ZIP 检查通过；未集成'),
    'system.xsa': ('PetaLinux imported XSA', '2022.2', '等同中期 clockfix XSA'),
    'kv260_dpu_clockfix.bit': ('PetaLinux hardware bit', '2022.2', '等同 XSA 内嵌 bit'),
    'system.bit': ('current candidate system.bit', '2022.2', '等同中期 XSA 内嵌 bit'),
    'system.dtb': ('current DTB', 'Linux 2022.2', '等同 FIT 内嵌 DTB'),
    'BOOT.BIN': ('current BOOT.BIN', 'bootgen 2022.2', '成员列表可读；字节同源待证'),
    'image.ub': ('current FIT image', 'Linux 2022.2', '内嵌内核/DTB/ramdisk 核对通过'),
    'rootfs.cpio.gz': ('current ramdisk', 'PetaLinux 2022.2', '等同 FIT 内嵌 ramdisk'),
    'resnet50_b2304.xmodel': ('old compiled model', 'Vitis AI 3.0 label', '历史模型候选'),
    'resnet50_b2304_verified.xmodel': ('9/26 compiled model', 'Vitis AI 3.0 label', '候选；板端未验收'),
    'arch.json': ('DPU architecture file', 'fingerprint 0x101000056010405', '静态配置；板端未验'),
}
with (aud/'logs/artifact_hashes.tsv').open() as f:
    for obj in csv.DictReader(f, delimiter='\t'):
        path = obj['path']
        name = Path(path).name
        label, version, status = labels[name]
        if name == 'system.xsa' and '/work/kv260_dpu_clockfix_hw/' in path:
            label = 'intermediate clockfix XSA copy'
        rows.append(('artifact', label, version, path, obj['size'], obj['sha256'], status, 'logs/artifact_hashes.tsv;logs/xsa_members.tsv'))

extra = {}
with (aud/'logs/extra_hashes.txt').open() as f:
    for line in f:
        sha, path = line.strip().split('  ', 1)
        extra[path] = sha
for kind, label, ver, path, size, status in [
    ('artifact', 'old routed DCP', 'Vivado 2022.2', '/home/ghmd/work/kv260_dpu_b2304_uram/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_routed.dcp', 73480348, '历史 reset 对照'),
    ('artifact', 'new routed DCP', 'Vivado 2022.2', '/home/ghmd/kv260_clockfix_rebuild_20260926/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_routed.dcp', 73503245, '存在；reset 语义待证'),
    ('source', 'DPU IP component.xml', 'v4.1.0', '/home/ghmd/work/dpu/DPUCZDX8G_ip_repo_VAI_v3.0/DPUCZDX8G_v4_1_0/component.xml', 1127022, '本地引用齐全；重复副本相同'),
    ('source', 'Vitis-AI-v3.0.zip', 'unknown', '/home/ghmd/work/Vitis-AI-v3.0.zip', 0, '已确认不完整（0 字节）'),
]:
    rows.append((kind, label, ver, path, size, extra[path], status, 'logs/extra_hashes.txt'))
rows.append(('image', 'AMD KV260 DPU 3.0.0 img.gz', '2022.2 / Vitis AI 3.0 label', '/home/ghmd/下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz', 3503938277, 'a8599cc033920207953a3eb954be1b925465e77c3ca835b26ef1ccfa903441d0', 'gzip 检查通过；官方校验未完成', 'logs/official_image_sha256.txt;logs/official_image_static.txt'))

with (aud/'INVENTORY.tsv').open('w', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['category', 'name', 'version', 'path_or_object', 'size_bytes', 'sha256', 'status', 'evidence'])
    w.writerows(rows)
