# 原生 SSH 跨机 TCP 22 对照

用户确认 Ubuntu 本机 SSH 已通过，不重复安装或登录。本轮仅核对 Windows→Ubuntu 入站/回包和注册资料，无板端命令。

Ubuntu 172.23.242.132/16/wlp0s20f3；到 Windows WLAN 10.148.20.87 返回走 172.23.0.1，源172.23.242.132。仅有 local/main/default IPv4 路由规则；all/wlp0s20f3 rp_filter=2；网关邻居 REACHABLE。没有改路由、VPN、防火墙、SSH 配置或 Codex 登录凭据。

约 UTC11:23:35.145–11:26:35.186，tcpdump 所有接口过滤本机 IPv4 TCP22及相关ICMP，0包/SYN0/SYN-ACK0/ACK0。收集器监听提示处理时间11:24:01.754，匹配窗口使用该更保守时点；原始日志与进程启动估算分开保留。捕获进程已结束。没有保存应用载荷、PCAP、身份数据或凭据。

Windows 用户报告经singbox_tun复测无SSH欢迎信息，但本轮没有收到带UTC/源端口的Windows探针回执，未确认复测落在窗口中。因此只能记“本轮未观察到入站”，不能认定TUN或校园网络为具体丢包点，不能用无SYN直接证明返回路由故障。

共享接入目录已增加 observe_ssh_tcp22.py、Windows只读探针probe_windows_tcp22.ps1、Ubuntu_TCP22入站与回包.md；Ubuntu回执和注册生成器已更新。ubuntu-registration.json完整保留必填字段及真实Ubuntu地址、22、ghmd、项目路径、Codex路径/0.166.0与原ED25519主机指纹，ready=false，blockers仅为SSH网络路径及缺少窗口对应结果。不代填Windows结果，不把GPU问题作为SSH阻塞。

用户明确确认板端r3-ubuntu补丁已通过验收，本轮不重复部署。实际语音GPU不足独立保留，未停止其他模型、改准入或重跑语音。原结果见2026-10-30-VISUAL-SIMPLIFICATION-AND-SSH-PREP.md及视觉简化ubuntu/evidence/20261030T110222516088Z-verify_live/。后续只在确认窗口后对照SYN/SYN-ACK/ACK，定位到Windows出站、上游或返回路径；本机SSH已验收事实保持。

## 后续同窗实测：已确定未见请求抵达 Ubuntu

用户明确要求启动新180秒抓包并在CAPTURING时立即告知。实际UTC11:34:44.967347–11:37:44.982084持续运行，未提前终止。Windows回执UTC11:35:34.5588935–11:35:54.1055153，三次完整位于窗口内：

- 172.18.0.1:65514，11:35:35.031–11:35:40.064；
- 172.18.0.1:49213，11:35:42.074–11:35:47.082；
- 172.18.0.1:49242，11:35:49.090–11:35:54.105。

Find-NetRoute实际为singbox_tun/接口19/默认路由0.0.0.0/0/下一跳172.18.0.2。三个客户端均Connected=true，但读SSH欢迎信息超时。Ubuntu全接口对该IPv4端点的TCP22记录总数为0，各端口SYN0/SYN-ACK0；因此不是仅因NAT改端口导致精确匹配失败。

原始抓包实际记录44条ICMP“172.18.0.1 udp port58080 unreachable”，不是SSH；过滤器收到46包、记录44包、内核丢包0。不能把“TCP记录0”写成“全部抓包0”。已冻结Windows副本并保存sha与逐次配对到network-runs/20261030T113440507578Z/及ubuntu-tcp22-paired-analysis.json。

该轮未观察到Windows SSH请求抵达Ubuntu抓包点，也没有对应SSH回应，不支持“Ubuntu已发回SSH回应但回包被丢”的判断。范围缩小到Ubuntu抓包点之前，具体TUN处理还是上游丢弃需Windows物理网卡出站/转发记录，不以猜测认定。注册资料已原子更新，ready=false，阻塞仅为SSH路径，三次时间窗对应已确认。本轮没有板端操作、本机登录重测、路由修改或GPU保护变更。
