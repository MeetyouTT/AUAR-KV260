"""Explicit same-weight frontend and capture-thread selections, no auto-start."""


def validate_frontend_options(value):
    optimization=value.get('frontend_optimization','baseline')
    priority=value.get('capture_priority_nice',0)
    process=value.get('frontend_process',False)
    capture_process=value.get('frontend_capture_process',False)
    if type(capture_process) is not bool or capture_process and process is not True:
        raise ValueError('Automatic capture process requires explicit frontend process')
    if type(process) is not bool or process and (optimization not in ('baseline','combined') or type(value.get('frontend_threads',1)) is not int or value.get('frontend_threads',1)!=1):
        raise ValueError('Process frontend requires a reviewed mode with one model thread')
    if optimization not in ('baseline','combined'):
        raise ValueError('Choose baseline or reviewed same-weight combined frontend')
    if type(priority) is not int or priority not in (0,-10):
        raise ValueError('Capture consumer priority is disabled or fixed nice -10')
    return optimization,priority


def create_frontend_pool(directory,*,optimization,num_threads=1,frontend_process=False):
    from board.runtime.audio.board_capture import BoardFrontendPool
    if type(frontend_process) is not bool:
        raise ValueError('Explicit process frontend boolean required')
    if frontend_process:
        if optimization not in ('baseline','combined') or type(num_threads) is not int or num_threads!=1:
            raise ValueError('Process frontend requires a reviewed mode/one model thread')
        from board.runtime.audio.board_frontend_process import BoardProcessSpeechGate
        return BoardFrontendPool(BoardProcessSpeechGate(directory,num_threads=1,optimization=optimization))
    if optimization=='baseline':
        from board.runtime.audio.board_gtcrn_fft import BoardFftSpeechGate
        gate=BoardFftSpeechGate(directory,num_threads=num_threads)
    elif optimization=='combined':
        if type(num_threads) is not int or num_threads!=1:
            raise ValueError('Reviewed combined candidate requires one CPU thread')
        from board.runtime.audio.board_gtcrn_reuse import ReuseFftSpeechGate
        gate=ReuseFftSpeechGate(directory,num_threads=1,buffer_reuse=True,io_binding=True)
    else:
        raise ValueError('Unknown frontend selection; no fallback')
    return BoardFrontendPool(gate)


def priority_recording_options(gui,visual_controller):
    from board.runtime.audio.board_capture_priority import PriorityBoardAutomaticCapture,PriorityBoardBargeCapture
    return dict(audio_frontend=None,
        auto_capture_factory=lambda *args,**kwargs:PriorityBoardAutomaticCapture(*args,
            frontend_factory=gui.frontend.acquire,**kwargs),
        barge_capture_factory=gui.runtime.make_barge_capture_factory(visual_controller.output,
            lambda:getattr(visual_controller,'reply',''),gui.frontend.acquire,capture_type=PriorityBoardBargeCapture))


def automatic_capture_recording_options(gui, options):
    from board.runtime.audio.board_frontend_auto import RemoteAutomaticCapture
    def speech_start_ready(capture_id):
        recording=gui.recording
        return bool(recording is not None and ((recording.monitor_owned and recording.monitor_key) or recording.auto_enabled)
            and recording.listen_id==capture_id and recording.capture is not None
            and getattr(recording.capture,'capture_id',None)==capture_id)
    result=dict(options)
    result['auto_capture_factory']=lambda *args,**kwargs:RemoteAutomaticCapture(*args,
        frontend_pool=gui.frontend,speech_start_ready=speech_start_ready,**kwargs)
    return result
