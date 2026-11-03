# Windows → Ubuntu TCP 22 入站与回包

2026-10-30。本轮只检查网络路径，不重复本机 SSH 安装/登录验证。Ubuntu 连接元数据、Codex 0.166.0 和登录状态沿用此前已通过且用户确认的结果。

## 最新同窗配对结论

Ubuntu 在 UTC **11:34:44.967–11:37:44.982** 持续抓包 180 秒。Windows 的三次探针完整落在该窗口内，路由为 `singbox_tun`、源地址 `172.18.0.1`、下一跳 `172.18.0.2`。

| Windows 尝试 UTC | Windows 源端口 | Windows 结果 | Ubuntu 入站 SYN | Ubuntu 出站 SYN-ACK |
| --- | --- | --- | --- | --- |
| 11:35:35.031–11:35:40.064 | 65514 | TCP Connected=true，SSH 欢迎读取超时 | 0 | 0 |
| 11:35:42.074–11:35:47.082 | 49213 | TCP Connected=true，SSH 欢迎读取超时 | 0 | 0 |
| 11:35:49.090–11:35:54.105 | 49242 | TCP Connected=true，SSH 欢迎读取超时 | 0 | 0 |

不仅三个端口没有记录，整个窗口内该 Ubuntu IPv4 端点的 **TCP 22 记录总数也是 0**，因此结论不依赖 TUN/NAT 是否改写了源端口。没有观察到 SSH 请求抵达 Ubuntu 抓包点，也没有对应的 SSH 回应；本轮没有证据证明“Ubuntu 已回复但回包被丢”。Windows/TUN 的 Connected=true 不能替代与真实 Ubuntu sshd 建立连接的证据。

抓包并非完全没有流量：记录了 **44 条 ICMP `172.18.0.1 udp port 58080 unreachable`**，它们不是 SSH 请求或回应。过滤器统计收到46包、记录44包，内核抓包丢包0；这些统计和原始头部均保留，不把 ICMP 当成 SSH 回包。

当前已将问题范围缩小到 **Ubuntu 抓包点之前**。下一步由 Windows 核对 TUN 对该目标的转发与物理 WLAN 出站记录，再区分 TUN 处理和上游网络丢弃；尚不能指定具体丢包节点。本轮未改路由、TUN、防火墙或 SSH 配置。

完整逐次配对见 `ubuntu-tcp22-paired-analysis.json`；原始材料在 `network-runs/20261030T113440507578Z/`，其中 `windows-probe-correlated.json` 是本轮 Windows 回执冻结副本，原 Windows 文件由 Windows 自己维护。抓包已限时结束。

`ubuntu-registration.json` 已保留全部必填接入字段，`ready=false`，阻塞原因更新为“同窗 Windows 请求未到达 Ubuntu SSH 抓包点，需核对 Windows TUN/物理出站及上游路径”。Windows 身份认证、主机指纹及应用连接均未伪填成功。

## 首轮实测（历史窗口未对齐）

- Ubuntu 仍为 `172.23.242.132/16`，接口 `wlp0s20f3`。IPv4 策略规则只有 local/main/default，未发现 TUN 策略表。
- 到用户给出的 Windows WLAN `10.148.20.87`，返回路由为 `via 172.23.0.1 dev wlp0s20f3`、源 `172.23.242.132`；无线网关邻居状态 REACHABLE。
- `all` 与 `wlp0s20f3` 的 `rp_filter=2`。本轮未修改它或其他网络设置。
- 检查时没有现存 SSH TCP 连接。
- 对所有接口抓取本机 IPv4 TCP 22 头部及相关 ICMP，过滤条件为 `((tcp port 22) and host 172.23.242.132) or (icmp and host 172.23.242.132)`，未保存 PCAP 或应用载荷。
- 该次捕获 0 包，SSH SYN、SYN-ACK、ACK 均为 0。抓包已正常限时结束，没有留下后台抓包任务。

