import threading
import pytest
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from tests.framework.test_board_speaker_business import Encoder,MODEL,quality,capture,BOOT


@pytest.mark.parametrize('queued_count',[1,2])
def test_queued_future_cancellation_callback_can_remove_jobs_during_shutdown(tmp_path,queued_count):
    service=BoardSpeakerBusiness.create(tmp_path/'public-speaker',encoder_factory=Encoder,
        board_boot_id=BOOT,quality=quality,expected_model_id=MODEL,anonymous_config={'enabled':True},
        wall_clock=lambda:1793400000.,data_origin='synthetic')
    entered=threading.Event();release=threading.Event()
    def block_sole_worker():
        entered.set();assert release.wait(3)
    blocker=service.pool.submit(block_sole_worker)
    try:
        assert entered.wait(1)
        for number in range(queued_count):
            meta,pcm=capture(number+1)
            meta['session_id']='public-session-'+str(number)
            service.submit_analysis(meta,pcm,'b'*32)
        with service.lock:
            assert len(service.jobs)==queued_count
            futures=[job['future'] for job in service.jobs.values()]
            assert all(not future.running() and not future.done() for future in futures)
        # cancel() on this queued future synchronously calls finished(), whose
        # original locked callback removes that same job. No timing race needed.
        assert service.close(timeout=.01) is False
        assert all(future.cancelled() for future in futures)
        with service.lock:assert service.jobs=={}
    finally:
        release.set();blocker.result(2)
        # Only for cleaning up the deliberately failing unmodified baseline.
        if service.closing.is_set() and not hasattr(service,'close_future'):
            service.closing.clear()
        assert service.close()
