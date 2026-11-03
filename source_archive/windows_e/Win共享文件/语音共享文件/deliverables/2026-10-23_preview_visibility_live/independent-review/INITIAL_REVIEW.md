# GUI视频链路CPU独立初审

范围：只读本地源码与主任务已读回的证据，未访问UART/板卡、未开启音频/模型、未改业务或共享入口。现役7源来自`current-source-proof.json`，已按SHA核对；共享仓中旧GTK与现役布局/映射逻辑不同，本文以`baseline/aura/`为准。方案/竞赛包README、项目规则和最新CPU日志已读。

## 结论

**存在“预览视图隐藏后仍推流”的真实生命周期缺口，值得优先修；但仅凭`queue1:src`名称尚不能把36.71%单核CPU全部归给它。** 相比另写像素内核，先让隐藏的相机预览停止转换/缩放/送XID，不改变显示内容或业务帧率，收益条件更清楚。

现役`board_avatar_gtk.py:396`只给vision DrawingArea接`map→attach_preview`，没有对应`unmap→detach`；`show_page`在579行切换Gtk.Stack，随后只控制portrait/insights可见性。`attach_preview`在924行创建pipeline，`CameraPreviewWorker.push`遍历全部`outputs`，其work循环不检查widget是否仍mapped。一次访问vision页后，回main不会从outputs移除vision，该pipeline继续处理新相机帧。`large`关闭时已有显式detach（906行）；必须保留放大窗口的独立生命周期，不能只按主页面全关输出。

角色portrait在vision页会隐藏（583行），但其native pipeline同样没有可见性暂停；这也是后续候选，但显示暂停和控制/音频/动画时钟须分开处理，不宜顺带改控制器或8fps约束。

## 两条不同pipeline

| 分支 | 数据与路径 | 已有边界/事实 |
|---|---|---|
| 角色native | RGB bytes→`aura_rgb565_copy`→RGB16 appsrc→queue→identity→ximagesink | C++入口已有NEON RGB565；没有videoconvert。固定8fps独立worker/presenter已生效。caps仍24/1和duration1/24，但没有videorate或额外循环生成帧；不能据此认定实际推24fps。|
| 相机预览 | RAM内640×480 BGR文件→Python Gst.Buffer复制→appsrc→queue→videoconvert→videoscale→目标尺寸→identity/Python回调→ximagesink | 每个输出各一条pipeline、各自复制和转换；queue下游丢旧帧，appsrc也有一个BGR帧的容量检查。过期帧在identity sink pad丢弃，读回ref用于界面动作时效。|

角色路径在本次主任务读回时`avatar_display.fps=8.00009`，received与pushed计数存在历史启动/重绑差值，不能当重复帧证据。`FramePresenter`每次取走pending后置None，generation检查后只push一次。该路径已经优化，不重复计功。

相机work每10ms轮询并不意味着100fps推流。参考`board.vision.local_preview.RawFrameReader`已有inode/version与frame_id去重；现役这份依赖未列入7源读回表，主任务如需把去重作为本次源码验收结论，应补其SHA。JPEG分支也对preview key去重。

两条queue均未显式命名，自动编号由pipeline创建/重建顺序决定。`queue1:src`的下游可能是相机转换/缩放，也可能是角色Ximagesink；创建时间和编号只算线索。需要结合实际页面、preview displayed_frames增量、portrait received增量、native/相机回调所在TID或低开销native采样确认归属。不能因名字直接说GIL或硬件慢。

## 最小修复应遵守的状态契约

1. vision DrawingArea真实unmap时移除该name的输出并令pipeline NULL；重新map始终重新绑定XID并PLAYING。现役attach特意取消旧“binding相同就跳过”，是为修drawable重映射，不能恢复那个缓存捷径。
2. 定时50ms bind回调已有realized/mapped检查。unmap→延迟bind必须不重建隐藏输出；多次map/unmap不残留旧pipeline。程序cleanup、重复detach和关闭large都应幂等。
3. 隐藏vision输出后，`read('vision')`应无可见ref。`ui_runtime.frame_visible/frame_reference`据此变false/None，ask_frame等动作暂不可用；重新显示拿到新帧后恢复。不要通过延长250ms TTL或伪造旧ref保持“可见”。
4. hands-free attention在现役构造中取`services.identity_snapshot`，独立于preview sink显示ref。候选应保留这条业务输入，不能因隐藏预览停止相机采集/检测/身份，也不触碰音频常驻保护。
5. 如果`outputs`已经为空，可避免继续读RawFrame文件和调用services.read；但必须在首个output重新attach时重置reader/last_key，确保同一当前源帧能立即显示。不要把空输出期间的旧source_age误认为当前新帧。

相机`videoconvert/videoscale`换序不是天然零差：若协商目标为RGB16，现役先量化再缩放，换成先BGR缩放后量化会改变取整/抖动/插值。若未来选择RGB565直接推送，也必须做真实像素与显示尺寸/stride对照，不能直接继承角色RGB565的历史通过结论。

## 还缺的决定信息

- 当前`ui_page`与大预览是否打开；vision和large的displayed_frames/update_hz/transport增量。
- `queue1:src`实际执行的native栈或本pipeline回调TID映射；仅看同一pid不够。
- 相机pipeline协商caps、预览目标尺寸和X11 visual位深，以区分转换/缩放/X显示的成本。
- 低成本的显示开关对照：自然空闲时只改变预览可见性，保持同相机/模型/帧率/音频，再对比GUI进程CPU和各线程；绝不并开第二DPU owner或用隐藏角色/降帧伪装收益。

本报告未执行测试或板端实验；语义缺口由源码证明，CPU收益与故障归因仍待主任务实测。
