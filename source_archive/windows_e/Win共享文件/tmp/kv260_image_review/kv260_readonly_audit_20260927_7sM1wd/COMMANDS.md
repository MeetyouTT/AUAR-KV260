# 实际采集命令与退出状态

## host

```sh
date -Is; cat /etc/os-release; uname -a; free -h; lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,MODEL; findmnt -T /home/ghmd -o TARGET,SOURCE,FSTYPE,OPTIONS; df -hT /home/ghmd; df -i /home/ghmd
```

退出状态：0。输出：`logs/host.txt`。

## package_state

```sh
dpkg --audit; dpkg-query -W 2>/dev/null | rg "^(build-essential|gcc|g\+\+|make|git|python3|libncurses5|libncurses5-dev|libtinfo5|libssl-dev|zlib1g-dev|flex|bison|diffstat|chrpath|socat|xterm|texinfo|gcc-multilib|libc6-dev-i386|docker-ce|docker.io|qemu-user-static|device-tree-compiler|u-boot-tools|python3-numpy)[[:space:]]"; readlink -f /bin/sh
```

退出状态：0。输出：`logs/package_state.txt`。

## package_verify

```sh
dpkg -V bash coreutils dpkg libc6 libstdc++6 gcc g++ make git python3 zlib1g 2>&1
```

退出状态：0。输出：`logs/package_verify.txt`。

## host_errors

```sh
journalctl -k -b --no-pager 2>&1 | rg -i "I/O error|EXT4-fs error|nvme.*error|out of memory|oom-kill|killed process|no space left|read-only file system" | tail -100; journalctl --no-pager -p err -b 2>&1 | tail -100
```

退出状态：0。输出：`logs/host_errors.txt`。

## tool_paths

```sh
command -v vivado || true; command -v vitis || true; command -v petalinux-build || true; command -v docker || true; find /home/ghmd/Xilinx/Vivado/2022.2 /home/ghmd/Xilinx/Vitis/2022.2 /home/ghmd/Xilinx/Vitis_HLS/2022.2 /home/ghmd/petalinux/2022.2 -maxdepth 3 -type f \( -name vivado -o -name vitis -o -name petalinux-build -o -name settings64.sh -o -name settings.sh -o -name version.txt \) -printf "%p %s\n" 2>/dev/null; cat /home/ghmd/petalinux_installation_log
```

退出状态：0。输出：`logs/tool_paths.txt`。

## xilinx_install

```sh
rg -in "(success|complete|error|fail|warning|device|installing|installed)" /home/ghmd/Xilinx/.xinstall/Vitis_2022.2/xinstall.log | tail -100; cat /home/ghmd/Xilinx/.xinstall/Vitis_2022.2/data/version.dat; find /home/ghmd/Xilinx/Downloads/Vivado_2022.2 -maxdepth 2 -type f -printf "%p %s\n" | head -60
```

退出状态：0。输出：`logs/xilinx_install.txt`。

## petalinux_config

```sh
rg -n "(CONFIG_SUBSYSTEM|CONFIG_YOCTO|CONFIG_PETALINUX|CONFIG_ARCH|XSA|2022\.2|HDF)" /home/ghmd/work/petalinux-kv260-dpu/project-spec/configs/config /home/ghmd/work/petalinux-kv260-dpu/config.project /home/ghmd/work/petalinux-kv260-dpu/.petalinux/metadata 2>/dev/null | head -150; find /home/ghmd/work/petalinux-kv260-dpu -maxdepth 4 -type f \( -name "*.xsa" -o -name "*.hdf" -o -name "*.bif" -o -name "*.dtb" -o -name "*.bit" -o -name "image.ub" -o -name "BOOT.BIN" \) -printf "%p %s %TY-%Tm-%TdT%TH:%TM\n" | head -120
```

退出状态：0。输出：`logs/petalinux_config.txt`。

## build_errors

```sh
rg -in "(error:|fatal:|failed|No space left|No such file|permission denied|killed|out of memory|fetcher failure|do_fetch|checksum mismatch|completed successfully|build succeeded)" /home/ghmd/work/petalinux-kv260-dpu/petalinux-build.log /home/ghmd/work/*build.log 2>/dev/null | tail -180
```

退出状态：0。输出：`logs/build_errors.txt`。

## docker_state

```sh
systemctl is-active docker.service docker.socket 2>&1; if [ "$(systemctl is-active docker.service 2>/dev/null)" = active ]; then docker image ls --digests --no-trunc 2>&1 | head -80; fi
```

退出状态：0。输出：`logs/docker_state.txt`。

## source_state

```sh
git -C /home/ghmd/work/vitis-ai-source/Vitis-AI-3.0 rev-parse --is-inside-work-tree HEAD 2>&1; git -C /home/ghmd/work/vitis-ai-source/Vitis-AI-3.0 status --short 2>&1 | head -30; stat -c "%n %s bytes" /home/ghmd/work/Vitis-AI-v3.0.zip; find /home/ghmd/work/models -maxdepth 4 -type f \( -name "*.json" -o -name "*.xmodel" -o -name "*.log" \) -printf "%p %s\n" | head -100
```

