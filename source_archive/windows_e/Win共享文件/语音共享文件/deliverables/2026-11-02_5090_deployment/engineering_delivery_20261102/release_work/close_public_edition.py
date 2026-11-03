from common import *
import datetime
manifest=load(ROOT/'board/config/public_board_resources.json')
capture=load(QA/'board_public_copy.json')
replay=load(QA/'board_public_runtime_replay.json')
core=load(QA/'release_receipt.json')
staging=load(QA/'audio_stage_verification.json')
assert replay==core['public_consumers'] and replay['result']=='PASS'
assert len(replay['fixed_prompts'])==3 and replay['camera_ExecStartPre_passed']==20
assert core['cpu_affinity']==1 and core['rar_test']==core['verify_after_unpack']=='PASS'
assert core['contents']==len((ROOT/'checksums.sha256').read_text(encoding='utf8').splitlines())+1
assert len(core['suite']['steps'])==9 and all(s['exit_code']==0 for s in core['suite']['steps'])
assert 'Public KV260 files verified: 201 destinations' in (QA/'windows_stage_with_audio.txt').read_text(encoding='utf-8-sig') and staging['audio_files_matched']==15
assets=load(ROOT/'data/reference/public_feedback.json')['assets']
for a in assets:
    k=a['name'];b=replay['fixed_prompts'][k];assert b['sha256']==a['sha256'] and b['duration_seconds']==a['duration_seconds']
arts={core['package']:core,'auar_board_audio_dependencies.zip':load(QA/'board_audio_archive.json'),'auar_skills.zip':load(QA/'skills_archive.json'),'auar_wide_source_routed.dcp':load(QA/'routed_checkpoint.json')}
for n,info in arts.items():
    p=OUT/n;assert sha(p)==info['sha256'] and p.stat().st_size==info['bytes']
