# 2026-10-15 触屏录音与本地播放互斥

用户继续要求“继续”。本轮先读 ZIP README、项目规则和最新采录记录，落实下一项：将已板测的 MCP01 录音接入当前 GTK 界面，补后台音频所有权和真实窗口验收。详见 [本轮报告](/home/ghmd/aura-touch-recording-20261015/REPORT.md)。

## 实际完成

- 新增 `tools/board_recording.py`，修改 GTK/后台渲染/HTTP 操作适配，把本地录音和缓存播放置于同一后台控制器。
- 互动页原按钮已可开始/停止录音，显示真实时长；取消清除录音，不产生伪识别文本或回答。
- 主机框架 **161 项通过**；实际板端相关 **18 项测试**、资源与启动预检通过；运行包收集检查 **927 文件**通过。
- 实际部署 `ee6bc2c48a5886ae`，启动器 `157fdb41b24e4c9d`。应用前备份并核对旧哈希，主动重启 GUI 一次，相机服务保持运行。
- 原生 GTK/XTest 点选真实录音并停止，62000 样本/3.875 秒；再次录音取消后结果为空。
- 20 秒自动停止实测为320000样本/640000 PCM字节，93次状态观测，结束后无设备占用。
- 录音中缓存播放请求、实际缓存播放中录音请求均被拒绝；最后回到互动页 IDLE/输出 NULL，无残留音频、无错误，音量58%/非静音保持。
- 两张1024×600实屏截图已查看；58份UART响应、14包载荷、10运行文件及2图片独立核验通过，见 [核验](/home/ghmd/aura-touch-recording-20261015/validation.json)。含1份已解决清单助手错误原始记录。

## 问题处理

主机 HTTP 测试首次因沙箱不允许 socket 创建而失败，移到主机侧运行同组18项及全量161项均通过。没有绕过或忽略失败。

暂存助手把新清单 `update_id` 当作旧 `release_id`，在部署前核验时报错。检查已上传文件哈希后修正并完成清单，再应用更新；旧服务在此错误期间未被停止。运行代码回滚未触发。

## 状态与边界

后续部署和验收的当前 boot 为 `6d8d2fb6-1b92-434b-98c4-58f65f8b5fb9`；相机PID986/代次不变。最终GUI supervisor PID148040，两个服务均active、自动重启计数0。较早探针是旧boot，本轮没有观察外部断电/重启过程，不追加冷启动通过结论。

`eth0` 最终仍 NO-CARRIER/无IP，路由为空；等待局域网连接及 Windows 服务地址。当前完成 M6/L2 的本地触屏采录子项，没有完成跨机问答。GTK/XTest 不是实物手指触摸；长期性能、身份、机构和新版PL仍待验收。截图UI tick约4fps，流畅度单列，不以预览入口约12.6Hz冒充物理屏幕帧率。

主仓改动：新增 `tools/board_recording.py`、`tests/framework/test_board_recording.py`、`tests/framework/test_stage_bridge.py`；修改 `tools/board_avatar_gtk.py`、`tools/board_avatar_worker.py`、`tools/realtime_bridge.py`、`tools/package_board_avatar.py`；同步录音说明、README、框架状态和项目导航。原文件副本、部署/验收助手、匹配包及原始证据位于 `/home/ghmd/aura-touch-recording-20261015/`。
