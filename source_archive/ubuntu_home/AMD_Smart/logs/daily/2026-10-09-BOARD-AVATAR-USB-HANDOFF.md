# 汐蓝完整运行包拷贝准备

用户询问“那现在怎么办”。沿当前播放器部署任务，先读 ZIP README、AMD_Smart 规则、最新连接日志和完整包核验；检查 Ubuntu 是否已有可用传包介质。

## 本轮检查

主机侧 `lsblk -J -o NAME,TYPE,TRAN,RM,SIZE,MOUNTPOINT` 只显示系统 NVMe/loop 设备，没有 USB 存储；`ip -brief address` 显示 Wi-Fi、回环和未启用 Docker 网桥，没有有线网卡。板端网络的最新证据仍为前次 eth0 管理层 UP 但 NO-CARRIER；本轮未重复连接串口或修改网络。

已异步询问用户目前方便使用 U 盘、将板卡接到路由器的网线，还是只有现有串口线。准备记录时尚未收到选择。按可逆的本地准备继续整理 U 盘拷贝材料，没有将未回复解释为允许访问任何外部存储。

## 已准备的具体文件

目录：[USB_READY_AURA_AVATAR](/home/ghmd/aura-board-avatar-gtk-20261009/USB_READY_AURA_AVATAR)。

- 完整运行包 `aura-board-avatar-gtk-runtime-20261009T112752Z-57fc8c.zip`：与原包建立本地硬链接，避免复制大文件，不修改其字节。
- `SHA256SUMS`：拷贝后校验用。
- `package_verification.json`：保留原包 871 载荷核验记录。
- `U盘部署步骤.txt`：拷贝/挂载位置确认、包 SHA 核对、独立新目录解包、资源检查、启动与实机验收步骤。

重新读取待拷贝 ZIP，大小 **217023529 字节**，SHA256 **1a8677ce385516b406344f5e22acfed72e1fd9ab1ffe79aa745760e1137917de**，与原核验一致。[本次准备核验](/home/ghmd/aura-board-avatar-gtk-20261009/usb_handoff_validation.json)。原程序/配置/素材/声线及已发布 ZIP 的内容未改变，未重复运行与本次拷贝准备无关的软件测试。

## 下一步与限制

优先建议用户把 U 盘插到运行 Ubuntu 的电脑。实际识别挂载点、目标目录和空间后再拷贝，拷贝核验后安全卸载，用户将其插到 KV260，再经已可用的串口控制台处理独立目录部署及启动。网络也是可选传输方法，待用户提供实际连接方式。当前未拷入 U 盘、未部署完整素材、未创建玩偶窗口或播放声音。
