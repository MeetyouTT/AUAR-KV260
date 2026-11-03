"""Host synthetic native-video check; no camera, board or audio device."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

REPO = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0,str(REPO))
from tools.preview_board_touch import LayoutPreview
from tools.board_camera_preview import CameraPreviewWorker
from tools.board_screen_capture import capture
from board.vision.local_preview import RawFrameStore
from PIL import Image


def main():
    output = Path(__file__).with_name('native-video')
    output.mkdir(exist_ok=True)
    preview = LayoutPreview()
    stage = preview.stage
    preview.example = False
    owner = {'board_boot_id':'preview-only','service_epoch':'native-test','camera_epoch':'b'*32}
    reference = {'camera_epoch':owner['camera_epoch'],'frame_id':0,'captured_mono_ms':0}
    class Services:
        def read(self):
            return {'snapshot':dict(owner,source_kind='fixture',modules={'camera':{'state':'READY'},
                       'vision':{'state':'READY','people_count':0},'target':{'state':'NONE'}},
                       capabilities={},preview=dict(reference)),
                    'link':'READY','raw_preview':True,'preview':None,'results':[],'pending_count':0,
                    'error':'','connection':stage.connection_store.read()}
    services = stage.services = Services()
    stop = threading.Event()
    thread = None
    worker = None
    try:
        with tempfile.TemporaryDirectory(prefix='aura-video-test-') as directory:
            store = RawFrameStore(owner,directory)
            worker = stage.preview_output = CameraPreviewWorker(services,raw_directory=directory)
            preview.refresh()  # Poll before the initially hidden vision page realizes.
            stage.show_page('vision');preview.drain()
            def produce():
                frame = 0
                while not stop.wait(.03):
                    frame += 1
                    stamp = int(time.monotonic()*1000)
                    store.publish(frame,stamp,bytes([30,40,220])*(640*480))
                    reference.update(frame_id=frame,captured_mono_ms=stamp)
            thread = threading.Thread(target=produce)
            thread.start()
            def wait_visible():
                deadline = time.monotonic()+4
                while time.monotonic()<deadline:
                    preview.refresh();preview.drain()
                    if (worker.read('vision')['frame_visible'] and stage.preview_image.get_mapped()
                            and not stage.preview_placeholder.get_visible()):return
                raise AssertionError(worker.read('vision'))
            wait_visible()
            origin = stage.preview_image.get_window().get_origin()
            center = (origin[-2]+200,origin[-1]+150)
            capture(output/'vision.png')
            red = Image.open(output/'vision.png').getpixel(center)
            rect=stage.preview_image.get_allocation()
            assert red[0]>180 and red[1]<80 and red[2]<80,(red,(rect.x,rect.y,rect.width,rect.height),stage.preview_image.get_window().get_geometry(),origin,worker.read('vision'))
            before = worker.read('vision')['displayed_frames']
            time.sleep(.3)
            assert worker.read('vision')['displayed_frames']>before+3
            stage.show_page('main');preview.refresh();preview.drain()
            assert not stage.preview_image.get_mapped()
            capture(output/'main.png')
            main_pixel = Image.open(output/'main.png').getpixel(center)
            assert not (main_pixel[0]>180 and main_pixel[1]<80 and main_pixel[2]<80),main_pixel
            stage.show_page('vision');wait_visible()
            capture(output/'vision-return.png')
            returned = Image.open(output/'vision-return.png').getpixel(center)
            assert returned[0]>180 and returned[1]<80 and returned[2]<80,returned
            stop.set();thread.join();time.sleep(.4)
            preview.refresh();preview.drain()
            assert not worker.read('vision')['frame_visible']
            assert not stage.preview_image.get_mapped()
            result = {'status':'PASS','scope':'HOST_SYNTHETIC_GSTREAMER_NOT_BOARD_OR_CAMERA',
                      'video_size':[400,300],'native_pixel':red,'main_pixel':main_pixel,'returned_pixel':returned,
                      'checks':['independent_video_updates','hidden_on_main','returns_embedded_on_vision','stale_video_hidden']}
            (output/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(result))
            store.close()
    finally:
        stop.set()
        if thread:thread.join()
        if worker:worker.close()
        preview.close()


if __name__ == '__main__':main()
