# 2026-10-17 微力同步实际状态检查

用户要求直接查看微力同步情况。通过本机CLI及回环管理API读取运行状态、目录、连接、错误、远端完成度及指定文件的当前版本可用设备；不修改任务或清除错误。

## 实际结果

本机v2.33.2，任务根 `/home/ghmd/Win共享文件`，双向同步、未暂停、自动扫描间隔3600秒，文件监控无错误。当前索引80706文件、8978目录、49947931867字节（约49.95GB）。本机idle、needTotalItems/needBytes均0、errors/pullErrors均0，待同步队列和错误列表为空。上轮新增的.pytest_cache规则已由实际API确认加载。

连接设备名JoneNike，在线且未暂停，类型quic-client，isLocal=false。没有据此推断具体中继路径、实际Windows用户名或局域网硬件拓扑。完整设备ID、配置密钥和公开地址未保留在最终诊断报告。

第二次快照Unix1792242125读取对端完成度99.8988035%，还需247项/50545557字节；start_board_asr.ps1已在对端索引确认，新完整ASR ZIP当时尚未确认。约135秒后的快照Unix1792242260显示对端100%、needItems=0、needBytes=0，remoteState=valid，远端待同步文件列表为空，传输确有推进。

最新逐项查询确认ASR所需11项（8源码/说明、3模型数据）以及完整代码包asr-host-complete-code-b9ac9d83fe24f179.zip均被对端报告拥有当前全局索引版本，11项全局/本地大小与必需清单一致。缓存目录也不再构成对端待同步项。此证据属于同步程序的版本索引确认，未在Windows上独立重算文件SHA或启动ASR服务，不等于跨机识别已验收。

## 工件与验证

工作目录 `/home/ghmd/aura-sync-inventory-20261017/verysync-status/`：三次脱敏快照、validation.json。最新快照status-1792242260.json，核验状态PASS_CURRENT_SYNC_COMPLETE_AND_ASR_PEER_INDEX_CONFIRMED；零待同步/零本机错误、对端完成度和11项+ZIP可用版本断言通过。

新增诊断辅助脚本inspect_verysync_status.py和verify_verysync_status.py，保留在工作目录。初轮API错误列表返回null，辅助脚本改为按空列表处理后检查通过，没有修改微力配置或掩盖后台错误。

没有重启同步、操作忽略模式、修改源码/模型、触碰板端服务或远程发送消息。可让Windows Codex重新读取已同步的共享文件夹/aura，在实际语音环境启动识别服务；如旧网页仍显示之前缓存错误，可刷新核对当前任务状态。
