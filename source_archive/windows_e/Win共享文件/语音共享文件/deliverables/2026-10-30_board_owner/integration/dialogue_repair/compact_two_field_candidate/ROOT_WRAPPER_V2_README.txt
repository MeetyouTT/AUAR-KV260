最新只用root_public_probe_v2.py；v1原b4文件、原回执保留，不用于本次实际推理。
唯一增量是在execute现场按已钉SOURCE_MANIFEST.before_sha256重验before所有5源，覆盖D01原host/contract。其余整模块AST与v1一致。
48本地fake/source测试PASS（原28+原wrapper18原样重放到v2+新2项before pin检查）；未执行模型/设备。

根代理Windows公开探针；默认dry，未执行推理。

原28项合同测试与新18项wrapper假依赖测试共46PASS。测试不调用GPU/模型/服务/麦克风/播放/真实Store；新wrapper测试中的backend是fake。
原5份after源、SOURCE_MANIFEST.json907bd0...及HANDOFF.jsond27a...保持原字节；本次仅新增root wrapper/pins/tests/模板/本说明。

命令（仅主控执行；ABBA和D01必须分开，不能在原真人/后台推理窗口内重叠）：
  D:/py312/python.exe -B -X utf8 <本目录>/root_public_probe_v2.py --experiment abba
  D:/py312/python.exe -B -X utf8 <本目录>/root_public_probe_v2.py --experiment d01
以上只打印计划，没有读取服务或进行推理。

实际调用由根先完成正常关闭UI、检查唯一writer已释放、确认原进程归属/后台推理停止，然后复制root_permit.template.json并填入fresh UTC、当前唯一runner PID、当前boot以及真实unit metadata；所有授权/关闭等布尔字段必须由根据实置true。模板不是许可。issued_utc在启动时仅120秒内有效，不能重用旧文件。
  D:/py312/python.exe -B -X utf8 <本目录>/root_public_probe_v2.py --experiment abba --execute --root-permit <fresh-abba.json>
  D:/py312/python.exe -B -X utf8 <本目录>/root_public_probe_v2.py --experiment d01 --execute --root-permit <fresh-d01.json>

每次只选一个experiment。ABBA固定4次、ABC/AB/AB/ABC、0warmup、固定seed8701/2048/120/temp0.6/thinkfalse。D01只有1次原正式入口：exact当前978B canonical system prompt，thinkTrue，无output_format，直接validate_model_reply，核391或三百九十一；不会把ABC别名或新AB拼入think路径。它不走CompactRequestAdapter，也不放宽原wire。200只证明flag请求被接受；thinking_output_observed单独列数值，0字符不证明模型没有内部思考。单次391通过不等于复杂推理或function calling通过。

SOURCE_PINS：当前live host fd4a8c...、wire39306...、contracte079...，原chatbody0ebd...、GPU41e3...及policyf34e...，exact prompt11b1...；详见ROOT_PROBE_PINS.json。ABBA仅在新Python测试进程加载candidate contract/adapter/host，原wire和原validator保持固定pin。D01用before原contract/host。代码用object.__new__(LocalModelBackend)，绝不调用constructor/from_config或启动第二TTS；原GpuCoordinator/NvidiaMemoryProbe/OllamaResidencyProbe和backend.llm的GPU准入/有限连接/取消finally保持。

旧root_direct_name_abba.py的NoRedirect/fetch/selected_static_prompt原AST从SHA8a1ab5...文件提取复用。旧execute及其过时SOURCES不执行；新pins绑定目前已安装host与v17。每次请求前后仍需hostrole model_inference_only、oktrue/activefalse/pending0/loggingfalse、模型27B及OmniVoice16暖态，原唯一runner PID/模型所在D盘blob路径，/api/ps唯一选定模型/ctx2048及size/VRAM稳定。UI/writer的关闭由根fresh attestation提供，本脚本不SSH、不关闭UI或访问私库。原其他模型、fit4096/53层/保留显存预算不变。

每个模型调用原deadline30秒；GPU/网络/runner metadata也沿原有有限超时。根给外层进程设足够总预算（4次最高120秒加每次guard的有界metadata时间）；意外强制终止仅使用根已审的自有进程/进程组收尾，不按进程名杀Ollama/TTS或其他模型。本wrapper不创建服务、模型进程，也不主动发kill；超时/取消依靠原backend关闭自有socket并释放本测试进程lease，之后再做postguard。它没有跨进程原子模型锁，不能替代根的唯一测试窗口。

输出仅root_benchmark_runs/<abba|d01>_<随机>.json；有完整结果路径、fixed error_code、token/duration、数值thinking/HTTP状态、speech hash、guard归属metadata。不输出/归档提示词、reply正文、thinking正文、PCM或真实私数据；D01观察器只盯本chat _ResponseSocket，residency GET的200不会冒作think accepted。无隐藏重试。错误/数学语义UNKNOWN可保留证据并返回失败，不把完成一次请求当性能/功能PASS。加载/缓存/输出token和cross-arm文本hash要分别核对，不只比较总耗时。

正式379源/配置/私库不改；执行后根按既有正常流程恢复本次真实监听偏好。尚无新模型实测/提速结论。若公共结果有收益，再考虑配套Windows+board闭合发布，原用户实际首声/完整业务体验需另验。
