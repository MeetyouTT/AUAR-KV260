"""The selected-voice cache must not block touchscreen startup or hide outages."""
import threading
import time
from board.runtime.audio import channel_jobs


CONFIG={'enabled':True,'host':'192.168.50.1','port':8792,'timeout_ms':120000}


def test_feedback_download_runs_off_the_ui_thread_and_error_is_visible(monkeypatch,tmp_path):
    entered=threading.Event();release=threading.Event()
    def unavailable(*args):
        entered.set();release.wait(2);raise OSError('PC unavailable')
    monkeypatch.setattr(channel_jobs,'feedback_cache',unavailable)
    started=time.monotonic()
    jobs=channel_jobs.ChannelConversationJobs(CONFIG,'boot-test',tmp_path)
    try:
        assert time.monotonic()-started<.5
        assert entered.wait(1)
        assert jobs.public()['feedback_ready'] is False
        release.set()
        deadline=time.monotonic()+1
        while not jobs.public()['feedback_error'] and time.monotonic()<deadline:time.sleep(.01)
        assert 'PC unavailable' in jobs.public()['feedback_error']
        assert jobs.enabled()
    finally:release.set();jobs.close()


def test_failed_cache_can_recover_without_restart_and_config_change_refetches(monkeypatch,tmp_path):
    calls=[]
    def cache(config,root,*,social=False):
        if social:return {}
        calls.append(config['port']);return {'thinking':{'path':'fixture'}}
    monkeypatch.setattr(channel_jobs,'feedback_cache',cache)
    jobs=channel_jobs.ChannelConversationJobs(CONFIG,'boot-test',tmp_path)
    try:
        deadline=time.monotonic()+1
        while not jobs.public()['feedback_ready'] and time.monotonic()<deadline:time.sleep(.01)
        assert jobs.public()['feedback_ready']
        jobs.prepare_feedback(CONFIG);assert calls==[8792]
        jobs.prepare_feedback(dict(CONFIG,port=8793));assert calls==[8792,8793]
    finally:jobs.close()
