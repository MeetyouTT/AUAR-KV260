# 380 项主清单之外的 31 组依赖

本表复核上一轮取件审查的全部组。原始运行输入和可重建源码按各自用途登记。

| 编号 | 交付或取得方式 | 核验范围 | 包内依据 |
|---|---|---|---|
| D04 | 4 份默认设置和离线落盘 | 原读写器回读；正式入口只读配对通过 | board/settings；board/stage.py |
| CAM1 | 单独的相机运行根 | 224 项逐文件校验；与主根 39 处同名差异分别保留 | board/camera_release.json；src/camera/runtime |
| H01 | 独立历史主机布局 | 45 个启动映射，含两处同名差异；在 Ubuntu 离线还原，未在 Windows 启动 GPU 服务 | board/deploy.json 的 host_files |
| C01 | 32 份主配置和 5 份 Windows 配置映射 | 按原件还原或显式填写类型化字段；现场生成会改变启动 SHA | src/config/readme.md；build/env.json |
| C02 | 私有区及当前开机绑定由现场建立 | 原件校验源码随包，原用户数据库、密钥、当前 camera/boot 绑定不收录 | src/board/runtime；board/readme.md |
| G03 | overlay 源、脱敏底图与真实底图 SHA | dtc 编译，两种底图的真实合并均通过，未在板端加载 | src/fpga/overlay；board/system |
| G04 | 8 段 XRT 元数据和原容器 SHA | 重建容器后 8 段逐段回读；另支持指定原始容器 | src/fpga/xrt_metadata |
| N04 | R4 源及完整 CMake 链 | Ubuntu 上从源码交叉编译 libaura_yuki.so；正式旧库已按固定 SHA 随本版收录 | src/native/avatar；build/build_native.sh |
| N03 | 两个 VART 原生候选 | operator、v2 两个库从各自的 C++ 源重建 | src/camera/native_operator；src/camera/native_v2 |
| M01 | 2 个 ONNX，3 个目标 xmodel 输入锁 | ONNX 实测 SHA；指定目标镜像可取得 YOLOX，另外两图提供量化编译入口 | src/models/readme.md；board/deploy.json |
| A01 | 2 帧色条样例与包内正式五件素材 | 样例通过原读取器；用已持有原件完成正式角色哈希预检，本版安装器已从包内直接取用五件素材及匹配渲染库 | src/assets/readme.md；board/release_9a4f.json |
| D02 | SD 整镜像及内核、目标 ABI 固定 | 记录镜像和分区；从原 EXT4 开发文件完成交叉构建；未烧写或冷启动设备 | board/system/image_manifest.json；build/prepare_cross_sdk.py |
| G02 | 4 份真实 TB 与 RTL 证据门禁 | 4×3 步骤及反向拒绝测试，详情见验证摘要 | sim/rtl/run.tcl；build/rtl_results.py |
| G01 | RTL、两份自定义 IP、DPU、BD 与 XDC | Vivado 2022.2 从空输出建工程；综合及实现数值见验证摘要 | build/build.tcl；src/fpga |
| G05 | 固件配对、Bootgen 及产物导出 | 原发布交叉验证与本轮新实现输出分别列于验证摘要 | build/export_firmware.py；build/bitstream_pairing.py |
| M02 | 真实适配/量化/编译脚本及容器锁 | 本轮执行阶段见验证摘要；LFW 数据与包含人脸像素的向量保留在包外 | build/prepare_models.py；src/models/calibration |
| M04 | 15 个语音输入锁 | 用原独立附件的全部 15 项完成校验和离线落盘 | src/models/inputs/board_audio_dependencies.json |
| M03 | 27B、OmniVoice 输入锁、合成参考音 | 整模型在包外；离线主机布局验证通过，GPU 生成和音频实测需在对应环境中完成 | src/models/inputs；src/host/model_service |
| D01 | 2 份 systemd 单元与 56 份 drop-in | 33 + 23 份按实际加载顺序检查，离线安装通过 | board/systemd；board/deploy.json |
| CAM2 | 入口链、预检和版本绑定 | 相机入口及预检的引用文件在离线根逐项检查；实际摄像头尚待启动 | src/camera/entry_chain/source_paths.json |
| D03 | 历史映射 1131 个目的地 | 加入运动等增补映射后共有 1156 个目标；同内容文件可复用一个包内源 | board/deploy.json 的 mapping |
| N05 | 25 项单轴控制部署清单，MMIO 和轨迹源码 | 两个 MMIO 库与轨迹库完成交叉编译；执行器未动作 | src/motion/follow；src/motion/trajectory_src |
| N01 | YOLOX AArch64 桥接源码 | 使用目标 OpenCV、Vitis AI Library 与 glog 完成链接 | src/board/vision/native |
| N02 | 像素、缩放与视频输出原生源码 | 链接目标 OpenCV 与 GStreamer 后完成 AArch64 构建 | src/tools/native_pixels.cpp |
| A03 | 3 段固定提示音及反馈清单 | 公开提示音保留原 SHA，按原部署映射落盘 | src/assets/public_cues |
| A02 | Droid 字体、ByteTrack 许可与测试图输入锁 | 字体与源码许可随包；历史 person_bus.jpg 按 SHA 从包外取得 | src/assets/fonts/licenses；src/board/vision/bytetrack |
| PY01 | 5 个迁移依赖模块 | device_memory、memory_controls 及三个 timeline 模块均在原导入路径 | src/common |
| F01 | 框架 CLI、模拟配置、golden 与原测试 | Ubuntu 重新运行 doctor 与合成业务 demo | src/tools/aura_project.py；src/data/golden |
| T01 | 原 ID/STOP 验收脚本和 4 项配套输入 | 可还原受控验收目录；缺省只打印计划，实板操作未执行 | src/tests/bench_identity_stop.py；board/bench.json |
| S01 | 比赛 PYNQ Skill 原包 28 件 | Ubuntu 重跑 15 个单测和 73 个 mock 用例；实板和跨板未测 | skill/README.md |
| R01 | 既有权利说明、归属、18 条历史指标及新回执 | 根许可沿用原件；正式公开授权、正式技术文档与实物材料由队伍决定 | license；data/metrics.csv；report/validation_summary.md |
