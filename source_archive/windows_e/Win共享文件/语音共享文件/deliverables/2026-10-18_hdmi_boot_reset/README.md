# 每次开机自动重新初始化 HDMI 输出

UTC 2026-10-19 04:46 实际安装，本地日期2026-10-18。用户要求普通重启和断电开机时自动重启HDMI输出。

**已设置，下次开机生效：等待显示就绪 → 关闭输出2秒 → 恢复1024×600 / 59.85Hz → 启动连续对话界面。** 现有启动器原本已启用每boot一次1秒输出重建，本轮只将实际开机配置的 `display_retrain_off_seconds` 从1改为2；未添加重复启动服务。新boot会使旧标记失效，正常重启和断电开机均会重新执行；同一boot内仅重启界面不会反复关闭输出。

## 实际改动与证据

- 板端实际文件：`/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/startup/config.json`，启动服务 `aura-avatar-ui.service` 已enabled，ExecStart已核对指向该配置。
- [修改前配置](baseline/actual-config.json) 与 [安装后配置](installed/installed-startup-config.json)，唯一字段差异为关闭时间1→2秒。安装后SHA `73986dae4996a733db622843337fa2abc667fc53ecc7da3d336dffea44bcb064`。
- 原文件已备份为同目录 `config.before-hdmi-boot-reset-20261018.json`；回退仅恢复这份配置，无需回退GUI、语音模型或相机。
- [安装与板端预检](evidence/install/response.json)、[实际开机入口检查](evidence/precheck/response.json)、[原启动器](baseline/actual-launcher.py)、[核验与文件清单](verification.json)。9份冻结文件长度/SHA已核对。

## 验证与限制

17项既有显示启动逻辑测试通过，包括新boot换代、同boot不重复、EDID延迟、时序保护、取消/失败时恢复；显示命令为fixture，不是实体显示验收。实机安装前后启动预检通过，boot和GUI/相机PID保持，服务未重启；当前屏幕EDID已能实读128字节。

本轮没有自动重启或断电。下次普通重启和冷启动的实际执行、实体花屏是否消失仍待现场确认；不能把配置写入或软件模式回读当作花屏已彻底修复。

后续更新身份/界面候选时，须继承当前活动入口的显示配置，保留2秒输出重建；不要用较早 `scripts/board_ui_startup/config.json` 的旧GUI/组件清单覆盖当前活动版本。该历史源码目录的README已增加本交付入口。
