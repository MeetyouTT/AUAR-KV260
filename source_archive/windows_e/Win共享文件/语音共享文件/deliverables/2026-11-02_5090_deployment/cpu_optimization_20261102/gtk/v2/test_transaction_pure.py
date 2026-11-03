"""Small pure/template checks only. Never import/run the transaction main."""
import ast
import base64
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=(HERE/'transaction_preview_projection.py').read_text(encoding='utf-8')
TREE=ast.parse(SOURCE)
class FakePath(PurePosixPath):
    def resolve(self,*args,**kwargs):return self
SPACE={'copy':copy,'json':json,'Path':FakePath}
nodes=[node for node in TREE.body if isinstance(node,ast.ClassDef) and node.name=='Hold'
    or isinstance(node,ast.FunctionDef) and node.name in ('require','json_bytes','startup_after','selected_readback')
    or isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id in ('TARGETS','OLD','NEW') for target in node.targets)]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pure-transaction-functions>','exec'),SPACE)

def startup():
    pins={'component-'+str(i):('f'*64) for i in range(375)}
    pins.update(SPACE['OLD'])
    pins.update({'tools/unified_identity_binding.py':'a'*64,'common/board_timeline_clock.py':'b'*64,'config/pan_face.local.json':'c'*64})
    assert len(pins)==380
    return {'component_sha256':pins,'runtime':'/public/runtime','voice_marker':'a911-or-later','clock_policy':{'version':3},'unrelated':[1,2,3]}

class TemplateTests(unittest.TestCase):
    def test_startup_changes_only_two_components(self):
        before=startup();after=json.loads(SPACE['startup_after'](before,SPACE['NEW']))
        self.assertEqual(len(after['component_sha256']),380)
        for name,value in before['component_sha256'].items():
            self.assertEqual(after['component_sha256'][name],SPACE['NEW'].get(name,value))
        self.assertEqual(after['voice_marker'],before['voice_marker']);self.assertEqual(after['clock_policy'],before['clock_policy'])

    def test_rollback_preserves_later_voice_clock_and_pan_edits(self):
        current=json.loads(SPACE['startup_after'](startup(),SPACE['NEW']))
        current['component_sha256']['tools/unified_identity_binding.py']='1'*64
        current['component_sha256']['common/board_timeline_clock.py']='2'*64
        current['component_sha256']['config/pan_face.local.json']='3'*64
        current['clock_policy']={'version':99}
        after=json.loads(SPACE['startup_after'](current,SPACE['OLD']))
        expected=copy.deepcopy(current);expected['component_sha256'].update(SPACE['OLD'])
        self.assertEqual(after,expected)

    def test_selected_source_overlap_holds_before_source_reads(self):
        name='/public/aura/board/interaction/ui_services.py'
        ui={'board_business':{'face_readback':{'path':'/public/readback.json','sha256':'a'*64}}}
        binding={'source_sha256':{name:SPACE['OLD']['board/interaction/ui_services.py']}}
        calls=[]
        def pinned(path,digest):calls.append(str(path));return json.dumps(binding).encode(),(1,2,3)
        SPACE['read_file']=lambda path:(json.dumps(ui).encode(),(1,2,3));SPACE['pinned']=pinned
        with self.assertRaisesRegex(SPACE['Hold'],'HOLD_SELECTED_READBACK_PINS_MODIFIED_COMPONENT'):
            SPACE['selected_readback'](FakePath('/public/aura'),{}, {name:FakePath(name)})
        self.assertEqual(calls,['/public/readback.json'])

    def test_selected_startup_pin_also_holds(self):
        name='/public/startup/config.json'
        ui={'board_business':{'face_readback':{'path':'/public/readback.json','sha256':'a'*64}}}
        binding={'source_sha256':{name:'b'*64}}
        SPACE['read_file']=lambda path:(json.dumps(ui).encode(),(1,2,3))
        SPACE['pinned']=lambda path,digest:(json.dumps(binding).encode(),(1,2,3))
        with self.assertRaisesRegex(SPACE['Hold'],'HOLD_SELECTED_READBACK_PINS_MODIFIED_COMPONENT'):
            SPACE['selected_readback'](FakePath('/public/aura'),{}, {name:FakePath(name)})
        self.assertIn("[aura/name for name in TARGETS]+[context['startup_path']]",SOURCE)

    def test_actual_rollback_guard_rejects_any_unknown_bytes(self):
        function=next(node for node in TREE.body if isinstance(node,ast.FunctionDef) and node.name=='preflight')
        guard=next(node for node in ast.walk(function) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='require' and len(node.args)==2 and isinstance(node.args[1],ast.Constant) and node.args[1].value=='HOLD_ROLLBACK_UNKNOWN_TARGET')
        expression=compile(ast.Expression(guard.args[0]),'<actual-rollback-known-byte-guard>','eval')
        name=SPACE['TARGETS'][0];old=SPACE['OLD'][name];new=SPACE['NEW'][name];unknown='0'*64
        for actual in (old,new,unknown):
            for pin in (old,new,unknown):
                result=eval(expression,dict(SPACE,actual=actual,pins={name:pin},name=name))
                self.assertEqual(result,actual!=unknown and pin!=unknown)

    def test_default_dry_run_precedes_mutation_branch(self):
        function=next(node for node in TREE.body if isinstance(node,ast.FunctionDef) and node.name=='execute')
        guard=next(i for i,node in enumerate(function.body) if isinstance(node,ast.If) and ast.dump(node.test)==ast.dump(ast.UnaryOp(op=ast.Not(),operand=ast.Name(id='apply',ctx=ast.Load()))))
        self.assertIsInstance(function.body[guard].body[0],ast.Return)
        first_lock=next(i for i,node in enumerate(function.body) if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='descriptor' for t in node.targets))
        self.assertLess(guard,first_lock)
        self.assertIn("parser.add_argument('--apply',action='store_true')",SOURCE)

    def test_payload_has_exact_reviewed_old_new_bytes(self):
        payload=json.loads((HERE/'transaction_payload.json').read_bytes())
        self.assertEqual(set(payload['components']),set(SPACE['TARGETS']))
        for name,row in payload['components'].items():
            self.assertEqual(row['old_sha256'],SPACE['OLD'][name]);self.assertEqual(row['new_sha256'],SPACE['NEW'][name])
            data=base64.b64decode(row['new_bytes_base64'],validate=True)
            self.assertEqual(hashlib.sha256(data).hexdigest(),SPACE['NEW'][name])
            self.assertEqual(data,(HERE/'candidate'/name).read_bytes())

    def test_no_service_or_recursive_delete_execution_path(self):
        calls=[node for node in ast.walk(TREE) if isinstance(node,ast.Call)]
        commands=[node.args[0] for node in calls if isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='subprocess' and node.func.attr=='run']
        self.assertEqual(len(commands),1)
        self.assertEqual([item.value for item in commands[0].elts[:2]],['systemctl','show'])
        self.assertFalse(any(isinstance(node.func,ast.Attribute) and node.func.attr in ('unlink','rmtree','remove','system') for node in calls))

if __name__=='__main__':
    output=io.StringIO();result=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TemplateTests))
    (HERE/'TRANSACTION_PURE_CHECK.txt').write_text(output.getvalue(),encoding='utf-8')
    value={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),
        'transaction_main_imported_or_executed':False,'board_or_network_contacted':False,'deployment_files_mutated':False}
    (HERE/'TRANSACTION_PURE_CHECK.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value));raise SystemExit(0 if result.wasSuccessful() else 1)
