from common import *
import datetime
main=load(QA/'release_receipt.json')
audio=load(QA/'board_audio_archive.json')
skills=load(QA/'skills_archive.json')
dcp=load(QA/'routed_checkpoint.json')
staging=load(QA/'audio_stage_verification.json')
art={main['package']:main,audio['path']:audio,'auar_skills.zip':skills,dcp['name']:dcp}
assert main['contents']==len((ROOT/'checksums.sha256').read_text().splitlines())+1
steps=main['suite']['steps']; assert len(steps)==9 and all(x['exit_code']==0 for x in steps)
for name,entry in art.items():
    p=OUT/name
    assert p.is_file() and p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256'],name
(OUT/'SHA256SUMS.txt').write_bytes(''.join(v['sha256']+'  '+k+'\n' for k,v in art.items()).encode('ascii'))
note=f'''AUAR·雪妃　KV260 初级组自主命题工程交付
2026-11-02

交付文件
  auar_kv260_engineering.rar　主工程，RAR5，{main['bytes']:,} 字节，解压后 {main['contents']:,} 个文件，根目录 aura。
  auar_board_audio_dependencies.zip　板端语音依赖，ASR、前端、VAD、CPU 声纹模型及 ARM64 wheel 的 15 个锁定文件。
  auar_skills.zip　三位子智能体整理的运动命令保护、三模型感知时效、语音大模型运行优化，另附已有的通用 PYNQ 工具。内容也在主包的 skill 目录中。
  auar_wide_source_routed.dcp　Ubuntu 上的原版 wide 已布线检查点，供 Vivado 2022.2 快速重新导出 XSA。主包保留从源码构建所需的前版增量参考 DCP。
  SHA256SUMS.txt　以上四个文件的 SHA-256。
  verification　Ubuntu 解包复测、Vivado 建工程和导出、音频暂存及固件比对的记录。
  aura　主包对应的可直接浏览版。

低核 Ubuntu 20.04 使用顺序
将所需文件放在同一目录。复制全部四件时可运行 sha256sum -c SHA256SUMS.txt。可用支持 RAR5 的 unrar 解压，运行 unrar x auar_kv260_engineering.rar。也可直接复制此处的 aura 目录。
进入解压出的 aura 后执行
  python3 -B build/scripts/reproduce.py --out "$HOME/auar-check-01"
请使用新的输出目录。此步骤只用 Python 3.8+ 标准库，一个 CPU 核心即可。实际复跑使用 Ubuntu 20.04.4、Python {main['python']}，以 CPU affinity 固定到单核，{len(steps)} 项全部返回 0。

复算性能见 report/performance_addendum.txt 和 data/results/performance。三模型的工件实读结果在 data/results/xir_three_models.json；四套 RTL 的实跑仿真见 sim、data/results/xsim、skill/command_guard_validation。
若用原布线检查点快速导出，请先载入 Vivado 2022.2，在 aura 目录执行
  python3 -B build/scripts/fpga.py export --checkpoint ../auar_wide_source_routed.dcp --out "$HOME/auar-xsa-01"
提取固件的下一步见 build/readme.md。已从此检查点重新导出并核对四个板端工件，SHA-256 与原发布相同。本轮未从头再跑综合布线。

准备板端部署时，保留音频 ZIP 在 aura 旁边，在 aura 目录执行
  python3 -B board/scripts/stage.py --audio ../auar_board_audio_dependencies.zip --out "$HOME/auar-rootfs-01"
该入口在本次验证中生成 {staging['rootfs_files']:,} 个暂存文件，15/15 音频依赖的落盘哈希一致。可选的 --image-root /mnt/kv260-original 只从另行挂载的原卡镜像读取清单内 SHA 完全匹配的文件。详见 board/readme.md。Windows 模型准备方法见 src/windows/readme.md，27B 和 OmniVoice 权重按固定版本另备。

验收范围
工程完整性、离线回归、Vivado 建工程和从原检查点导出已复验。空白卡冷启动还需实物验证。7 个历史相机校验项、1 个现役原生库，以及 3 段固定提示音和清单的原件见 board/config/image_inputs.json。归档保留对应的哈希以及可取得的原生源码、目标文件和提示音生成步骤。个人数据库和真实登记样本留在原机。移动残影及自动向右偶发抖动保留现场反馈。180 秒窗口为性能采样，三分钟整机全功能同时运行须另验。
面向参赛公开提交时，以 report/release_status.md、performance_addendum.txt 区分历史与本轮结果。角色美术的公开再分发授权、队伍开源声明和仓库地址由队伍核定。
'''
(OUT/'先读_交付与核验.txt').write_text(note,encoding='utf-8-sig')
receipt={'status':'VERIFIED_ENGINEERING_HANDOFF','verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'windows_folder':str(OUT),'basis':'E: project records and Ubuntu ghmd engineering sources, historical records and original archived SD rootfs','artifacts':{n:{k:v[k] for k in ['bytes','sha256']} for n,v in art.items()},'main_files':main['contents'],'ubuntu':'20.04.4 LTS','cpu_affinity':1,'offline_workflow_steps':len(steps),'board_audio_verified':staging['audio_files_matched'],'physical_actions':False,'new_full_place_and_route':False,'new_full_3min_physical_acceptance':False,'original_image_inputs':12}
save(B/'engineering_delivery_20261102/ENGINEERING_PACKAGE_DELIVERED.json',receipt)
print('4 artifacts verified', main['bytes'], main['sha256'])
remote="""import os,fcntl
from pathlib import Path
p=Path.home()/'AMD_Smart/logs/daily/2026-11-02.md'
tag='[auar-engineering-delivery-20261102-'+HASH[:12]+']'
line='\\n## AUAR 工程交付归档 '+tag+'\\n\\nE 盘主包 auar_kv260_engineering.rar，'+str(SIZE)+' 字节，SHA-256 '+HASH+'。Ubuntu 20.04.4、Python 3.8.10、单核解压复跑 9 步均通过。380 项业务文件、25 项跟随文件、3 份实际部署的 DPU 模型、五对 LLM/TTS 性能采样及 3 个专项技能均已归档。4 项板端固件从原 wide 已布线检查点导出后与原发布 SHA 完全相符。另附原 DCP。本版取代本日较早归档，补齐三个可发现的技能入口并单测独立 ZIP。未更改实板。\\n'
with p.open('a+',encoding='utf8') as f:
    fcntl.flock(f,fcntl.LOCK_EX); f.seek(0)
    if tag not in f.read():
        f.write(line);f.flush();os.fsync(f.fileno())
print('daily entry recorded')
"""
print(ssh(remote.replace('HASH',repr(main['sha256'])).replace('SIZE',str(main['bytes']))).strip())
