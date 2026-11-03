"""Exercise the actual finite-trial entry using an independent-clock fake PL."""
import contextlib,importlib.util,io,json,signal,sys,tempfile,types,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path[:0]=[str(R/'controller'),str(R/'candidate/runtime/aura')]
from test_hardware_slew import FrameSlewDevice
from board.motion.vsrv_driver import PhysicalReference

class TrialTests(unittest.TestCase):
    def execute(self,fault=None):
        spec=importlib.util.spec_from_file_location('trial',R/'rated_range_trial.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        class Clock:
            now=100.;sleeps=0
            def monotonic(self):self.now+=.000001;return self.now
            def sleep(self,seconds):
                self.sleeps+=1;self.now+=seconds
                if self.sleeps==8 and fault=='gap':self.now+=.2
                if self.sleeps==8 and fault=='cancel':handlers[signal.SIGTERM]()
        clock=Clock();device=FrameSlewDevice(clock.monotonic,1460,500,2500)
        class Registers:
            def __init__(self,*a):pass
            def __enter__(self):return self
            def __exit__(self,*a):device.stop()
        handlers={};m.time=clock;m.signal=types.SimpleNamespace(SIGTERM=signal.SIGTERM,SIGINT=signal.SIGINT,signal=lambda sig,fn:handlers.update({sig:fn}))
        saved={n:sys.modules.get(n) for n in ['bench_identity_stop','vsrv_driver','batch_transport','batch_driver']};argv=sys.argv[:]
        try:
            with tempfile.TemporaryDirectory() as td:
                p=Path(td);(p/'manifest.json').write_text('{}');(p/'context.json').write_text('{}')
                (p/'auth.json').write_text(json.dumps({'boot_id':'fixture','bounds_us':[500,2500],'clearance_confirmed':True,'requested_angles_deg':[-90,90]}))
                (p/'reference.json').write_text(json.dumps({'boot_id':'fixture','stopped_readback':device.status()}))
                sys.modules['bench_identity_stop']=types.SimpleNamespace(validated_context=lambda a:(p,{'payload_files':{'libvsrv.so':'fixture'},'runtime_files':{}},'fixture'))
                sys.modules['vsrv_driver']=types.SimpleNamespace(PhysicalReference=PhysicalReference)
                sys.modules['batch_transport']=types.SimpleNamespace(BatchRegisters=Registers)
                sys.modules['batch_driver']=types.SimpleNamespace(BatchDriver=lambda *a:device)
                sys.argv=['trial','--manifest',str(p/'manifest.json'),'--context',str(p/'context.json'),'--reference',str(p/'reference.json'),'--authorization',str(p/'auth.json'),'--controller',str(p),'--output',str(p/'result.json'),'--manifest-sha256','fixture','--confirmation','ATTENDED_RATED_180']
                with contextlib.redirect_stdout(io.StringIO()):
                    if fault:
                        with self.assertRaises((RuntimeError,AssertionError)):m.main()
                    else:m.main()
                result=json.loads((p/'result.json').read_text())
                self.assertTrue(result['stop_confirmed']);self.assertFalse(device.active)
                self.assertTrue(all(500<=c['target']<=2500 for c in device.commands))
                self.assertTrue(all(abs(f['width']-f['before'])<=4 for f in device.frames))
                return result,device
        finally:
            sys.argv=argv
            for n,v in saved.items():
                if v is None:sys.modules.pop(n,None)
                else:sys.modules[n]=v

    def test_full_sequence_returns_center_and_stops(self):
        result,device=self.execute()
        self.assertEqual(result['status'],'NOMINAL_ENDPOINT_COMMANDS_COMPLETED_PENDING_HUMAN')
        self.assertEqual([p['target_us'] for p in result['phases']],[1500,500,1500,2500,1500])
        self.assertEqual(device.pulse,1500)
        self.assertLess(result['elapsed_s'],35)
        self.assertTrue(all('arrived_mono_s' in p for p in result['phases']))

    def test_cpu_gap_does_not_resume_expired_motion(self):
        result,_=self.execute('gap');self.assertIsNotNone(result['error'])

    def test_operator_cancel_stops_before_full_sweep(self):
        result,_=self.execute('cancel');self.assertLess(len(result['phases']),5)

if __name__=='__main__':unittest.main()
