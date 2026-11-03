# Windows缺失的四份ASR源码

源机器：Ubuntu `ghmd-MRA-XXX`，用户目录 `/home/ghmd`。
源码根：`/home/ghmd/Win共享文件/共享文件夹/aura`。

已核对的相对路径：

- `scripts/start_board_asr.ps1`
- `tools/asr_server.py`
- `common/asr_wire.py`
- `docs/BOARD_ASR.md`

补丁包：`asr-host-files-d85566bfa026965a.zip`，7249字节。
SHA256：`a31d058f08e50b4cdf88cc7efa90619fd152b7fd5ecbbd3781468f20579daded`。

将包复制到Windows，解压到实际项目的 `aura` 文件夹，保留scripts/tools/common/docs相对目录。压缩包含上述4份文件和 `ASR_HOST_FILES_MANIFEST.json`，已逐字节回读、核对ZIP CRC和文件SHA256；模型和Python环境沿用Windows已有副本。

```powershell
Get-FileHash -Algorithm SHA256 '<压缩包实际路径>'
Expand-Archive -LiteralPath '<压缩包实际路径>' -DestinationPath '<Windows项目aura实际路径>'
```

本轮只制作源码补丁和检查访问状态，未在Windows解压或运行。完成后按 `docs/BOARD_ASR.md` 启动服务。

## KV260副本与访问证据

本次通过串口只读确认：

- 运行时目录：`/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura`。
- `tools/asr_server.py`、`common/asr_wire.py`存在，SHA256与Ubuntu原件一致。
- `scripts/start_board_asr.ps1`、`docs/BOARD_ASR.md`未部署到该目录，无法仅从板端运行时凑齐这4份。
- 账号root；22端口存在监听。`passwd -S root`显示P，即已有密码，检查没有读取密码或密码摘要。没有取得该密码，也没有验证SSH密码或公钥登录。
- 本代理实际使用且已经验证的是UART串口root终端，不代表SSH免密可用。没有修改认证、密码或密钥配置。

证据：`/home/ghmd/aura-asr-integration-20261016/evidence/20261017T121130.038701Z-ssh-inventory-fixed/response.json`。首次检查因板卡没有ss工具失败，已改读`/proc/net/tcp*`完成，串口回显恢复。
