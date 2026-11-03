"""Release unused CUDA allocator blocks only; weights remain on GPU."""
import memory_schedule_probe as experiment

experiment.RESULT_PATH=experiment.HERE/'trim_cache.json'
experiment.MODES=('resident','trimmed','trimmed','resident')
experiment.RUN_INDEX=7
experiment.probe_dflash.REPORT_PATH=experiment.HERE/'trim_runner.json'
try:experiment.main()
except BaseException as exc:
    experiment.REPORT.update(status='FAILED_NOT_DEPLOYED',error=type(exc).__name__+': '+str(exc))
    experiment.save()
    raise
