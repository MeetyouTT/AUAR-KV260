# 普通重启/断电开机自动初始化 HDMI 输出

用户最新要求：每次开机、普通重启和断电重启，自动对HDMI输出重新初始化。已读ZIP README、C执行手册、AGENTS、共享入口、现行开机源码/测试及最新DPU切换/花屏日志，无子代理。

实查当前 `aura-avatar-ui.service` 为enabled/active，ExecStart指向 `/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/startup/launcher.py --config .../startup/config.json`。原配置已为startup_display_retrain=true、off1秒、EDID宽限15秒/稳定3秒；原启动器boot标记逻辑覆盖热/冷重启，同boot仅界面重启不重复关闭。不是原来完全没有自动初始化。

本轮只将活动配置 `display_retrain_off_seconds` 由1改为2，按原校验范围设置。修改前SHA b94b4522021c875bda4e9b414e82f52ae9bad00ce4bbc8892c29e4ddc466c0f2，修改后73986dae4996a733db622843337fa2abc667fc53ecc7da3d336dffea44bcb064。原件保存 `config.before-hdmi-boot-reset-20261018.json`，候选预检通过后原子替换，随后再次预检通过。没有更改GUI/模型/时序/组件清单，也没有创建重复显示服务。

17项既有显示逻辑测试通过，覆盖boot换代/取消恢复/失败重试/EDID与已核验时序保护；命令为fixture，不当作物理验收。活动启动器SHA61d852c0fd02077c0d6d167516cad90401e49551ff0e64f7e3fcaca3dcba932d与被测共享源码一致。安装后实读配置及SHA通过，原boot f4789036、GUI监督器PID2302、相机2300保持，EDID当前实读128字节。

结果为PASS_PERSISTED_NEXT_BOOT_HDMI_RESET_2S，配置持久化、下次开机生效。未发送整板重启或断电命令，下次冷热启动自动执行和实体花屏是否消失仍待现场验证。不能将输出初始化当作根因已修复。

共享[交付说明](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-18_hdmi_boot_reset/README.md)保存修改前后配置、启动器、安装辅助及过滤证据，9份冻结文件逐项核对长度/SHA。更新Ubuntu回执、入口、导航及旧startup目录README；不覆写旧config/release历史清单。后续DPU/GUI候选须继承当前2秒设置，不能再用旧配置覆盖。
