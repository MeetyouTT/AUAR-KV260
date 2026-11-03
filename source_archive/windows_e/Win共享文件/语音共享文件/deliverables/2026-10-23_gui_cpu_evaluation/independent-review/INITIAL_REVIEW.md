# GUI CPU 独立初审

范围：只读本机现役7份GUI核心源码、current-source-proof.json，以及10月20—21日已交付的渲染优化证据。没有访问板卡/UART、启动音频/图形服务或模型，没有修改业务源。本报告是候选判断，性能需主任务的同输入回放证明。

当前30秒240帧记录：core p50/p95约33.06/65.25ms，total35.89/68.48ms，public1.02/2.04ms，compose_resize1.18/2.09ms，jpeg0.12/0.24ms。core覆盖controller.tick，不是纯像素CPU时间；各阶段p50/p95不可直接相加。当前数字支持先细分core，不支持从此直接认定GIL或摄像头导致。

## 最高价值候选：IDLE身体插值推迟到已有融合pose

现役 `IdleBodyTrack.__init__` 将身体播放器的 `blend_frames` 固定为 `native.materialize_blend`。这已替换历史PIL插值，是10月21日真实完成的优化，不应再重复提作新收益。

但在IDLE且asset不是mouths.keys时，`RealtimeFacials.apply`只需要身体图，再由BlinkLayer/最终pose处理；此时提前生成整张RGBA插值图会产生全帧blend、ctypes输出buffer、PIL.frombytes，再由NativePixels.data导出bytes。现有NativePixels.blend已经能够返回带 `_native_blend=(a,b,t)` 的轻量代理，NativePixels.pose已有aura_pose_blend融合路径，可以直接消费两张原图。

建议仅让这一条IDLE路径的 `body.sample`选lazy blend，其余路径保留当前行为：

- 说话路径仍须materialize，因为`composite_idle_mouth`需要PIL对真实身体像素裁剪/拷贝/合成；不能把一个共享首图im的lazy代理直接交给PIL图像操作。
- 现役刚读回的 `BlinkLayer.apply` 在存在眼睑layer时，已调用`core.native_pixels.materialize(base)`。因此IDLE眨眼可以落回原先材料化处理；不应只凭历史共享文件（缺该行）断定当前眨眼会坏。
- 非native路径、LISTENING/THINKING/反应动作，以及口型中的gain=0关闭阶段都应保守保持原路径，除非另行证明。
- 最终RGB像素必须与基线逐帧比较；不能假定C++融合混合与先aura_blend再pose必然逐字节相同，尤其NEON/尾部混合和alpha背景舍入。

最低验收：固定状态/时间序列、同随机种子、同资产、同native threads=3和同output尺寸，分别包含无眨眼、眨眼开始/中间/结束、身体相邻帧插值、动作/说话退出、状态切换。比较图像mode/size、RGB像素、meta中的index/source_position/矩阵/状态，并监控base原图未被改写。ABBA先warmup再计时；记录线程CPU和process CPU，native库OpenCV线程耗时不能只用调用线程CPU代表。

## 不优先做的项目

1. `NativePixels.data`已有id+weakref校验、LRU上限和原图bytes复用；不能把“每次pose都image.tobytes”当已确认问题。动态合成图无法仅按id跨帧缓存，必须保持不可变发布规则。
2. `NativePixels.output.raw`和PIL.frombytes有拷贝，但改成frombuffer复用会使已发布帧随下次pose被覆盖；若非主要热点，不先引入buffer生命周期协议。
3. core.display_frame(IDLE)后body.sample(IDLE)看似重复，但两者拥有独立播放器/阶段状态。直接删除core调用或复用同一meta可能改变FSM exit/burst/阶段机时序，风险高于上述lazy像素路径。
4. 现役RealtimeController/StreamingController已经消费render_requested分频；不再以此作为新优化。
5. public快照、Native RGB565、口型ROI、NEON blend、动作期间跳过不显示身体、固定8fps送显已完成；不重复计功，不降画质或帧率换CPU数字。

## 等待的决定性数据

主任务短时headless profile应把冷加载/解码排除计时，然后观察body.materialize_blend、NativePixels.pose与C++flatten/affine/resize分段。若pose/affine远高于身体材料化，lazy路径收益可能有限；若profile主要是文件读取或PNG decode，先修复warmup/缓存实验条件，不能拿冷态开销当稳态热点。
