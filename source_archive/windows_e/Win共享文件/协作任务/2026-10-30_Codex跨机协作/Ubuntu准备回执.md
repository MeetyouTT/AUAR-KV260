# Ubuntu 原生 SSH 接入准备回执

2026-10-30。Ubuntu 侧服务、公钥与 Codex 已准备并通过本机真实 SSH 登录验证；Windows 跨机连通尚未确认，`ubuntu-registration.json` 保持 `ready: false`。

接续检查：用户已确认本机 SSH 验证通过，本轮没有重复安装或登录测试。Windows 经 `singbox_tun` 复测仍未收到 SSH 欢迎信息；本轮专门检查跨机 TCP 入站及回包，详见 [TCP 22 对照记录](Ubuntu_TCP22入站与回包.md)。

最新 UTC11:34:44.967–11:37:44.982 的 180 秒抓包已与 Windows 三次尝试对齐：端口65514/49213/49242全部在窗口内，Ubuntu TCP22记录0、SYN0、SYN-ACK0。另有44条 UDP58080不可达的ICMP记录，不属于SSH。注册资料已更新为该实测阻塞，ready仍为false；后续核对Windows TUN转发和物理出站，不重复本机SSH安装或登录。板端r3验收和Windows GPU准入问题分别记录。

| 项目 | 已核验结果 |
| --- | --- |
| Ubuntu 用户 | `ghmd`，登录 shell `/bin/bash` |
| Ubuntu 地址 | `172.23.242.132/16`，`wlp0s20f3`；目前仅为 Windows 接入候选 |
| SSH | OpenSSH Server `1:8.2p1-4ubuntu0.13`，22 端口，active/running/enabled |
| 项目目录 | `/home/ghmd/Win共享文件/语音共享文件` |
| 主源码 | 上述项目内 `aura/`；不是根目录较早的 `aura` 副本 |
| Codex | `/home/ghmd/.local/bin/codex`，`codex-cli 0.166.0` |
| 登录状态 | `codex login status` 确认为 `Logged in using ChatGPT` |
| 主机 ED25519 指纹 | `SHA256:tNZ7GjGBvS/wQDcvA2omrWvQAKLYIaR4/a2WaBf/Mrs` |
| Windows 公钥指纹 | `SHA256:2e0xLhkeWwz48xIv0QqIfeTNeXoEX6sgjt2yo5ftvlc` |

已将提供的 `windows-codex.pub` 去重追加到 `/home/ghmd/.ssh/authorized_keys`。第二次运行检查没有重复追加，目录/文件权限分别为 0700/0600。保留了此前内容，没有读取或复制 Windows 私钥。

在 `.bashrc` 中追加了有标记的用户本地 bin PATH 配置，保留原 Codex 代理包装函数及其他设置。本机回环地址经过真实 OpenSSH 登录，普通 SSH 命令 shell 和登录 shell 均能找到 Codex，并通过版本、登录状态及项目目录检查；见 `ubuntu-local-ssh-verification.json`。测试临时密钥只存在本机临时目录，测试后已移除授权及临时目录，Windows 公钥保持。

通过 Ubuntu 系统授权安装了 OpenSSH Server 和必需的 SFTP 组件，没有升级其他软件包或卸载软件；使用保留原配置的安装选项。有效 `PermitRootLogin=without-password`、公钥认证启用，root 密码登录未开放。UFW 不活动，INPUT 默认 ACCEPT；没有修改防火墙或路由。SSH 主机私钥由安装器在系统目录本地生成，未输出或复制其内容。

## 当前网络不确定性

Windows 用户报告 WLAN 为 `10.148.20.87/17`、网关 `10.148.0.1`，到 Ubuntu 的现有路由经过 `singbox_tun`。Ubuntu 返回该 Windows 地址的路由为：

```text
10.148.20.87 via 172.23.0.1 dev wlp0s20f3 src 172.23.242.132
```

Ubuntu 发出的两次 ICMP 没有收到应答；这不证明 TCP/22 不通。用户此前未收到 SSH 欢迎信息的检查发生在服务安装前；需要在服务已监听的状态下重新测量，不能据此确定为 VPN、校园网隔离或 SSH 配置故障。

另对 `wlp0s20f3` 进行了 45 秒只含 SSH TCP 头部的被动观察，0 个匹配包，观察进程已结束。尚未确认 Windows 复测是否落在该窗口，因此不能把它记为“Windows 已重试而被上游阻断”。服务、策略与路由证据见 `ubuntu-network-audit.json`。

Windows 应先只读复测：

```powershell
Test-NetConnection 172.23.242.132 -Port 22 -InformationLevel Detailed
ssh-keyscan -T 5 -p 22 -t ed25519 172.23.242.132
Find-NetRoute -RemoteIPAddress 172.23.242.132
```

对照 SourceAddress、InterfaceAlias、NextHop 和上面的主机指纹。尚未改动 sing-box 规则、增加静态路由、切换网卡或使用板卡专用地址。若实测显示流量仍走 TUN，由 Windows 侧核对到该 Ubuntu 地址的实际分流规则及网关可达性；实际原因仍需证据。

待两机 TCP 路径核验后，Ubuntu 更新自己的注册资料，Windows 再运行现有 `connect_windows.py`，保留严格主机指纹检查。`windows-connection.json` 和 `windows-preparation.json` 由 Windows 更新，本机未代填成功。

## 原生应用接入边界

没有手动启动 app-server，也没有为其开放局域网端口。Windows 应用通过 SSH 和远端登录 shell 启动 Codex，随后选择已核验的项目目录；依据为[官方 SSH 连接说明](https://learn.chatgpt.com/docs/remote-connections#connect-to-an-ssh-host)。应用内连接和现有会话是否可访问仍需 Windows 实测，不宣称已建立远程 Codex 会话。

接入成功后，优先通过可访问的远程 Codex 会话交接任务和读取结果。本共享目录仅保存接入资料与验证证据。后续 Ubuntu 负责板端编译和部署；Windows 负责 27B、OmniVoice 与接口联调；业务处理和记忆存储最终全部在板端是后续目标，本次没有执行迁移或板卡覆写/重启。
