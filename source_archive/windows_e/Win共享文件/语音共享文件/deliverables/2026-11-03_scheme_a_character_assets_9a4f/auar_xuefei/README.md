# AUAR · 雪妃工程包（含正式角色素材）

本版以 KV260 正式对话运行清单 `9a4f06da6035f62d1fafad1af71f61553b9e8656e62ef9b9a628adff0edabc15` 为基线。Windows 和 Ubuntu 两侧原件按 SHA-256 归并到一个工程。379 项共同组件中，371 项取自之前的同版交付，8 项取自较新专项。对话模块取正式版 `ad47213a…`。临时思考版 `71431dc7…` 与其对话模块 `88b9d6e2…` 只在差异表中登记。

## 在 Ubuntu 上复验

解开 RAR，进入唯一根目录 `auar_xuefei`。输出目录应位于源码树之外且内容全新。下面的路径适用于本次验证用的 Ubuntu 机器。

```sh
sha256sum --quiet -c checksums.sha256
export VIV="$HOME/Xilinx_2022.2/Vivado/2022.2"
export VIT="$HOME/Xilinx_2022.2/Vitis/2022.2"
export OUT="$HOME/auar-rebuild-$(date +%Y%m%d-%H%M%S)"
python3 -B build/reproduce.py --out "$OUT" --stage all --vivado "$VIV/bin/vivado" --vitis-root "$VIT"
```

`all` 顺序执行框架自检和演示、比赛 Skill、四个 XSim 测试台、Vivado 建立工程、综合实现和 BIT/XSA 导出。若只核验硬件，使用 `--stage hardware`。单独运行 RTL 和建工程可以复用同一个新输出目录。

```sh
python3 -B build/reproduce.py --out "$OUT" --stage rtl --vivado "$VIV/bin/vivado"
python3 -B build/reproduce.py --out "$OUT" --stage prepare --vivado "$VIV/bin/vivado" --vitis-root "$VIT" --rtl-results "$OUT/rtl/result.json"
python3 -B build/reproduce.py --out "$OUT" --stage implement --vivado "$VIV/bin/vivado" --vitis-root "$VIT" --rtl-results "$OUT/rtl/result.json"
```

二选一执行上述构建流程。已存在阶段回执时，入口会拒绝覆盖。RTL 阶段逐项保存 xvlog、xelab、xsim 的命令、退出码、日志 SHA 与通过标记。硬件入口还核对源码指纹、实际路由完成度、时序和 DRC。`report/validation_summary.md` 对应本轮实际结果。

## 固件、模型与原生库

```sh
export DTC17="$HOME/kv260-dpu41-control-20261001/dependencies/dtc-1.7.2"
export LD_LIBRARY_PATH="$DTC17/libfdt${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python3 -B build/export_firmware.py --out "$OUT/firmware" \
  --bit "$OUT/hardware/auar_source.bit" --xsa "$OUT/hardware/auar_source.xsa" \
  --base-dtb "$HOME/aura-system-pan-20261028/fresh-base.dtb" \
  --dtc "$VIT/bin/dtc" --fdtoverlay "$DTC17/fdtoverlay" \
  --xclbinutil "$VIT/bin/xclbinutil" --bootgen "$VIT/bin/bootgen"
python3 -B build/prepare_models.py check
python3 -B build/check_assets.py
```

只验证 overlay 与 XRT 元数据时使用 `--metadata-only`，省略 `--bit` 与 `--xsa`。省略 `--base-dtb` 会使用包内脱敏底图做合并测试。主机上有已备份的 KV260 EXT4 分区时，可直接从匹配的头文件和库交叉编译 8 个 AArch64 原生库。

```sh
python3 -B build/prepare_cross_sdk.py \
  --rootfs "$HOME/kv260-sd-backup-20261003/offline-inspection/root.original.ext4" \
  --vitis-root "$VIT" --out "$OUT/cross-sdk" --build-out "$OUT/native"
```

## 工程入口

| 路径 | 用途 |
|---|---|
| `src/board`、`src/host`、`src/common`、`src/ui`、`src/tools` | 原 aura 运行根的同级模块，含正式业务、GUI、协议及历史主机推理入口 |
| `src/camera`、`src/motion` | 独立相机命名空间与原始入口链、转轴控制和本地驱动源码 |
| `src/fpga`、`src/third_party/dpu`、`sim/rtl` | KV260 BD、IP、约束、RTL 和四个测试台 |
| `src/models`、`src/native`、`src/assets` | 固定模型输入、适配代码、原生实现及可分发样例 |
| `board` | 真实部署位置、systemd 顺序、模板、外置输入清单和离线安装入口 |
| `skill/pynq-contract-testgen` | 比赛 Skill 的 28 个原文件及复现命令 |
| `report`、`data/metrics.csv` | 本次验证、原件取件记录、31 组清单外依赖、技术说明索引及历史运行数据 |

执行 `sh board/install.sh plan` 可查看设备现场字段和所需外置原件。正式角色的五件运行素材及匹配的 ARM64 渲染库已随包收录，详见 `src/assets/yuki/readme.md`。原始 27B 权重、整张 SD 卡和运行时个人数据仍按原外置依赖清单准备。离线安装和板机验收步骤见 `board/readme.md`。原板端镜像包含 Python 3.9。正式角色入口使用 Python 3.9 的 Path API，Ubuntu 的框架自检可使用 Python 3.8。历史主机服务为独立 Windows GPU 服务，端口 8797。本次工程构建和打包环境是 Ubuntu。

队伍原创内容沿用根目录 `license` 的权利说明，第三方各项见 `third_party_notices.md`。正式技术文档可从 `report/design_report.md` 和本次验证回执取数。


## 上板资料与实测对照补充

本版新增 board/bringup/readme.md 的上板准备顺序、只读安装检查、成套FPGA产物归集及两个合成输入采集入口。board/evidence 保存三组按版本登记的真实历史板端记录，board/evidence_sources.json 对应原件/公开副本SHA，data/board_reference 提供对照与确定性合成输入。

在工程根运行 python3 -B board/verify_evidence.py --out <包外新目录>，可得到逐项 comparison.json / comparison.csv。新固件与历史测量的覆盖范围在 board/evidence_index.json 和 report/board_evidence_summary.md 中列明。包内 board/artifacts_candidate 为本轮新建的6件固件/硬件产物，尚待独立目标板验收。

## 正式角色素材补入

本版新增雪妃5件正式素材和匹配的ARM64渲染库，安装映射已改为从包内取件；9a4f启动清单的380项内容SHA保持一致。可执行 python3 -B build/check_character_assets.py 核对素材和11项配对引用。此补充没有新增目标板显示验收。
