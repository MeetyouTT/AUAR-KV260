import copy,json
from pathlib import Path
import unittest
from cold_policy import validate_checkpoint


class ColdPolicy(unittest.TestCase):
    def setUp(self):
        doc=json.loads(Path('/home/ghmd/aura-native-live-20261024/r3/stop-checkpoint-result.json').read_text())['checkpoint']
        self.document=doc;seed=doc['seed']
        self.before=dict(primary_calls=seed['primary_calls'],primary_period_overruns=seed['primary_period_overruns'],
            optional={k:dict(calls=seed['admissions'][i],overruns=seed['overruns'][i]) for i,k in [(1,'yunet'),(2,'sface')]},
            sface_completed=doc['auxiliary']['sface_counters']['completed'])
        self.kw=dict(current_boot=seed['boot_id'],source_pid=seed['source_pid'],source_birth_ticks=seed['source_birth_ticks'],
            source_process_alive=False,lock_free=True,unit={'MainPID':'0','ExecMainStatus':'0','Result':'success'})
    def test_exact_completed_shutdown_allows_physical_step(self):
        self.assertTrue(validate_checkpoint(self.document,self.before,**self.kw))
    def test_live_or_locked_owner_blocks_poweroff(self):
        for key,value in [('source_process_alive',True),('lock_free',False)]:
            with self.assertRaises(ValueError):validate_checkpoint(self.document,self.before,**dict(self.kw,**{key:value}))
    def test_wrong_epoch_or_source_blocks_poweroff(self):
        with self.assertRaises(ValueError):validate_checkpoint(self.document,self.before,**dict(self.kw,source_pid=99))
        with self.assertRaises(ValueError):validate_checkpoint(self.document,self.before,**dict(self.kw,current_boot='other'))
    def test_unknown_and_pending_completion_blocks_poweroff(self):
        doc=copy.deepcopy(self.document);doc['seed']['fenced']=1
        with self.assertRaises(ValueError):validate_checkpoint(doc,self.before,**self.kw)
        doc=copy.deepcopy(self.document);doc['auxiliary']['pending_result_tokens'][1]=123
        with self.assertRaises(ValueError):validate_checkpoint(doc,self.before,**self.kw)
    def test_nonzero_service_exit_blocks_poweroff(self):
        with self.assertRaises(ValueError):validate_checkpoint(self.document,self.before,**dict(self.kw,unit={'MainPID':'0','Result':'exit-code','ExecMainStatus':'1'}))
    def test_counter_loss_blocks_poweroff(self):
        before=copy.deepcopy(self.before);before['primary_calls']+=1
        with self.assertRaises(ValueError):validate_checkpoint(self.document,before,**self.kw)
        before=copy.deepcopy(self.before);before['sface_completed']+=1
        with self.assertRaises(ValueError):validate_checkpoint(self.document,before,**self.kw)

if __name__=='__main__':unittest.main()
