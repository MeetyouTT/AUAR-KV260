"""Face-only ownership, actual HTTP crop isolation and explicit enrollment."""
import copy
import json
import struct
import threading
import urllib.error
import urllib.parse
import urllib.request
import unittest
import zlib
from http.server import ThreadingHTTPServer
from board.identity.face_targets import FaceTargetService
from board.identity.voice_enrollment import VoiceEnrollment
from board.interaction.ui_contract import validate_snapshot
from board.vision.ui_camera_service import handler_for
from tests.framework import test_camera_identity as fixtures
from tests.framework import test_board_ui_services as clients


def png(width=112,height=112):
    def chunk(tag,data):return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+chunk(
        b'IDAT',zlib.compress((b'\0'+b'\x80\x90\xa0'*width)*height))+chunk(b'IEND',b'')


class Detector:
    def __init__(self,faces):self.faces=faces
    def detect(self,_):return self.faces


FACE=[20.,20.,70.,80.,35.,40.,65.,40.,50.,58.,38.,78.,62.,78.,.99]


class FaceOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.LiveIdentityTests('test_no_auto_enrollment_or_photos_written')
        self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.targets=FaceTargetService(lambda:None,self.case.service.offer_face,self.case.state.camera_epoch,
            lock=self.case.state.lock,clock=lambda:self.case.now)
        self.targets.ready=True;self.case.service.face_targets=self.targets
        self.fid=1
        self.detect([FACE]);self.detect([FACE])

    def detect(self,faces):
        self.case.now+=200;self.fid+=1;self.case.state.captured(self.case.now)
        self.case.state.observed(self.fid,self.case.now,{'target_id':None,'tracks':[]},1.)
        self.targets.process((None,self.fid,self.case.now),Detector(faces))

    def infer(self):
        packet,self.case.service.pending=self.case.service.pending,None
        extractor=fixtures.Extractor();extractor.preview_png=png()
        self.case.service.process(packet,extractor)

    def test_face_can_be_enrolled_without_any_body_detection_or_selection(self):
        self.infer();state=validate_snapshot(self.case.state.snapshot(),'boot',self.case.now)
        self.assertIsNone(state['modules']['target']['selected'])
        self.assertEqual(state['modules']['vision']['people_count'],0)
        self.assertEqual(state['modules']['identity']['face_count'],1)
        self.assertTrue(state['capabilities']['identity_enroll'])
        self.assertTrue(self.case.state.command(self.case.enrollment())['accepted'])
        self.assertEqual(self.case.store.revision,1)

    def test_body_detector_failure_does_not_change_face_owner(self):
        key=self.case.state.identity_target();self.case.state.detector_error='body DPU unavailable'
        self.assertEqual(self.case.state.identity_target(),key)

    def test_face_absence_immediately_hides_preview_and_invalidates_old_work(self):
        self.infer();key=self.case.state.identity_target();fid=self.case.service.result['fid']
        self.assertEqual(self.case.service.face_preview(key,fid),png())
        self.detect([])
        self.assertIsNone(self.case.state.identity_target())
        self.assertIsNone(self.case.service.face_preview(key,fid))
        self.assertFalse(self.case.state.snapshot()['capabilities']['identity_enroll'])

    def test_multiple_faces_do_not_choose_largest_or_previous_person(self):
        second=list(FACE);second[0]+=200
        self.detect([FACE,second]);self.detect([FACE,second])
        state=self.case.state.snapshot()['modules']['identity']
        self.assertEqual(state['face_count'],2);self.assertIsNone(state['face_target'])
        self.assertFalse(self.case.state.snapshot()['capabilities']['identity_enroll'])

    def test_ambiguity_then_single_face_creates_a_new_binding_generation(self):
        old=self.case.state.identity_target();second=list(FACE);second[0]+=200
        self.detect([FACE,second]);self.detect([FACE])
        new=self.case.state.identity_target();self.assertEqual(old['track_id'],new['track_id'])
        self.assertNotEqual(old['track_generation'],new['track_generation'])

    def test_camera_freeze_hides_face_even_if_last_detection_was_good(self):
        self.infer();self.case.now+=1000
        self.assertIsNone(self.case.state.identity_target())
        self.assertNotIn('face_preview',self.case.state.snapshot()['modules']['identity'])

    def test_preview_is_face_only_and_rejects_wrong_track_frame_and_revision(self):
        self.infer();result=self.case.service.result;key=copy.deepcopy(result['target']);fid=result['fid']
        self.assertEqual(self.case.service.face_preview(key,fid),png())
        self.assertIsNone(self.case.service.face_preview(dict(key,track_generation=99),fid))
        self.assertIsNone(self.case.service.face_preview(key,fid+1))
        self.case.store.enroll('other','other',(0,1,0,0),consent=True)
        self.assertIsNone(self.case.service.face_preview(key,fid))

    def test_voice_enrollment_uses_face_ownership_without_body_target(self):
        self.infer()
        flow=VoiceEnrollment('boot',self.case.state.snapshot,self.case.state.command,
            clock=lambda:self.case.now/1000,now_ms=lambda:self.case.now)
        handle=lambda text:flow.handle(text,self.case.state.snapshot())
        self.assertEqual(handle('帮我登记身份')['code'],'ask_name')
        self.assertEqual(handle('我叫小林')['code'],'confirm_name')
        self.assertEqual(handle('确认登记')['code'],'registered')
        self.assertEqual(self.case.store.revision,1)

    def test_face_http_returns_exact_crop_and_refuses_expired_owner(self):
        self.infer();state=self.case.state;result=self.case.service.result
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(state))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        query=dict(result['target'],frame_id=result['fid'])
        url='http://127.0.0.1:'+str(server.server_port)+'/v1/ui/identity-face.png?'+urllib.parse.urlencode(query)
        with urllib.request.urlopen(url,timeout=2) as response:
            self.assertEqual(response.headers['Content-Type'],'image/png');self.assertEqual(response.read(),png())
        self.detect([])
        with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(url,timeout=2)
        self.assertEqual(caught.exception.code,404)


