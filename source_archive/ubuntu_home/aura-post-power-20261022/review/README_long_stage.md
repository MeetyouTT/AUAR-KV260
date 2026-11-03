# 长测生成与单helper传输独立审查

审查通过，当前未发现阻塞项。只读两份实现及生成的600秒helper；未执行UART、板卡、systemd、相机或音频操作，也没有导入/执行原实板短helper。

10项本地检查通过：AST验证600秒121样本/最后索引120、1800秒361/360，确认没有24→120→600的索引陷阱；restore finalbody逐AST相同，变动仅窗口/名称/计时器常量。GIL1ms、原模型/调度针脚、30ms/5ms和重试参数未由extend更改。当前具体short是light1时效＋1ms双模型诊断，不能把它的长测结果称作已启用重试的结果。

包装用sys._getframe().f_code.co_filename关联当前执行源，未误用导入短module的__file__。短源SHA必须匹配；600启动要求短测complete/passed/rollback_verified；root已补1800要求600 scope通过。现有600生成文件1cdd…保留此前等价的600启动前置，新1800必须从更新后的builder生成。

单helper传输复用既有framed协议；launch body核验boot、bundle SHA、tar恰好一个普通source.py、size<300000及源SHA，随后runpy。已有目标仅字节一致才复用，否则拒绝；新目标xb独占创建，不覆盖原源。root在审查期间补了namespace和父目录resolve检查；临时文件反例确认父symlink/最终symlink、额外tar成员、tar symlink、300000字节、错误boot/hash和不同已有目标都被拒绝。

launch body测试仅在TemporaryDirectory执行，boot路径和namespace常量映射到临时目录，runpy替换为记录调用的stub；真实传输与实板推理不在本审查证据内。最初夹具在root同步加namespace门期间被拒的日志保留为旧夹具错误，最终10项通过日志才是验收证据。

准确文件SHA与结论见long-stage-review.json；测试为test_long_and_stage.py，最终日志为long-stage-tests.txt。
