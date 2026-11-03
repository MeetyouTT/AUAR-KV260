import ast
import copy
import io
import json
from pathlib import Path
import threading
import unittest
from projection_support import *

HERE=Path(__file__).resolve().parent

class ProjectionTests(unittest.TestCase):
    def assert_same(self,obj):self.assertEqual(*pair(obj))

    def test_original_service_apis_and_gst_graph_unchanged(self):
        def methods(source,name):
            cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name==name)
            return {node.name:ast.dump(node) for node in cls.body if isinstance(node,ast.FunctionDef)}
        before=methods(SOURCES['original_services'],'UiServiceClient');after=methods(SOURCES['candidate_services'],'UiServiceClient')
        self.assertEqual(set(after)-set(before),{'read_preview'})
        for key in before:self.assertEqual(before[key],after[key],key)
        before=methods(SOURCES['original_preview'],'CameraPreviewWorker');after=methods(SOURCES['candidate_preview'],'CameraPreviewWorker')
        for key in before:
            if key!='work':self.assertEqual(before[key],after[key],key)
        self.assertIn('videoconvert ! videoscale ! video/x-raw,width=',SOURCES['candidate_preview'])
        self.assertNotIn('videoscale ! videoconvert',SOURCES['candidate_preview'])

    def test_ready_raw_jpeg_remote_fixture_and_opt_out(self):
        for filled in (False,True):
            for host,raw,kind in (('127.0.0.1',True,'actual'),('127.0.0.1',False,'actual'),('192.0.2.1',True,'actual'),('127.0.0.1',True,'fixture')):
                with self.subTest(filled=filled,host=host,raw=raw,kind=kind):
                    obj,_=client(filled=filled);obj.connection['host']=host;obj.local_raw=raw
                    obj.gate.value['source_kind']=kind;self.assert_same(obj)

    def test_source_expiry_exact_boundary_and_no_preview(self):
        for now in (9999,10000,12499,12500,12501):
            obj,clock=client();clock.value=now;self.assert_same(obj)
            self.assertEqual(obj.read_preview()['snapshot'] is None,now>=12500)
        obj,_=client();obj.gate.value.pop('preview');obj.preview=obj.preview_key=None;self.assert_same(obj)

    def test_link_states_camera_loss_and_missing_camera(self):
        for link in ('DISABLED','CONNECTING','OFFLINE','STALE','READY'):
            obj,_=client();obj.link=link;self.assert_same(obj)
        for state in ('LOST','ERROR','UNKNOWN','READY'):
            obj,_=client();obj.gate.value['modules']['camera']['state']=state;self.assert_same(obj)
        obj,_=client();obj.gate.value['modules'].pop('camera');self.assert_same(obj)

    def test_jpeg_cache_reference_and_1500ms_boundary(self):
        for age in (1499,1500,1501):
            obj,clock=client();stamp=clock.value-age
            obj.gate.value['preview']['captured_mono_ms']=stamp;obj.preview_key=copy.deepcopy(obj.gate.value['preview'])
            self.assert_same(obj);self.assertEqual(obj.read_preview()['preview'] is None,age>1500)
        for key in ('camera_epoch','frame_id','captured_mono_ms'):
            obj,_=client();obj.preview_key[key]='mismatch';self.assert_same(obj);self.assertIsNone(obj.read_preview()['preview'])

    def test_cancel_and_identity_preview_do_not_change_camera_decision(self):
        obj,_=client();obj.gate.cancel();self.assert_same(obj)
        self.assertEqual(obj.read()['snapshot']['modules']['interaction']['state'],'CANCELLED')
        obj.gate.value['modules']['identity']['face_preview']={'target':obj.gate.value['modules']['target']['selected'],'frame_id':1,'captured_mono_ms':10000,'ttl_ms':500}
        obj.identity_preview_enabled=True;obj.identity_face=b'PUBLIC-PNG';obj.identity_face_key=copy.deepcopy(obj.gate.value['modules']['identity']['face_preview'])
        self.assert_same(obj)

    def test_projection_contains_no_mutable_internal_reference(self):
        obj,_=client();obj.preview=bytearray(b'PUBLIC-JPEG')
        value=obj.read_preview();value['snapshot']['preview']['frame_id']=999
        value['snapshot']['modules']['camera']['state']='ERROR';value['preview'][0]=0
        self.assertEqual(obj.gate.value['preview']['frame_id'],1)
        self.assertEqual(obj.gate.value['modules']['camera']['state'],'READY')
        self.assertEqual(obj.preview[0],ord('P'))

    def test_configure_replaces_gate_and_invalidates_source(self):
        obj,_=client();obj.configure({'enabled':False,'host':'127.0.0.1','port':8790})
        self.assert_same(obj);self.assertIsNone(obj.read_preview()['snapshot'])
        self.assertEqual(obj.ui_generation,1);self.assertEqual(obj.config_generation,1)

    def test_actual_worker_raw_and_loss_decisions_equal(self):
        for mode in ('ready','cancelled','expired','lost','missing-preview'):
            outputs=[]
            for version in ('original','candidate'):
                obj,clock=client(version)
                if mode=='cancelled':obj.gate.cancel()
                elif mode=='expired':clock.value=12500
                elif mode=='lost':obj.gate.value['modules']['camera']['state']='LOST'
                elif mode=='missing-preview':obj.gate.value.pop('preview');obj.preview=obj.preview_key=None
                outputs.append(worker_trace(version,obj,clock))
            with self.subTest(mode=mode):self.assertEqual(outputs[0],outputs[1]);self.assertEqual(outputs[0]['error'],'')

    def test_legacy_read_only_service_uses_compatibility_fallback(self):
        obj,clock=client('original')
        # The candidate worker sees an old service object with only read().
        result=worker_trace('candidate',obj,clock)
        self.assertEqual(result['error'],'');self.assertTrue(any(row[0]=='push' for row in result['trace']))

    def test_concurrent_configure_loss_cancel_has_coherent_owner_and_jpeg(self):
        obj,clock=client();errors=[];start=threading.Barrier(2)
        def writer():
            try:
                start.wait()
                for index in range(350):
                    obj.configure({'enabled':True,'host':'127.0.0.1','port':8790})
                    value=snapshot(epoch='service-'+str(index%2+1),frame=index+1)
                    populate(obj,value)
                    with obj.condition:
                        if index%3==0:obj.gate.cancel()
                        if index%7==0:obj.link='OFFLINE'
            except BaseException as exc:errors.append(type(exc).__name__)
        thread=threading.Thread(target=writer);thread.start();start.wait()
        reads=0
        while thread.is_alive() or reads<500:
            view=obj.read_preview();value=view['snapshot'];reads+=1
            if value is not None:
                self.assertEqual(value['preview']['camera_epoch'],'camera-'+value['service_epoch'])
                if view['preview'] is not None:self.assertEqual(view['preview'],b'PUBLIC-JPEG-'+str(value['preview']['frame_id']).encode())
                value['modules']['camera']['state']='MUTATED-RETURN-ONLY'
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive());self.assertFalse(errors)
        self.assertNotEqual(obj.gate.value['modules']['camera']['state'],'MUTATED-RETURN-ONLY')

if __name__=='__main__':
    log=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(ProjectionTests)
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (HERE/'UNIT_TEST_RESULTS.txt').write_text(log.getvalue(),encoding='utf-8')
    report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),
        'source':'Pinned source; synthetic snapshots only','devices_services_models_or_database_opened':False,'production_changed':False}
    (HERE/'UNIT_TEST_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));raise SystemExit(0 if result.wasSuccessful() else 1)
