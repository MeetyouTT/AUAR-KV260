# 汐蓝完整运行包已拷入 U 盘

用户在确认 USB 插入顺序后回复“好了”。已识别 U 盘位于 Ubuntu：`/dev/sda` USB/removable、分区 `/dev/sda1`、vfat、卷名 64 GB，挂载于 `/media/ghmd/64 GB`，可用 62574952448 字节。只针对本次新目录操作，没有格式化或覆盖已有内容。

## 完成内容

新增本地 [拷贝脚本](/home/ghmd/aura-board-avatar-gtk-20261009/copy_usb_bundle.py)。源文件、本次设备身份、主机挂载点/读写权限、空间和目标目录存在性先核验，再使用独占创建写入、逐文件 fsync/回读 SHA 校验。

U 盘新目录 `AURA_AVATAR_20261009_1a8677ce` 内已拷入四个文件：

- `aura-board-avatar-gtk-runtime-20261009T112752Z-57fc8c.zip`：217023529 字节，SHA256 `1a8677ce385516b406344f5e22acfed72e1fd9ab1ffe79aa745760e1137917de`。
- `SHA256SUMS`。
- `package_verification.json`。
- `U盘部署步骤.txt`。

四个文件的 fsync、大小/SHA 回读一致。随后实际执行 `udisksctl unmount -b /dev/sda1` 返回 0 / `Unmounted /dev/sda1.`，安全卸载完成；现在可由用户拔下并插到 KV260，原串口线继续连接。

[本次核验](/home/ghmd/aura-board-avatar-gtk-20261009/usb_copy_validation.json)，完整拷贝过程为 `evidence/20261009T115410.041145Z-usb-copy/status.json`。

## 检查期间纠正

沙箱内 findmnt 将外部介质呈现为 ro；初步因此判断不能写入。主机侧核对为 rw，设备写保护 off；实际可通过获准主机操作写入。内核另提示上次未正常卸载，不能据此断言文件损坏。一次 `sudo -n fsck.fat -n` 因需要密码而未执行；没有修复、重新挂载或修改文件系统参数。

首轮拷贝脚本因 lsblk 未含 NAME 列而返回平面清单，设备检查安全停止，尚未创建目标目录或写入文件。已加入 NAME 取得树形结构，再只读 inspect 确认设备、空间及目标不存在后成功拷贝。未绕过身份检查。

## 验证边界与下一步

本轮只是 U 盘拷贝和安全卸载，完整播放器仍未部署到 KV260、没有创建窗口或播放声音。新增脚本语法验证通过，四源/目标文件一致；没有重复与本次文件传输无关的软件测试。

下一步需要用户将该 U 盘从 Ubuntu 移插到 KV260。识别实际块设备/挂载位置后，核对 ZIP 并在板端新独立目录展开，保持 aura/deliverables 相邻，先资源/库预检再启动窗口并验收。没有停止现有视觉进程、改写 FPGA 或操作舵机。
