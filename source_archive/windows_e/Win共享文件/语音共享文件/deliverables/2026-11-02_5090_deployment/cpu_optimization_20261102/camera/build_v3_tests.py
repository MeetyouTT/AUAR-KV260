from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE/'test_lazy_jpeg.py').read_text(encoding='utf-8')
assert source.count("candidate_v2/ui_camera_service.py")==1
source=source.replace('candidate_v2/ui_camera_service.py','candidate_v3/ui_camera_service.py')
new=r'''
    def retained_old_request_race(self,old_mode,new_mode):
        state,frame,_,_=setup_state(Codec(old_mode))
        resolve=frame.resolve;ready=threading.Event();release=threading.Event();values=[]
        def delayed():
            value=resolve();ready.set()
            if not release.wait(2):raise RuntimeError('test completion barrier timeout')
            return value
        frame.resolve=delayed
        worker=threading.Thread(target=lambda:values.append(state.preview(state.camera_epoch,1)))
        worker.start();self.assertTrue(ready.wait(1))
        state.publish_preview(2,950,PreviewJpeg(image(63),Codec(new_mode),state._preview_encode_lock))
        current=state.preview(state.camera_epoch,2)
        error=state.preview_error
        release.set();worker.join(1);self.assertFalse(worker.is_alive())
        self.assertEqual(list(state.frames),[1,2])
        self.assertEqual(state.preview_error,error)
        return current,values[0],error

    def test_old_retained_success_does_not_clear_latest_jpeg_failure(self):
        current,old,error=self.retained_old_request_race('ok','raise')
        self.assertIsNone(current);self.assertIsNotNone(old);self.assertTrue(error)

    def test_old_retained_failure_does_not_pollute_latest_success(self):
        current,old,error=self.retained_old_request_race('raise','ok')
        self.assertIsNotNone(current);self.assertIsNone(old);self.assertEqual(error,'')

    def test_producer_failure_before_cached_request_stays_visible(self):
        state,_,_,_=setup_state();first=state.preview(state.camera_epoch,1)
        state.preview_failed('synthetic newer raw publication failed')
        self.assertEqual(state.preview(state.camera_epoch,1),first)
        self.assertEqual(state.preview_error,'synthetic newer raw publication failed')
        self.assertTrue(state._preview_producer_failed)

    def test_producer_failure_after_request_start_stays_visible(self):
        state,frame,_,_=setup_state();resolve=frame.resolve;ready=threading.Event();release=threading.Event();values=[]
        def delayed():
            value=resolve();ready.set()
            if not release.wait(2):raise RuntimeError('test completion barrier timeout')
            return value
        frame.resolve=delayed
        worker=threading.Thread(target=lambda:values.append(state.preview(state.camera_epoch,1)))
        worker.start();self.assertTrue(ready.wait(1))
        state.preview_failed('synthetic newer raw publication failed');release.set();worker.join(1)
        self.assertFalse(worker.is_alive());self.assertIsNotNone(values[0])
        self.assertEqual(state.preview_error,'synthetic newer raw publication failed')

    def test_only_new_producer_publication_resets_producer_failure(self):
        state,_,_,_=setup_state();state.preview_failed('synthetic raw failure')
        self.assertTrue(state._preview_producer_failed)
        state.publish_preview(2,950,PreviewJpeg(image(64),Codec(),state._preview_encode_lock))
        self.assertFalse(state._preview_producer_failed);self.assertEqual(state.preview_error,'')
        self.assertIsNotNone(state.preview(state.camera_epoch,2))

    def test_twelve_same_fid_queued_requests_keep_no_retired_images(self):
        state,_,codec,_=setup_state();retained=[];threads=[];results=[]
        state._preview_encode_lock.acquire()
        try:
            for index in range(12):
                frame=state.frames[1][1];retained.append(frame);resolve=frame.resolve;entered=threading.Event()
                def waiting(resolve=resolve,entered=entered):
                    entered.set();return resolve()
                frame.resolve=waiting
                worker=threading.Thread(target=lambda:results.append(state.preview(state.camera_epoch,1)))
                threads.append(worker);worker.start();self.assertTrue(entered.wait(1))
                state.publish_preview(1,950,PreviewJpeg(image(index),codec,state._preview_encode_lock))
            self.assertEqual(len(state.frames),1)
            self.assertEqual(sum(frame._image is not None for frame in retained),0)
            self.assertEqual(sum(frame._image is not None for _,frame in state.frames.values()),1)
            self.assertEqual(codec.calls,0)
        finally:
            state._preview_encode_lock.release()
            for worker in threads:worker.join(2);self.assertFalse(worker.is_alive())
        self.assertEqual(results,[None]*12);self.assertEqual(codec.calls,0)
        self.assertIsNotNone(state.preview(state.camera_epoch,1));self.assertEqual(codec.calls,1)

    def test_same_object_republication_does_not_retire_itself(self):
        state,frame,codec,_=setup_state();state.publish_preview(1,950,frame)
        self.assertFalse(frame._retired.is_set());self.assertIsNotNone(state.preview(state.camera_epoch,1))
        self.assertEqual(codec.calls,1)

'''
marker="if __name__=='__main__':unittest.main(verbosity=2)"
assert source.count(marker)==1
source=source.replace(marker,new+'\n'+marker)
compile(source,'<camera-v3-tests>','exec')
with (HERE/'test_lazy_jpeg_v3.py').open('x',encoding='utf-8') as stream:stream.write(source)
print('Built v3 regression suite: 27 tests')
