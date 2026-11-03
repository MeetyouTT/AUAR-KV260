"""Six distinct chat inputs, exact original target/TTS, cold-shape graph validation."""
from cuda_graph_probe import experiment

experiment.RESULT_PATH=experiment.HERE/'graph_validation.json'
experiment.RUN_INDEX=9
experiment.INPUTS=('今天比较开心，陪我聊聊','今天有点累，想和你说说话','我有点紧张，明天要参加一个活动','今天下雨了，我只想待在家里','我刚读完一本有意思的书','谢谢你陪着我，晚安')
experiment.probe_dflash.REPORT_PATH=experiment.HERE/'graph_validation_runner.json'
try:experiment.main()
except BaseException as exc:
    experiment.REPORT.update(status='FAILED_NOT_DEPLOYED',error=type(exc).__name__+': '+str(exc))
    experiment.save();raise
