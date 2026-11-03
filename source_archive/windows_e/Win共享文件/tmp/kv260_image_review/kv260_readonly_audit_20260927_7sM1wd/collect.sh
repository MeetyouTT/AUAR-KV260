#!/usr/bin/env bash
set -u
AUD=/home/ghmd/kv260_readonly_audit_20260927_7sM1wd
mkdir -p "$AUD/logs"
printf '# 实际采集命令与退出状态\n\n' > "$AUD/COMMANDS.md"
capture() {
  local name="$1" cmd="$2" rc
  printf '## %s\n\n```sh\n%s\n```\n\n' "$name" "$cmd" >> "$AUD/COMMANDS.md"
  ( cd "$AUD" && bash -c "$cmd" ) > "$AUD/logs/$name.txt" 2>&1
  rc=$?
  printf '退出状态：%d。输出：`logs/%s.txt`。\n\n' "$rc" "$name" >> "$AUD/COMMANDS.md"
}
capture host 'date -Is; cat /etc/os-release; uname -a; free -h; lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,MODEL; findmnt -T /home/ghmd -o TARGET,SOURCE,FSTYPE,OPTIONS; df -hT /home/ghmd; df -i /home/ghmd'
capture package_state 'dpkg --audit; dpkg-query -W 2>/dev/null | rg "^(build-essential|gcc|g\+\+|make|git|python3|libncurses5|libncurses5-dev|libtinfo5|libssl-dev|zlib1g-dev|flex|bison|diffstat|chrpath|socat|xterm|texinfo|gcc-multilib|libc6-dev-i386|docker-ce|docker.io|qemu-user-static|device-tree-compiler|u-boot-tools|python3-numpy)[[:space:]]"; readlink -f /bin/sh'
capture package_verify 'dpkg -V bash coreutils dpkg libc6 libstdc++6 gcc g++ make git python3 zlib1g 2>&1'
capture host_errors 'journalctl -k -b --no-pager 2>&1 | rg -i "I/O error|EXT4-fs error|nvme.*error|out of memory|oom-kill|killed process|no space left|read-only file system" | tail -100; journalctl --no-pager -p err -b 2>&1 | tail -100'
capture tool_paths 'command -v vivado || true; command -v vitis || true; command -v petalinux-build || true; command -v docker || true; find /home/ghmd/Xilinx/Vivado/2022.2 /home/ghmd/Xilinx/Vitis/2022.2 /home/ghmd/Xilinx/Vitis_HLS/2022.2 /home/ghmd/petalinux/2022.2 -maxdepth 3 -type f \( -name vivado -o -name vitis -o -name petalinux-build -o -name settings64.sh -o -name settings.sh -o -name version.txt \) -printf "%p %s\n" 2>/dev/null; cat /home/ghmd/petalinux_installation_log'
capture xilinx_install 'rg -in "(success|complete|error|fail|warning|device|installing|installed)" /home/ghmd/Xilinx/.xinstall/Vitis_2022.2/xinstall.log | tail -100; cat /home/ghmd/Xilinx/.xinstall/Vitis_2022.2/data/version.dat; find /home/ghmd/Xilinx/Downloads/Vivado_2022.2 -maxdepth 2 -type f -printf "%p %s\n" | head -60'
capture petalinux_config 'rg -n "(CONFIG_SUBSYSTEM|CONFIG_YOCTO|CONFIG_PETALINUX|CONFIG_ARCH|XSA|2022\.2|HDF)" /home/ghmd/work/petalinux-kv260-dpu/project-spec/configs/config /home/ghmd/work/petalinux-kv260-dpu/config.project /home/ghmd/work/petalinux-kv260-dpu/.petalinux/metadata 2>/dev/null | head -150; find /home/ghmd/work/petalinux-kv260-dpu -maxdepth 4 -type f \( -name "*.xsa" -o -name "*.hdf" -o -name "*.bif" -o -name "*.dtb" -o -name "*.bit" -o -name "image.ub" -o -name "BOOT.BIN" \) -printf "%p %s %TY-%Tm-%TdT%TH:%TM\n" | head -120'
capture build_errors 'rg -in "(error:|fatal:|failed|No space left|No such file|permission denied|killed|out of memory|fetcher failure|do_fetch|checksum mismatch|completed successfully|build succeeded)" /home/ghmd/work/petalinux-kv260-dpu/petalinux-build.log /home/ghmd/work/*build.log 2>/dev/null | tail -180'
capture docker_state 'systemctl is-active docker.service docker.socket 2>&1; if [ "$(systemctl is-active docker.service 2>/dev/null)" = active ]; then docker image ls --digests --no-trunc 2>&1 | head -80; fi'
capture source_state 'git -C /home/ghmd/work/vitis-ai-source/Vitis-AI-3.0 rev-parse --is-inside-work-tree HEAD 2>&1; git -C /home/ghmd/work/vitis-ai-source/Vitis-AI-3.0 status --short 2>&1 | head -30; stat -c "%n %s bytes" /home/ghmd/work/Vitis-AI-v3.0.zip; find /home/ghmd/work/models -maxdepth 4 -type f \( -name "*.json" -o -name "*.xmodel" -o -name "*.log" \) -printf "%p %s\n" | head -100'
capture project_sources 'find /home/ghmd/work/kv260_dpu /home/ghmd/work/kv260_dpu_b2304_uram /home/ghmd/kv260_clockfix_rebuild_20260926 /home/ghmd/work/dpu -maxdepth 4 -type f \( -name "*.xpr" -o -name "*.bd" -o -name "*.xdc" -o -name "component.xml" -o -name "*.xci" -o -name "*.tcl" \) -printf "%p %s\n" | head -180; rg -n "(DPUCZDX8G|DPU_CLK_MHz|FREQ_HZ|ip_repo|part=|board_part|21000000|80000000)" /home/ghmd/work/kv260_dpu/kv260_dpu.xpr /home/ghmd/work/kv260_dpu_b2304_uram/kv260_dpu.xpr /home/ghmd/kv260_clockfix_rebuild_20260926/kv260_dpu.xpr 2>/dev/null | head -120'
capture image_files 'find /home/ghmd/work/petalinux-kv260-dpu/images/linux /home/ghmd/work/petalinux-kv260-dpu/sd-card-staging-dpu-clock-fixed-numpy-sdmmc-nfsd-gem3 /home/ghmd/work/kv260_dpu_b2304_uram/output /home/ghmd/kv260_clockfix_rebuild_20260926/artifacts -maxdepth 2 -type f -printf "%p %s %TY-%Tm-%TdT%TH:%TM\n" 2>/dev/null | head -180; cat /home/ghmd/work/petalinux-kv260-dpu/images/linux/bootgen.bif'
