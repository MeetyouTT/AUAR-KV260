# 转轴跟随与Windows身份分工

本地2026-10-19，UTC2026-10-20。用户要求Ubuntu开始转轴跟随，Windows负责身份识别开发。原身份开发/部署不再由Ubuntu并行修改。

## 起点与范围

读ZIP README、FPGA原框架/资料导航、AMD_Smart和语音根AGENTS、共享入口/双方回执、10月8日VSRV方向/有限视觉/固定往返板测及最新项目记录。无子代理。旧实测方向为镜像左侧脉宽增大/逆时针，polarity=-1；脉宽1400～1600µs曾有限测试，不当作当前机构机械标定。

UTC05:06串口只读：boot3e1add36-b917-4289-91dc-699348528782，官方kv260-benchmark-b4096.bit.bin operating；当前相机已是enrollment-photos/candidate-6f1aa1842d53，identity=true、约9.91Hz；GUI为capture-snapshot候选。未复用旧stage/b1b08当作当前业务根。当前位流不含VSRV，不读取未知寄存器。机构/相机装配状态已询问，暂无本轮确认。

## 实现

新增 `common/motion_observation.py`、`board/motion/{camera_feed,follow}.py`、`tools/{board_camera_motion,board_pan_follow}.py`、`config/pan_follow.shadow.json`、`tests/framework/test_pan_follow.py`。原身份/GTK/ui_camera_service/VSRV驱动源码未编辑。

相机可选入口只包装原HTTP handler，在同一相机/模型进程增加loopback只读坐标路由，不新增摄像头/DPU所有者。导出当前选择的真实测量框、源帧/出队时间、boot/相机/服务/轨迹代次，250ms源期限不随UI/预览刷新；无照片/身份特征。

控制使用五个不同源帧确认、100ms低通、滞回死区、40µs/s/单步4µs/参考±40µs，并受已有台架脉宽范围约束。轴载相机做居中反馈，固定相机必须给实测锚点，防止静态误差累计至边界。重复/乱序/修改源、过期/断流、换人/重启、时钟或ACK异常均停止锁定，不自动恢复。ShadowDriver不访问硬件；物理控制须注入已按现有VSRV协议显式参考并ARM的驱动，不提供默认实物零点或隐式ARM。现有VSRV仍为相对租约，不虚称源绝对期限RTL已完成。

## 验证

- 初次默认Python完整发现304项，NumPy缺失/沙箱套接字禁用导致11错误和12跳过；未当作代码回归结论。使用已有host-env并获得回环套接字权限后，完整324项全部通过，其中35项新增；未安装新依赖。
- 板端独立目录 `/home/root/aura-pan-follow-20261019/test-2f1e928a6ec30f9b`，SHA核验9份文件。初次测试加载器调用NamespacePath.insert失败，未改生产服务；改显式路径列表后，实际当前CameraState上35项软件测试通过。相机源码SHA8aa94461e6b505857a199d91a0d35c78364d4621e1c7894c0d2798706ac38a8f。
- 90帧fixture回放，86次软件接受、范围1460～1540µs、最终REPLAY_ENDED/DISARMED。最终输入明确fixture，早期回放的actual形状测试留私有历史、不作实况证据。
- 临时回环HTTP端口上新坐标路由/原health均通过，未占用生产8790；不是真人帧或实物跟随。
- 测试前后相机PID2004、GUI41716、boot、位流保持；本轮未重启服务/切换FPGA/ARM/PWM。早期GUI7187与后来的41716是Windows并行更新过程，不能声称整轮所有PID始终不变。

## 交付与剩余

[交付入口](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-19_pan_follow/README.md)保存原样9源文件/14,929字节ZIP、过滤证据和合成轨迹，29份冻结工件按长度/SHA核验。原始UART/实际图像/身份库不共享。新增PAN_FOLLOW说明和Windows最小接入说明，Ubuntu回执/共享入口/导航更新；未代填Windows回执，不把写入共享当作Windows已接收。

生产相机尚未加载新只读接口。下一步先与Windows协调空闲窗口，在其最新相机目录仅加三个扩展文件/改启动入口，保留其身份源码和HDMI配置，再做10秒真人实况旁路。当前无VSRV且机构状态/参考位置未知，不能宣称实体已跟随；还需配套DPU/VSRV平台、机械标定、显式启停接入与受控实转验收。软件候选通过不等于完整转轴业务完成。

## 用户接入转轴后只读检查（UTC2026-10-20 06:54—06:56）

用户报告“这边连接了转轴，你看看怎么样”。本轮先核对ZIP入口、共享任务及双方回执/最新实际日志，通过串口确认原boot3e1add36保持，当前FPGA operating且仍是kv260-benchmark-b4096.bit.bin。相机PID2004，身份服务ready，约9.93Hz、帧龄131ms，无相机/检测错误；GUI为long-conversation/candidate-9a5bcf476bf8、PID41716、IDLE/自动对话停止。未用旧GUI根覆盖当前版本。

只读检查联合候选 `/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked` 存在，8个payload/4个runtime文件SHA全部匹配，官方固件文件和VART配置也匹配保存基线；联合BIN/XCLBIN/DTBO均存在。但当前固件名称不满足Native VSRV访问门槛，ZOCL refcnt=3，因此没有读取未知MMIO、切换位流/重启业务、ARM或PWM。

已询问是否仍为DS3230/J2.3、独立供电与板卡共地以及摄像头是否随轴转，答复尚未到达。用户“已连接”只升级为现场连接报告，不自动当作线序、电源或机械参考已验证。需先确定这些实物条件；切联合平台时还需协调Windows正在运行的视觉/身份使用者，不能在DPU占用时卸载。旧common/load脚本绑定历史boot，不能原样执行。

新增6份过滤证据与连接检查JSON，长度/SHA通过；实际相机源码仅私有读取，未同步原始UART/人脸或身份库。未修改产品源码，无需重复运行软件回归；本轮结论是连接报告已记录、板端正常、联合固件完整但未加载，实物转动未测试。