证据在 `network-runs/20261030T112308212272Z/` 和 `ubuntu-tcp22-observation-latest.json`。tcpdump 进程启动时刻按 `/proc` 估算约为 UTC `11:23:35.145`，结束为 `11:26:35.186`。收集器处理“开始监听”提示的时刻为 UTC `11:24:01.754`；匹配 Windows 回执时，保守使用该时刻之后至结束前的完整连接尝试，不能把提示处理时间冒作精确的抓包启动时间。

## 首轮当时的结论

首轮没有看到连接抵达 Ubuntu，也没有可对照的 TCP 回包。当时未收到 Windows 的带 UTC/源端口探针结果，无法确认窗口重叠；后来同步的 UTC11:29 探针也在首轮结束之后，不能拿它与首轮作因果对照。最新已对齐的结论见上文。

Windows 报告路由经过 `singbox_tun`，这是需要在 Windows 侧继续核对的路径事实，不直接等于已确认根因。Ubuntu 返回路由目前经无线网关，没有人为添加到 Windows 的静态路由。共享文件同步能够工作，也不能证明两机 TCP 22 直连可达。

## 下一次两端对照方法

Windows 已准备只读探针 `probe_windows_tcp22.ps1`，需由 Windows 执行。它会记录本机路由、三次连接的 UTC、源端口和是否读到 SSH 欢迎信息，并写入 **Windows 自己的** `windows-tcp22-probe.json`。本机未代填该结果，也未修改 `windows-connection.json`。

在两端约定的新抓包窗口内执行探针。Ubuntu 的命令为：

```bash
python3 -B '/home/ghmd/Win共享文件/协作任务/2026-10-30_Codex跨机协作/observe_ssh_tcp22.py' --seconds 180
```

收到 `CAPTURING` 后 Windows 执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'E:\Win共享文件\协作任务\2026-10-30_Codex跨机协作\probe_windows_tcp22.ps1'
```

此命令只对该脚本进程选择执行策略，不修改系统执行策略；探针不改路由、VPN、SSH 配置、模型或数据库，也不尝试身份认证。

| 同一连接在 Ubuntu 抓包中的表现 | 下一步应核对的位置 |
| --- | --- |
| Windows 尝试完整落在窗口内，Ubuntu 无 SYN | Windows 的实际出站接口、TUN 转发记录及上游网络；尚不能只凭 Ubuntu 抓包区分它们 |
| Ubuntu 收到 SYN，并发出 SYN-ACK，未收到客户端 ACK | Windows 是否收到回包，以及中间返回路径；保留原 TCP 元组对照 |
| Ubuntu 收到 SYN，但未发出响应 | 根据该源地址核对内核入站处理/过滤计数，不先放宽配置 |
| 三次握手完成且有服务器数据发送 | 继续对照 Windows 接收与 SSH 协议阶段，不再按“完全未到 Ubuntu”处理 |
| Windows 显示 TCP 已连通，Ubuntu 无对应 SYN且无 SSH 欢迎信息 | TUN 可能在本地接收 TCP；仅本机 Connect 成功不足以证明已连接真实 Ubuntu SSH 服务 |

窗口对照完成后，Ubuntu 执行 `write_ubuntu_registration.py` 更新自己的注册资料。脚本只复用已确认的本机证据和两端网络结果，不重复登录或安装。单纯 TCP accept 不会把 `ready` 改为 true；需要该候选地址确实返回 SSH 欢迎信息。随后 Windows 再按既有流程严格核对主机指纹、公钥登录和应用连接，三者不混为同一验收。

## 与项目状态分开

`ubuntu-registration.json` 的 `blockers` 仅列 SSH TCP 路径。板端 r3-ubuntu 补丁已由用户确认验收，本轮没有连接、覆写或重启板卡。Windows 实际语音的剩余问题是 GPU 准入不足；该问题单独保留在项目日志与原语音核验证据中，没有调整准入阈值、停止其他模型或绕过资源保护。