(OUT/'SHA256SUMS.txt').write_bytes(''.join(v['sha256']+'  '+n+'\n' for n,v in arts.items()).encode('ascii'))
note=f'''AUAR·雪妃　KV260 初级组自主命题工程交付
2026-11-02　含板上公开资源的更新版

交付文件
  auar_kv260_engineering.rar　主工程，RAR5，{core['bytes']:,} 字节，解压后 {core['contents']:,} 个文件。
  auar_board_audio_dependencies.zip　板端 ASR、音频前端、VAD、CPU 声纹模型和 ARM64 wheel，共 15 个锁定文件。
  auar_skills.zip　运动命令保护、三模型感知时效、语音大模型运行优化。三套专题技能已在单核 Ubuntu 上单独复跑；另附已有的通用 PYNQ 工具。
  auar_wide_source_routed.dcp　原版 wide 已布线检查点，可用 Vivado 2022.2 跳过综合布线直接导出。
  SHA256SUMS.txt　上述四件交付物的 SHA-256。verification 保存解包、硬件工程导出、模型/技能以及板上公开资源的核验记录。aura 为可直接浏览的工程树。

这次从 KV260 补回了什么
  三段已选音色的原始系统提示音和 feedback.json 位于 aura/board/public_cues。问候 2.66 秒、邀请 2.28 秒、思考 1.79 秒，均为 24 kHz 单声道 16 位 PCM。
  上版待从原卡补入的 12 项已逐项核对并随主 RAR 交付，包括 7 个历史相机校验项、现役相机原生共享库和这 4 个语音文件。
  界面和相机的两个原始 systemd 服务及 56 份已加载追加配置已归档。相机启动前的 20 道文件校验会引用 {replay['public_inputs']} 个不同文件。文件清单与原部署路径为 aura/board/config/public_board_resources.json。
  从这份 RAR 解压后，在隔离的 Ubuntu 暂存树中执行了原版 20 道文件校验，并用界面和语音业务的原版提示音读取代码加载三段 WAV。结果在 verification/board_public_runtime_replay.json。实板操作仅限读取公开发布文件和启动配置，未采集录音或访问个人数据。

另一台低核 Ubuntu 20.04
  四个交付件和 SHA256SUMS.txt 放在同一目录时，可运行 sha256sum -c SHA256SUMS.txt 校验传输。
  用支持 RAR5 的 unrar 执行 unrar x auar_kv260_engineering.rar，或直接从此处复制 aura。进入 aura 后执行
    python3 -B build/scripts/reproduce.py --out "$HOME/auar-check-01"
  请使用新的输出目录。复核只需 Python 3.8+ 标准库。本次从最终压缩包解压，在 Ubuntu 20.04.4、Python {core['python']}、单个 CPU 核心上运行，9 项检查均通过。
  准备板端文件时将板端音频 ZIP 留在 aura 旁，在 aura 内执行
    python3 -B board/scripts/stage.py --out "$HOME/auar-rootfs-01" --audio ../auar_board_audio_dependencies.zip
  已核对生成的 {staging['rootfs_files']:,} 个暂存文件及 15/15 音频依赖的落盘哈希。三段提示音来自主 RAR，默认暂存就能放回原路径。独立复跑原版读取代码需 Linux 用户命名空间及 bubblewrap，用法见 board/readme.md。
  载入 Vivado 2022.2 后可从原检查点导出
    python3 -B build/scripts/fpga.py export --checkpoint ../auar_wide_source_routed.dcp --out "$HOME/auar-xsa-01"
  从该检查点导出的四个板端固件与原版逐字节一致。FPGA 全量构建见 build/readme.md。Windows 的 27B 和 OmniVoice 外部权重按固定版本准备，入口见 src/windows/readme.md。

工程与实机验收
  性能采样和覆盖范围见 report/performance_addendum.txt 与 report/release_status.md。本次为只读收录及离线复验，空白卡冷启动和三分钟全功能同时运行仍须实物验证；移动残影与自动向右偶发抖动保留原现场记录。公开发布前，队伍需确认角色美术再分发授权、团队开源声明和仓库地址。
'''
(OUT/'先读_交付与核验.txt').write_text(note,encoding='utf-8-sig')
receipt={'status':'VERIFIED_ENGINEERING_HANDOFF_WITH_BOARD_PUBLIC_FILES','verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'windows_folder':str(OUT),'basis':'E: project, Ubuntu ghmd home and immutable disk image, read-only matched public files from KV260','artifacts':{n:{k:v[k] for k in ['bytes','sha256']} for n,v in arts.items()},'main_files':core['contents'],'ubuntu':'20.04.4 LTS','cpu_affinity':1,'offline_workflow_steps':9,'board_audio_verified':15,'physical_actions':False,'new_full_place_and_route':False,'new_full_3min_physical_acceptance':False,'original_image_inputs_bundled':12,'outstanding_from_original_12':0,'public_file_destinations':len(manifest['files']),'previous_release_sha256':'38e16a219ee638df788607a2bd741a5e8d7a8264e5e174d5bb69cab007e14dfc','board_replay':replay}
save(B/'engineering_delivery_20261102/ENGINEERING_PACKAGE_DELIVERED.json',receipt)
line='本版更新 KV260 只读授权的公开文件，主 RAR 为 '+str(core['bytes'])+' 字节，SHA-256 '+core['sha256']+'。上版列出的 12 项原件均已收录。Ubuntu 解包单核 9 项通过；隔离暂存树原版相机 ExecStartPre 20/20（135 个文件），界面及业务提示音 3/3。未登录私库，未操作设备。'
remote="""from pathlib import Path
import fcntl,os
f=Path.home()/'AMD_Smart/logs/daily/2026-11-02.md'
tag=TAG
with f.open('a+',encoding='utf8') as fp:
    fcntl.flock(fp,fcntl.LOCK_EX);fp.seek(0)
    if tag not in fp.read():
        fp.write('\\n## AUAR 板端公开文件工程交付 '+tag+'\\n\\n'+NOTE+'\\n');fp.flush();os.fsync(fp.fileno())
print('daily receipt verified')"""
print(ssh(remote.replace('TAG',repr('[auar-public-'+core['sha256'][:12]+']')).replace('NOTE',repr(line))).strip())
print(core['bytes'],core['contents'],core['sha256'],'staged',staging['rootfs_files'])
