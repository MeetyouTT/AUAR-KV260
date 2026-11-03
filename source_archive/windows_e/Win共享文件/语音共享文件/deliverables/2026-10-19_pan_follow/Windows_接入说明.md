# Windows身份开发与Ubuntu转轴跟随接入

**更新：UTC2026-10-20已在最新handsfree-dialogue/candidate-0c0a8ab46ec2完成wrapper/实况路由及联合平台接入，PWM关闭。当前结果和后续部署须保留的入口见[接入交付](../2026-10-20_pan_axis_integration/README.md)。本页下方“尚未安装”为此前的软件交接状态；最小文件/入口约定继续有效。**

用户指定Windows做身份、Ubuntu做转轴跟随。Ubuntu本轮只新增运动/接口文件，没有修改身份、GTK或ui_camera_service源码，也没有接管正在运行的相机。Windows回执仍由Windows填写。

## 身份端需要保留的接口

跟随读取当前相机已经选中的轨迹。选择继续使用原target_select机制；身份结果可影响选谁，但姓名或LLM回答不直接成为PWM指令。新接口为loopback `GET /v1/motion/observation`，输出带源帧的选中人体框，250ms期限独立于UI的较长展示TTL。

原运行相机尚未提供此路由。待当前身份采样/登记事务结束，协调一次相机重启后再验证。当前没有替Windows执行这一步。

## 最小相机接入

把以下三个新增文件按SHA清单合入最新活动相机的aura目录：

- `common/motion_observation.py`
- `board/motion/camera_feed.py`
- `tools/board_camera_motion.py`

保留原相机模块、身份修改、配置、数据库位置、WorkingDirectory及模型参数，只把原服务启动脚本入口从 `board/vision/ui_camera_service.py` 换为 `tools/board_camera_motion.py`，传入原来的同一份 `--config`。扩展在启动时包装原handler，只加只读路由；`run()`仍由原相机模块执行。原启动命令若不同，先核对实际unit，不直接套用路径。入口切换应先备份unit，并在空闲窗口执行。

禁止在现有相机运行时另启动一个相机进程或执行会建立第二DPU Runner的模型检查。先做语法/导入/清单检查，受控停止原相机后再启动新入口；失败恢复原unit。板端原始CameraState与新增扩展的兼容测试已通过，但不代替当前最新候选的部署后复验。

## 跟随侧验证

旁路控制器运行还需要本包其余运动/工具/配置文件；依赖原VSRVDriver仅用于协议类型检查，不会打开硬件。合并已有文件时检查SHA/本机改动，不直接覆盖未知新版本。

```bash
python3 -B tools/board_pan_follow.py --live --duration 10 --output /tmp/pan-shadow-new.jsonl
```

实况模式必须在板端运行，使用同一boot的monotonic时间。默认1500µs只是软件参考、相机随轴只是旁路假设，不是已完成机械标定。若接口404则任务报错并停止，不借用UI更新时间继续运行。

通过后把实际入口、三个新增文件SHA、实况轨迹位置和异常结果写回Windows回执。Ubuntu再接VSRV联合平台及当前机构标定；双方的服务重启/位流切换需协调，避免中断身份事务。后续部署保留已配置的每boot HDMI关闭2秒逻辑，不用历史startup覆盖当前入口。
