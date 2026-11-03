# 板端验收脚本修正记录

第一次 `start` 阶段在旧 manager 已正常卸载后停下，未停止服务、创建临时 drop-in 或启动新候选。实际返回为 `slot 0 is not used or invalid`，与脚本预期 `No active design` 不同；overlay 和 render 节点均已经移除，卸载协议返回 `0 (Ok)`。随后通过旧 manager 重新加载官方应用，query 和同图分类返回 0，原 Top-5 保持一致。

v2 仅修正旧 manager 的验收契约：允许其保留不活动 base 并返回空 slot；新候选仍要求 `No active design`。两者仍必须同时满足协议成功、实际 overlay/render 节点消失。此改动没有放宽硬件卸载检查，没有改动候选源码或二进制。

主机 `board/validate-v1.py` 和板端 `board/validate.py` 保存原版本。v2 使用新板端文件 `board/validate_v2.py`，原失败日志保留。v1 SHA-256：`745a9128829b24f9af719c1de356d9e5a02b9967279ead6f4f582ca8476f6c61`。

v2 已实际切换至候选，但第一个列包请求发生在 `Type=simple` 服务进程创建之后、`dfx_init()` 完成默认 FPGA 加载并开始监听 socket 之前，返回 `Connection refused`。后续只读采集确认候选没有退出，官方 overlay/render 均存在；列包、query 和同图分类随后全部返回 0。启动日志和首次失败没有删除。

v3 为服务切换增加最多 30 秒的只读就绪探测；只允许暂时的 socket 连接未就绪，并同时检查进程仍在运行，其他错误立即失败。压力测试中的客户端请求仍不重试。`ready` 阶段在当前已启动候选上完成剩余启动验收，避免无意义的再次硬件加载。后续所有服务切换也执行该探测。候选二进制和源码保持原哈希。

v3 压力测试的四个列包线程完成了各 250 次查询；目录线程在首轮删除后的 `/proc/<pid>/fdinfo/7` 读取中遇到 `FileNotFoundError`。fd 7 为短连接窗口中的描述符，`/proc` 枚举期间允许它被关闭。v4 对这类消失的非持久描述符继续枚举，同时仍要求恰好一个持久 inotify 描述符。监听数量、子孙回收、进程、协议和推理断言保持不变。旧 fixture 仅在标记核验后清理；重新完整执行 1000 查询及 100 轮目录测试，不把首次不完整目录测试计为通过。

v4 的完整 1000 查询/100 轮目录测试通过。随后活动目录移出检查中，运行 slot、overlay 和 render 节点均保留，监听回到基线；新启动的 `xdputil query` 返回 134，明确因为 `/etc/vart.conf` 引用的原位置 xclbin 文件已经移走而无法打开。原始错误和配置均保留。这不是实际硬件自动消失的证据，也不能当作推理通过。

v5 只给测试子进程设置现有库支持的 `XLNX_VART_FIRMWARE`，指向移出后的同一 xclbin，并在调用前比对原文件哈希。全局 VART 配置没有为此重写，fingerprint 校验没有关闭，模型/图片/原库保持不变。先在当前被移出的加载状态下实际复验和显式卸载，恢复官方应用；再重新完整执行活动目录消失、同名复用和物理卸载用例。是否通过以对应实际退出码、query、Top-5、overlay/render 及 slot 证据为准。
## 冷启动主机复核的关键词误报

第一次主机 postboot 回读已验证 5223 文件和 23 次分类，但宽松 `Oops:` 子串命中了 `mtdoops: mtd device (mtddev=name/number) must be supplied`。该提示同样存在于修复前的启动内核日志。为 `BUG:`/`Oops:` 增加单词边界后，对同一归档重新完整核验通过，没有更改板端日志或候选程序。

首次失败保留在 `reviews/20261004T084458.705705Z-postboot/review.json`，最终通过记录为 `reviews/20261004T084536.786164Z-postboot/review.json`。它是独立的主机日志匹配错误，不计入前面四次板端不完整验收。
