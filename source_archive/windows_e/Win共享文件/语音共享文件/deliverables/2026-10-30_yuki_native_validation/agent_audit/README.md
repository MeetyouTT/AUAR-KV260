# NekoMote 无图形验证入口审计

固定源码：Chocola-X/NekoMote@4fbf55aa6009df76ac40dc5f18e3781914bc464f。
本代理上轮仅通过 GitHub 读源码到内存，没有克隆源码，没有本地克隆路径。
源码获取、主构建与板端探针由父代理负责。本目录仅包含独立验证辅助脚本。

## 现有 CPU 审计入口

已有 nekomote_runtime_audit，无需先写新 C++ harness。它直接
import_emote → compile_playback → PlaybackInstance(seed=1)，默认启用物理。
初态和每条时间线独立 reset，主时间线用 Replace，差分用 AdditiveParallel。
每个作者步调用 step/prepare_frame，记录最大 commands、vertices、masks 与错误位置。
退出码 0 表示这些 CPU 用例通过，2 表示导入/编译/用例失败，1 表示参数或报告 I/O 错误。
不依赖窗口、GPU、音频服务，不生成 bundle，不复制纹理，只写指定报告。
120 作者步等于两秒，未覆盖更长动作和全部组合。CPU 通过不等于画面正确。

## 输入：需要真实 EMS 导出

import_emote.cpp 固定检查 spec == "ems"、3 <= version < 4。
若现有 source_yuk0/yuk_0.json 仍为 win，应先在独立目录解包已验证的
yuk_0.ems.psb，或用既有 FreeMote Win→EMS 转换后导出 JSON/resx/纹理。
不要只改 spec，因为中性颜色、纹理、坐标等平台语义也可能不同。

输入为 EMS JSON、顶层含 Resources 对象的 resx JSON，以及实际纹理文件。
texture.pixel="#resource#KEY" 经 Resources[KEY] 映射为 resource_root 下的相对路径。
若 pixel 缺失，显式传 --texture tex=relative/path.png；tex 是 source 下的纹理名。
源 JSON/resx/PNG 保持只读；导入审计不需要产生另一份 bundle。

## 构建 CPU 目标

Linux/WSL 命令模板，src/build 由父代理填写。要求 CMake≥3.25、C++20。
PNG/zlib/FLAC、JSON/FastFloat/stb 依赖按项目构建文档准备。
根构建还无条件配置 src/ui，因此即使只指定 CPU 目标也需要 pkg-config/fontconfig 开发元数据。
USE_SYSTEM_DEPS=ON 使用现有系统依赖，缺失即报错。

~~~sh
cmake -S "$src" -B "$build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DNEKOMOTE_USE_SYSTEM_DEPS=ON \
  -DNEKOMOTE_BUILD_ABI=OFF -DNEKOMOTE_BUILD_PREVIEW=OFF \
  -DNEKOMOTE_BUILD_PLAYER=OFF -DNEKOMOTE_BUILD_TESTS=OFF \
  -DNEKOMOTE_BUILD_TOOLS=ON -DNEKOMOTE_BUILD_VULKAN=OFF \
  -DNEKOMOTE_BUILD_QT_QUICK=OFF -DNEKOMOTE_BUILD_PLASMA=OFF \
  -DNEKOMOTE_BUILD_LAYER_SHELL=OFF -DNEKOMOTE_BUILD_X11=OFF
cmake --build "$build" --target \
  nekomote_import nekomote_runtime_audit nekomote_playback_probe
~~~

BUILD_ABI 默认 ON；即使关窗口仍会引入 render_gl/audio，因此须显式关 ABI。

## 导入审计及逐时间线求值

~~~sh
"$build/bin/nekomote_import" "$model/yuk_0.json" "$model/yuk_0.resx.json" \
  --resource-root "$model" --audit-report "$audit/import-report.json"
"$build/bin/nekomote_runtime_audit" "$model/yuk_0.json" "$model/yuk_0.resx.json" \
  --resource-root "$model" --steps 120 --output "$audit/runtime-report.json"
~~~

两工具均支持重复 --texture NAME=RELATIVE_PATH。跨平台包装器记录二进制哈希、
argv、退出码、stdout/stderr，导入失败时停止：

