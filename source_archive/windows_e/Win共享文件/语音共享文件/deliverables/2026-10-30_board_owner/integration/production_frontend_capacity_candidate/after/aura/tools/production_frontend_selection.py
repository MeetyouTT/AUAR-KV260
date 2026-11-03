"""Explicit same-weight frontend and capture-thread selections, no auto-start."""


def validate_frontend_options(value):
    optimization=value.get('frontend_optimization','baseline')
    priority=value.get('capture_priority_nice',0)
    if optimization not in ('baseline','combined'):
        raise ValueError('Choose baseline or reviewed same-weight combined frontend')
    if type(priority) is not int or priority not in (0,-10):
        raise ValueError('Capture consumer priority is disabled or fixed nice -10')
    return optimization,priority


def create_frontend_pool(directory,*,optimization,num_threads=1):
    from board.runtime.audio.board_capture import BoardFrontendPool
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
