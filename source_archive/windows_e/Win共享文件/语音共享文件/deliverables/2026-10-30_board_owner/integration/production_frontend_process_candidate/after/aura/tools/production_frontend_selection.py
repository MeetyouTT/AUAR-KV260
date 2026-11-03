"""Explicit same-weight frontend and capture-thread selections, no auto-start."""


def validate_frontend_options(value):
    optimization=value.get('frontend_optimization','baseline')
    priority=value.get('capture_priority_nice',0)
    process=value.get('frontend_process',False)
    if type(process) is not bool or process and (optimization!='baseline' or type(value.get('frontend_threads',1)) is not int or value.get('frontend_threads',1)!=1):
        raise ValueError('Process frontend is explicit baseline with one model thread')
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
        if optimization!='baseline' or type(num_threads) is not int or num_threads!=1:
            raise ValueError('Process frontend requires baseline/one model thread')
        from board.runtime.audio.board_frontend_process import BoardProcessSpeechGate
        return BoardFrontendPool(BoardProcessSpeechGate(directory,num_threads=1))
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