class FacePreviewClientTests(unittest.TestCase):
    client=clients.ClientTests.client
    class Transport(clients.FakeTransport):
        def __init__(self):super().__init__();self.face_calls=0;self.raw=png();self.include=True
        def json(self,*args):
            value=super().json(*args)
            if self.include:value['modules']['identity']['face_preview']={'target':value['modules']['target']['selected'],
                'frame_id':1,'captured_mono_ms':10000,'ttl_ms':3000}
            return value
        def request(self,base,path,limit):
            self.face_calls+=1
            return {'Content-Type':'image/png','X-Aura-Boot-Id':'boot-1','X-Aura-Service-Epoch':'service-1',
                'X-Aura-Camera-Epoch':'camera-1','X-Aura-Frame-Id':'1'},self.raw

    def test_face_fetch_is_opt_in_and_cleared_when_closed(self):
        transport=self.Transport();client=self.client(transport)
        self.assertEqual(transport.face_calls,0);client.set_identity_preview(True)
        clients.wait_for(lambda:client.read()['identity_face']==png())
        client.set_identity_preview(False);self.assertIsNone(client.read()['identity_face'])

    def test_whole_frame_dimensions_are_rejected(self):
        transport=self.Transport();transport.raw=png(640,480);client=self.client(transport)
        client.set_identity_preview(True);clients.wait_for(lambda:bool(client.read()['identity_face_error']))
        self.assertIsNone(client.read()['identity_face'])

    def test_missing_face_reference_clears_old_image(self):
        transport=self.Transport();client=self.client(transport);client.set_identity_preview(True)
        clients.wait_for(lambda:bool(client.read()['identity_face']))
        transport.include=False;client.refresh();clients.wait_for(lambda:client.read()['identity_face'] is None)


if __name__=='__main__':unittest.main()