~~~sh
python3 "$audit/run_cpu_audit.py" \
  --importer "$build/bin/nekomote_import" \
  --runtime-auditor "$build/bin/nekomote_runtime_audit" \
  --model-json "$model/yuk_0.json" --resx-json "$model/yuk_0.resx.json" \
  --resource-root "$model" --steps 120 --output "$audit/cpu-run"
~~~

execution.json 的 commit 字段是预期源码版本，并非包装器独立验证的二进制来源。
父代理应另存 git rev-parse HEAD 证据。

## 静态预检和确定性请求

audit_source.py 只检查部分已知 importer/geometry 门槛，不转换 PSB，不认证完整兼容：

~~~sh
python3 "$audit/audit_source.py" "$model/yuk_0.json" \
  --resx "$model/yuk_0.resx.json" --resource-root "$model" \
  --output "$audit/source-preflight.json" \
  --probe-requests "$audit/probe-requests" --steps 120
~~~

报告保留所有 type-12 节点及 mask 名单，不把 layerIndexMap 数量当作遮罩数。
已知雪妃 bp=32、cc=null、stencilType=5、bm=0/19、transformOrder=[0,3,2,1]
是有利条件；meshSyncChildMask、inheritMask、参数绑定和激活分支仍需实际验证。
conditional_runtime_checks 是候选问题，不等于已经证实的失败。

## CPU 通过后再生成 bundle 和帧协议

~~~sh
"$build/bin/nekomote_import" "$model/yuk_0.json" "$model/yuk_0.resx.json" \
  --resource-root "$model" --output "$audit/yuk0-bundle"
"$build/bin/nekomote_playback_probe" "$audit/yuk0-bundle/model.nkm" \
  "$audit/probe-requests/00.json" "$audit/probe-frame-00.json"
~~~

bundle 目录必须尚不存在，工具拒绝覆盖。此步会复制所引用纹理，第一轮 CPU 覆盖无需执行。
probe-requests/index.json 映射初态 00.json 和其后每条 timeline 请求。
输入使用 seed=1、主动作 flags=0、差分 flags=3。playback_probe 可输出帧顶点、
索引、commands/masks 与物理观测，作为后续 GLES2 上传的 CPU 帧协议。
仍需验证 GPU 混合/遮罩。待机宜另测 600 作者步，观察更长眨眼和物理周期。

## 最小 C++ 链

已有 runtime_audit 就实现了以下链路，所有返回值须检查；program 必须活得比 instance 长：

~~~cpp
asset_io::ImportOptions opts;
opts.json_path = model_json;
opts.resx_path = resx_json;
opts.resource_root = resource_root;
auto imported = asset_io::import_emote(opts);
auto compiled = runtime::compile_playback(imported.asset);
runtime::PlaybackInstance instance(*compiled.program, {1});
auto timeline = compiled.program->animation().find_timeline(label);
auto status = instance.play(timeline, runtime::TimelinePlayMode::Replace);
status = instance.step();          // animation + anchors + physics，60Hz 作者步
status = instance.prepare_frame(); // 最终几何与 CPU 绘制协议
auto frame = instance.frame();     // borrowed spans，下一次 mutation 后失效
~~~

## 固定源码定位

- [导入 CLI](https://github.com/Chocola-X/NekoMote/blob/4fbf55aa6009df76ac40dc5f18e3781914bc464f/tools/import_emote/main.cpp)
- [EMS/资源检查](https://github.com/Chocola-X/NekoMote/blob/4fbf55aa6009df76ac40dc5f18e3781914bc464f/src/asset_io/import_emote.cpp#L526)
- [CPU 审计](https://github.com/Chocola-X/NekoMote/blob/4fbf55aa6009df76ac40dc5f18e3781914bc464f/tools/runtime_audit/main.cpp)
- [Playback API](https://github.com/Chocola-X/NekoMote/blob/4fbf55aa6009df76ac40dc5f18e3781914bc464f/include/nekomote/runtime/playback.hpp)
- [固定请求/帧导出](https://github.com/Chocola-X/NekoMote/blob/4fbf55aa6009df76ac40dc5f18e3781914bc464f/tools/playback_probe/main.cpp)
- [已有导入测试](https://github.com/Chocola-X/NekoMote/blob/4fbf55aa6009df76ac40dc5f18e3781914bc464f/tests/unit/test_import.cpp)
- [几何编译门槛](https://github.com/Chocola-X/NekoMote/blob/4fbf55aa6009df76ac40dc5f18e3781914bc464f/src/runtime/geometry_scene.cpp#L247)