退出状态：0。输出：`logs/source_state.txt`。

## project_sources

```sh
find /home/ghmd/work/kv260_dpu /home/ghmd/work/kv260_dpu_b2304_uram /home/ghmd/kv260_clockfix_rebuild_20260926 /home/ghmd/work/dpu -maxdepth 4 -type f \( -name "*.xpr" -o -name "*.bd" -o -name "*.xdc" -o -name "component.xml" -o -name "*.xci" -o -name "*.tcl" \) -printf "%p %s\n" | head -180; rg -n "(DPUCZDX8G|DPU_CLK_MHz|FREQ_HZ|ip_repo|part=|board_part|21000000|80000000)" /home/ghmd/work/kv260_dpu/kv260_dpu.xpr /home/ghmd/work/kv260_dpu_b2304_uram/kv260_dpu.xpr /home/ghmd/kv260_clockfix_rebuild_20260926/kv260_dpu.xpr 2>/dev/null | head -120
```

退出状态：0。输出：`logs/project_sources.txt`。

## image_files

```sh
find /home/ghmd/work/petalinux-kv260-dpu/images/linux /home/ghmd/work/petalinux-kv260-dpu/sd-card-staging-dpu-clock-fixed-numpy-sdmmc-nfsd-gem3 /home/ghmd/work/kv260_dpu_b2304_uram/output /home/ghmd/kv260_clockfix_rebuild_20260926/artifacts -maxdepth 2 -type f -printf "%p %s %TY-%Tm-%TdT%TH:%TM\n" 2>/dev/null | head -180; cat /home/ghmd/work/petalinux-kv260-dpu/images/linux/bootgen.bif
```

退出状态：0。输出：`logs/image_files.txt`。

## 补充的只读命令

下表记录在审查目录内运行的主要补充命令。上述 `collect.sh` 的总退出状态为 0；其中若复合命令末尾成功，不能把中间子命令也算作成功。例如 `source_state` 内两次 Git 查询各自失败，`docker_state` 的 `systemctl` 查询失败。报告按原始输出逐项解释。

