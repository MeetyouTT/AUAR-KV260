# GLES2 帧内状态去重候选

三文件从当前已通过图像对照的 host 复制：gles2_renderer.cpp、gles2_renderer.hpp、tile_uv.hpp。只修改前两项；tile_uv.hpp逐字节相同。构造函数、frame协议、shader、局部UV、icon/mask LINEAR与color NEAREST均不变，无新TU依赖。host 主文件未改，无板端编译或负载。

缓存项为四个mode uniform各自的值、protection切换、RGB/alpha四元混合函数、活动纹理单元及两单元绑定、FBO、viewport、scissor开关与矩形、clear color。每个draw先置unknown；resize可能经原始GL助手改变状态，resize返回后再次置unknown。每帧首个写入一定实际执行，不借用上一帧或GTK上下文状态。

不变量审查：

- 所有draw、clear以及mask source迭代顺序不变；没有合并、移动或省略draw/clear。
- 每次mask重建仍先解绑unit1的mask纹理，再绑定mask FBO、关闭scissor全清，随后开启source scissor、写coverage；恢复color FBO/viewport和unit1绑定后再画内容。
- scissor数值是全局GL状态，FBO/viewport切换不自动失效；缓存比较的是完整四整数值，目标为mask或color时传入各自原数值。清除前的关闭始终受正确的已知状态约束。
- protection两次绘制仍依次为uniform1+保护混合、uniform0+原颜色混合，uniform cache也由专用protection()更新，不存在绕过缓存的直接写入。
- 最终quad仍独立VBO/EBO，仍恢复输出FBO、同尺寸viewport、关scissor、清背景、设置view/mode、绑定color纹理并执行原预乘over；末尾仍解绑unit1并回到unit0。
- constructor/target/texture的原始GL调用只发生在初始化/resize。它们之后缓存未知；正常帧内所有被缓存状态均只通过缓存助手写入。program、buffer和attribute设置没有跨帧缓存。

预算：固定StateCache预计ARM120B，以编译期sizeof<=160B限制；每帧两次置unknown，无动态容器或堆分配增加，无GPU资源/显存增加、无文件I/O或读回。相邻相同mode从每次4个glUniform1i降为0，混合函数和scissor在连续同值命令中各从N次降为1；unit0活动选择和保护双pass的重复纹理绑定也省去。mask全清、真正的纹理/FBO/viewport切换及所有draw都保留。没有保证提交尾延迟的降幅，需板测。

已执行review.py检查shader相同、tile_uv相同、draw/clear调用点数量相同及host未变，详见static-review.json。此项是源差异与手工状态流审查，没有生成镜像测试；C++编译、10+4图像对照、35秒离屏及300秒GTK由父代理统一进行。前版失败证据保持。
