import copy
import unittest
from firmware_trial_controller import verify_checkpoint


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.before={'primary_calls':100,'primary_period_overruns':1,'optional':{
            'yunet':{'calls':50,'overruns':2},'sface':{'calls':20,'overruns':1}},'sface_completed':18}
        self.doc={'schema':'aura-native-protection-checkpoint-2','scope':'final_quiescent_before_native_owner_close',
            'seed':{'boot_id':'test-boot','source_pid':123,'source_birth_ticks':456,'checkpoint_kind':1,
                'fenced':0,'primary_calls':101,'primary_period_overruns':1,'admissions':[101,51,20],
                'overruns':[0,2,1]},'auxiliary':{'fenced':False,'active':False,'primary_waiting':False,
                'pending_result_tokens':[0,0,0],'sface_counters':{'completed':18}}}
        self.kw={'boot':'test-boot','pid':123,'birth':456,'alive':False,'lock_free':True,
            'unit':{'MainPID':'0','ExecMainStatus':'0','Result':'success'}}

    def test_exact_quiescent_checkpoint_accepts(self):verify_checkpoint(self.doc,self.before,**self.kw)
    def test_retained_owner_refused(self):
        self.kw['alive']=True
        with self.assertRaises(RuntimeError):verify_checkpoint(self.doc,self.before,**self.kw)
    def test_pending_native_result_refused(self):
        self.doc['auxiliary']['pending_result_tokens'][1]=9
        with self.assertRaises(RuntimeError):verify_checkpoint(self.doc,self.before,**self.kw)
    def test_fault_history_decrease_refused(self):
        self.doc['seed']['overruns'][1]=0
        with self.assertRaises(RuntimeError):verify_checkpoint(self.doc,self.before,**self.kw)
    def test_wrong_process_birth_refused(self):
        self.doc['seed']['source_birth_ticks']=455
        with self.assertRaises(RuntimeError):verify_checkpoint(self.doc,self.before,**self.kw)
    def test_wrong_source_manifest_refused(self):
        self.doc['seed']['source_manifest_sha256']='old'
        with self.assertRaises(RuntimeError):verify_checkpoint(self.doc,self.before,manifest_sha='new',**self.kw)
    def test_wrong_source_unit_refused(self):
        self.doc['source_unit_sha256']='old'
        with self.assertRaises(RuntimeError):verify_checkpoint(self.doc,self.before,unit_sha='new',**self.kw)


if __name__=='__main__':unittest.main()
