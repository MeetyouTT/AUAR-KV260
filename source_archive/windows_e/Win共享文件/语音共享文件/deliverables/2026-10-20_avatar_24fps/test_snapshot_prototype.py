import ast,importlib.util,threading,time,unittest
from collections import deque
from pathlib import Path
HERE=Path(__file__).resolve().parent

class SnapshotTests(unittest.TestCase):
 def test_reader_copies_without_holding_render_lock(self):
  spec=importlib.util.spec_from_file_location('snapshot_worker',HERE/'snapshot_prototype/board_avatar_worker.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  worker=module.AvatarRenderWorker.__new__(module.AvatarRenderWorker);worker.condition=threading.Condition(threading.Lock())
  class GuardedState(dict):
   def __deepcopy__(self,memo):
    self_assert=worker.condition.acquire(blocking=False)
    if not self_assert:raise AssertionError('Reader holds render lock during deep copy')
    worker.condition.release();return {'nested':{'values':list(self['nested']['values'])}}
  worker.packet={'state':GuardedState(nested={'values':[1,2]}),'sequence':3,'render_ms':12,'at':time.monotonic(),'timings_ms':{'core':10}}
  worker.waiting=deque();worker.active=None;worker.results=deque([{'ok':True}]);worker.profile={'core':{'p95':20}}
  got=worker.read();got['state']['nested']['values'].append(9);got['state']['avatar_renderer']['profile']['core']['p95']=99
  self.assertEqual(worker.packet['state']['nested']['values'],[1,2]);self.assertEqual(worker.profile['core']['p95'],20)
 def test_unchanged_text_does_not_invalidate_label(self):
  tree=ast.parse((HERE/'snapshot_prototype/board_avatar_gtk.py').read_text(encoding='utf-8'));helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='set_label_text');space={};exec(compile(ast.Module(body=[helper],type_ignores=[]),'label-helper','exec'),space)
  class Label:
   value='';calls=0
   def get_text(self):return self.value
   def set_text(self,value):self.value=value;self.calls+=1
  label=Label()
  for text in ('等待','等待','说话','说话','') :space['set_label_text'](label,text)
  self.assertEqual(label.calls,3);self.assertEqual(label.value,'')
  class Buffer(Label):
   def get_start_iter(self):return 0
   def get_end_iter(self):return len(self.value)
   def get_text(self,start,end,include_hidden):return self.value[start:end]
  buffer=Buffer();space['set_label_text'](buffer,'完整回答');space['set_label_text'](buffer,'完整回答')
  self.assertEqual(buffer.calls,1);self.assertEqual(buffer.value,'完整回答')

if __name__=='__main__':unittest.main()
