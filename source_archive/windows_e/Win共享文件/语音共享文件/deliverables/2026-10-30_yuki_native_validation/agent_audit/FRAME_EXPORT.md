# 直接 EMS → CPU 帧协议

frame_export.cpp 只使用 import_emote、compile_playback(PhysicsMode::Enabled)、
PlaybackInstance 及上游 tools/frame_json.hpp，不加载 model.nkm。
上游源码保持原样；本文件属于独立验证辅助目录。

## 编译

父代理已有独立 probe_build 的 yuki_core 目标时，可在该独立项目末尾包含：

~~~cmake
include("${ROOT}/agent_audit/frame_export.target.cmake")
~~~

然后只构建 yuki_frame_export。不要修改上游主 CMake。
也可直接链接已经构建的静态库：

~~~sh
c++ -std=c++20 -O2 \
  -I"$root/source/include" -I"$root/source/tools" -I"$root/deps/json" \
  "$root/agent_audit/frame_export.cpp" "$build/libyuki_core.a" \
  -o "$build/yuki_frame_export"
~~~

## 运行

先用单帧样例核验：

~~~sh
"$build/yuki_frame_export" \
  "$root/inputs/ems/yuk_0.ems.json" "$root/inputs/ems/yuk_0.ems.resx.json" \
  "$root/agent_audit/frame_scenario_smoke.json" "$evidence/frame-smoke.json" \
  --resource-root "$root/inputs/ems"
~~~

较完整示例为 frame_scenarios.json：A 待机、face_cheek 指定时段 transition、
B 待机加 arm_type=1。参数通过 transition API 设置；示例不声称离散 cheek
变量能得到视觉连续的表情。此处用于验证实际求值和渲染路径。

CLI：

~~~text
frame_export MODEL.ems.json MODEL.ems.resx.json SCENARIO.json OUTPUT.json
  [--resource-root DIR] [--texture NAME=RELATIVE_PATH]
~~~

输出父目录须事先存在。退出码 0 成功、2 导入/场景/求值失败、1 用法/输出失败。
失败时仍写 ok=false 的 JSON 和错误细节；不能将部分 snapshots 当完整通过。

## 场景约定

顶层 seed 只接受 1；scenarios 是非空数组，每项：

- name：唯一名称。
- idle_timeline：存在且受支持的主时间线，本例用真实雪妃 A/B 通常待机。
- ticks：总作者步，0..36000；固定 60Hz。
- parameters：初始参数对象；值为数值或 {value,frames,easing}。
- events：按 tick 非降序排列的 {tick,parameters}，tick 范围 1..ticks。
- capture_ticks：指定保存帧的 tick 数组，不能重复，0 表示初始状态。

每场景创建独立 instance 后 reset，先播放 idle，再应用初始参数。
tick N 的事件在第 N 次 step 前应用；snapshot N 是 step/physics/prepare_frame 后状态。
非 capture 的中间步仍进行 step 和 prepare_frame，不跳步，不关闭物理。

## 输出

顶层 texture_bindings 给出完整 TextureBinding id/name/path/width/height；
path 相对 resource_root。model 含 screen/origin、author_scale、mirror、
base_motion 和本例固定 origin=[0,0]/instance_scale=1。

scenarios[].snapshots[]：

- frame：上游完整 vertices、indices、commands、mask_commands、masks、
  composition、纹理 ID/尺寸。顶点是 x,y,u,v,r,g,b,a。
- bounds：全部顶点、可见 draw_commands、mask_commands 三类 AABB。
- parameters：该帧所有已解析变量值。
- state：状态码、作者 tick 数、idle 权重/播放状态及 physics_enabled。

帧字段与 enum 数字严格保留上游定义，并在顶层 protocol 给出数值映射。
mask=0 无遮罩，其余为 masks 一基索引；所有命令共享同一顶点/索引缓冲。
位置 Y 向下、UV 原点左上，顶点颜色为 straight RGBA。mirror 属于呈现步骤，
不能在未知位置多翻转一次。导出只是 CPU 协议，不代表已验证 GLES2 画面。

上游 RenderFrame 的遮罩注释还规定 union-alpha、5bit 存储覆盖率、
双线性取样、floor-power-of-two 输出和内容组裁剪边界。完整画面对照须遵守
该契约；简单将 mask 当成普通透明图叠加不构成等价渲染。