| 实际命令或调用 | 退出状态 | 输出与限制 |
|---|---:|---|
| `lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,MODEL` | 1 | 本机 `lsblk` 不支持 `MOUNTPOINTS` 列；随后在 `host` 采集改用 `MOUNTPOINT`，退出 0。没有磁盘读写。 |
| `sha256sum /home/ghmd/下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz` | 0 | `logs/official_image_sha256.txt`。 |
| `gzip -t /home/ghmd/下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz` | 0 | 静默成功；未与官方哈希比较。 |
| `python3 inspect_artifacts.py` | 0 | 生成 `logs/artifact_hashes.tsv`、`logs/xsa_members.tsv`、`logs/official_image_partition_header.txt`；只读源文件。XSA 使用 Python `zipfile.testzip()`。 |
| `python3 inspect_fit_rootfs.py` | 0 | 生成 `logs/fit_members.txt`、`logs/rootfs_runtime.txt`；mmap 只读 FIT，读取 rootfs tar 成员和 vermagic，没有解包到原工程。 |
| `python3 inspect_official_image.py` | 0 | 生成 `logs/official_image_static.txt`；只读 gzip 解压流前约 79 MB，没有完整展开镜像。 |
| `python3 check_sources.py` | 0 | 生成 `logs/source_refs.txt`；读取 XPR/XML，核对路径，不打开项目或运行工程脚本。 |
| Python `zipfile` 读取三个 XSA 的 `kv260_dpu_bd.hwh`，正则筛选 DPU 时钟端口与基地址 | 0 | `logs/xsa_clock_ports.txt`；只读 XSA 成员。 |
| `diff -qr /home/ghmd/work/dpu/DPUCZDX8G_ip_repo_VAI_v3.0/DPUCZDX8G_v4_1_0 /home/ghmd/kv260_clockfix_rebuild_20260926/ip_repo/DPUCZDX8G_ip_repo_VAI_v3.0/DPUCZDX8G_v4_1_0` | 0 | `logs/ip_repo_diff.txt` 为空：所比较树逐文件相同。 |
| `env HOME=审查目录 XILINX_LOCAL_USER_DATA=审查目录 TMPDIR=审查目录 timeout 30 /home/ghmd/Xilinx/Vivado/2022.2/bin/vivado -version` | 0 | `logs/vivado_version.txt`；工具可启动。 |
| `env HOME=审查目录 XILINX_LOCAL_USER_DATA=审查目录 TMPDIR=审查目录 timeout 30 /home/ghmd/Xilinx/Vitis/2022.2/bin/vitis -version` | 255 | `logs/vitis_version.txt` 打印版本；标志/启动器返回非零，未当作整体损坏证据。 |
| `env HOME=审查目录 TMPDIR=审查目录 timeout 30 /home/ghmd/Xilinx/Vitis/2022.2/bin/bootgen -arch zynqmp -read /home/ghmd/work/petalinux-kv260-dpu/images/linux/BOOT.BIN` | 0 | `logs/bootgen_read.txt`；只读成员头，不证明每个成员字节与 BIF 输入相同。 |
| `/home/ghmd/Xilinx/Vitis/2022.2/bin/dtc -I dtb -O dts -o 审查目录/logs/system.dts images/linux/system.dtb` | 0 | `logs/system.dts`、`logs/dtc_stderr.txt`；仅写审查目录。 |
| `env HOME=审查目录 XILINX_LOCAL_USER_DATA=审查目录 TMPDIR=审查目录 timeout 180 vivado -mode batch -source 审查目录/query_reset.tcl -log 审查目录/logs/reset_vivado.log -journal 审查目录/logs/reset_vivado.jou` | 124 | `logs/reset_vivado.stdout`；已读 OOC、synth DCP，未完成所有 DCP 查询，超时不等于文件损坏。 |
| `journalctl -k --since 2026-09-17 --no-pager` 后用 `rg` 筛选 I/O、ext4、OOM 词 | 0（筛选有一行） | `logs/kernel_storage_oom_matches.txt` 仅有 ext4 挂载选项行。 |
| 对现存构建日志运行 `rg` 筛选 `No space left`、OOM、`ERROR:` 等 | 1（无匹配） | `logs/build_fail_matches.txt` 空；只覆盖列入的顶层构建日志。 |
| 对原安装日志执行 `sed -n '12850,12864p;13025p'` | 0 | `logs/xinstall_poststeps.txt`；仅保留相关行，未附可能含凭据的完整安装日志。 |
| `dpkg-query -W -f='${Package} ${Status} ${Version}\n' libncurses5 libncurses5-dev libtinfo5 libssl-dev zlib1g-dev flex bison socat device-tree-compiler u-boot-tools` | 1 | `logs/dependency_status.txt`；非零因几个包未找到。 |
| `git -C /home/ghmd/work/vitis-ai-source/Vitis-AI-3.0 rev-parse --is-inside-work-tree HEAD` | 128 | `logs/vitis_ai_source_state.txt`；该目录不是 Git checkout。 |
| `sha256sum` 对旧/新 routed DCP、IP `component.xml`、0 字节 zip | 0 | `logs/extra_hashes.txt`。 |
| `cp -n` 复制三份既有 Vivado reset 查询原始输出到审查目录，随后 `sha256sum` 原文件 | 0 | `logs/prior_*reset*.txt`；仅为历史原始输出的副本，不是本次重新测量。 |
| `python3 make_inventory.py` | 0 | 生成 `INVENTORY.tsv`，从本次哈希表取值。 |
| `rg` 筛选既有 Vivado/PetaLinux 构建日志、rootfs manifest、编译记录及源码配方；`strings` 只读查看 `boot.scr` 和 `Image` | 0（匹配查询） | 筛选结果分别保存为 `logs/new_fpga_build_excerpt.txt`、`logs/fpga_build_excerpt.txt`、`logs/petalinux_build_excerpt.txt`、`logs/rootfs_packages_excerpt.txt`、`logs/boot_script_excerpt.txt`、`logs/model_compile_excerpt.txt`、`logs/model_provenance_excerpt.txt`、`logs/vitis_ai_source_state.txt`。没有执行这些工程中的脚本。 |
| `rg -l -i 'omsToken|oauth token|password=|authorization:|BEGIN .*PRIVATE KEY|token=' 审查目录/logs 和四个交付文档` | 1（无匹配） | 只输出命中的文件名；本次无命中。此筛选不是对所有可能敏感格式的穷尽检查。 |
| Python 只读检查 `REPORT.md` 和 `SUMMARY.md` 的 `logs/` 相对链接 | 0 | 所有被引用日志存在。 |
| `python3 make_delivery.py` | 0 | 按显式排除列表生成 `SHA256SUMS.txt` 和 `kv260_readonly_audit_20260927.zip`；共 51 个交付文件，清单不包含自身，压缩包不含脚本、镜像、模型。 |
| `sha256sum -c SHA256SUMS.txt`、`unzip -t kv260_readonly_audit_20260927.zip` | 0、0 | 清单列出的文件全部通过哈希核对，压缩包成员全部通过测试；修改本命令记录后已重新打包并再次验证。 |

外部文档通过 AMD Docs 与 Xilinx 官方 GitHub 发布页只读查询，链接见 `REPORT.md`；官方镜像下载链接跳转账户页，未取得发布校验值。未运行工程自带未知脚本、包安装、构建、Docker 启动、板卡命令或磁盘写入。
