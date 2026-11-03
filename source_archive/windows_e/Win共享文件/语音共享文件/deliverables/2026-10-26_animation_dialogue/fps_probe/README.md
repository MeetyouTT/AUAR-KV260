# Windows动画合成可行性初测（2026-10-26）

可以考虑把逐帧合成放到Windows，板卡保留交互、音频播放时钟与原生送显。仅移动素材文件通常不解决板端的逐帧计算开销。本轮计算和传输初测均通过，值得继续接入验证；正式板端仍按8fps运行。

## 已实测的范围

当前原生人物区域为423×438；一帧RGB为555822字节，24fps的纯像素流量为106.72Mbps。网线协商速率1000Mbps。[当前配置](board_display_context.json)。

| 环节 | 结果 | 不能据此得出的结论 |
| --- | --- | --- |
| Windows CPU：待机、说话和四种动作 | 每类预热后96帧；P95约3.74–5.93ms，均有96种RGB像素SHA；四动作状态及说话恢复已断言 | 不是屏幕250fps，也未验证独立进程中的完整对话/UI竞争 |
| 冷素材首次使用 | 首帧约122–512ms，独立核心初始化约1.43秒 | 必须提前加载动作/嘴型，不能只引用热态结果 |
| 12fps原始RGB网线传输 | 64帧、实际12.00fps、往返P95 11.25ms，CRC全部通过 | 无屏幕输出 |
| 16fps原始RGB网线传输 | 64帧、实际16.00fps、往返P95 11.68ms，CRC全部通过 | 无屏幕输出 |
| 24fps原始RGB网线传输 | 64帧、实际24.00fps、往返P95 14.03ms，CRC全部通过 | 无屏幕输出，也不是动态渲染与网络合并压测 |

[CPU原始数据](windows_render.json)、[网络原始数据](wire_transport.json)。Windows计时使用高精度 `perf_counter`；早期低精度单调时钟的网络日志保留，最终数据已重测。每轮只允许一帧在途，192帧共106.72MB，临时端口随试验关闭。板端收到RGB后只做CRC和回执，没有建立第二个NativeVideo、解码器或窗口。

Windows使用独立OpenCV 5.0.0 headless目录、现有NumPy/Pillow及CPU单线程，未改变语音Python或GPU模型。共享演示源码的工厂、FSM、播放器和眼嘴层与板端存在版本差异；实验隔离加载实际板端模块，只将资源定位到共享目录，没有覆盖这些开发版源码。执行源SHA及差异见[模块核对](renderer_source_compare.json)与本目录 `board_source`、`demo_script.py`。这是Pillow/OpenCV路径，不是将ARM的原生像素共享库直接搬到Windows。

## 可实施的接入方式

1. 保留板端状态机/事件归属和音频主时钟。给Windows发送当前代次、动作、PCM播放位置及目标帧序号，Windows返回带相同归属的RGB帧。
2. 先使用原始RGB，避免先引入编码/解码变量；当前尺寸的带宽初测支持这条路径。更大画幅或无线链路再另测压缩方案。
3. 在当前单一原生sink接入最新合法帧，拒绝旧代次和过期帧；发送/接收队列有界，拥塞丢旧画面，避免越播越慢。现有8fps固定调度要在实验配置中同步调整。
4. 首次启用前预加载素材；断网、超时或渲染进程退出时由板端回到本地待机画面。交互取消、音频和机械安全由板端继续控制。
5. 实际送显从12、16到24fps逐级验收，测SPEAKING/插话/长时间运行的帧间隔、音画偏差、网络断续及Windows语音模型并发负载，再决定是否保留。

队列边界及推流行为参考官方[GStreamer appsrc](https://gstreamer.freedesktop.org/documentation/app/appsrc.html)与[queue](https://gstreamer.freedesktop.org/documentation/coreelements/queue.html)；具体属性需匹配板端版本。OpenCV安装来源为[官方Python安装说明](https://docs.opencv.org/5.0/py_tutorials/py_setup/py_pip_install/py_pip_install.html)及[PyPI项目](https://pypi.org/project/opencv-python-headless/)。

这会增加对Windows和网线的依赖，也减少板端独立完成的工作量。结合比赛“尽可能在板卡实现”的要求，适合作为可切换的性能实验/演示备选。当前结果只支持“有计算和带宽余量”的判断，尚未达到正式24fps或全功能迁移验收。
