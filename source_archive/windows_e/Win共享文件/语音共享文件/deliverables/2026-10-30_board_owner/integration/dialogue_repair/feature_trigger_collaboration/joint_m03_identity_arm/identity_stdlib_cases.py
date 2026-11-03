"""Run frozen public test bodies using only stdlib unittest fixtures.

No module-level code from the pytest files runs. One fixture resource path in
Harness.__init__ is replaced by the already verified runtime root. Test bodies
and assertions are compiled unchanged, including the independent owner cases.
"""
import ast
import copy
from contextlib import contextmanager
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch


def build_suite(args, public):
    from common.identity_links import validate_resolution
    from common.voice_enrollment import identity_query_requested
    from tools.provisional_voice import query_reply
    from board.runtime.board_business import BoardBusinessConfig, create_board_business_runtime
    from board.runtime.board_speaker_business import BoardSpeakerBusiness
    from common.conversation_selection import ConversationSelection
    from tools.yuki_business_candidate import bind_runtime_pair
    from tools.enrollment_receipts import existing_face_payload

    def parametrize(names, values):
        keys = tuple(s.strip() for s in names.split(','))
        def decorate(function):
            combinations = []
            for value in values:
                row = value if len(keys)>1 else (value,)
                if len(keys)!=len(row):
                    raise ValueError('Public parameter shape changed')
                combinations.append(dict(zip(keys,row)))
            function.public_parameters = getattr(function,'public_parameters',[]) + [combinations]
            return function
        return decorate

    pytest_adapter = NS(mark=NS(parametrize=parametrize))
    namespace = dict(ast=ast,copy=copy,contextmanager=contextmanager,hashlib=hashlib,json=json,
        Path=Path,sqlite3=sqlite3,threading=threading,time=time,NS=NS,patch=patch,pytest=pytest_adapter,
        public=public,RUNTIME_ROOT=args.runtime_root.resolve(),validate_resolution=validate_resolution,
        identity_query_requested=identity_query_requested,query_reply=query_reply,
        BoardBusinessConfig=BoardBusinessConfig,create_board_business_runtime=create_board_business_runtime,
        BoardSpeakerBusiness=BoardSpeakerBusiness,ConversationSelection=ConversationSelection,
        bind_runtime_pair=bind_runtime_pair,existing_face_payload=existing_face_payload)

    speaker = ast.parse(args.speaker_fixtures.read_bytes())
    needed = {'Encoder','quality','capture','call','count_people','visual','packet','route',
              'ExistingFaceBridge','bind_existing_face_and_voice'}
    nodes = [node for node in speaker.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in needed
        or isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'MODEL','BOOT','CID'} for t in node.targets)]
    if {n.name for n in nodes if hasattr(n,'name')} != needed:
        raise ValueError('Original public speaker fixture shape changed')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(args.speaker_fixtures),'exec'),namespace)
    face = ast.parse(args.face_fixtures.read_bytes())
    snapshots = [n for n in face.body if isinstance(n,ast.FunctionDef) and n.name=='snapshot']
    if len(snapshots)!=1:
        raise ValueError('Original public face fixture changed')
    exec(compile(ast.Module(body=snapshots,type_ignores=[]),str(args.face_fixtures),'exec'),namespace)
    namespace['basic_snapshot'] = namespace.pop('snapshot')

    own = ast.parse(args.identity_tests.read_bytes())
    nodes = [n for n in own.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))
             and (n.name in {'conflict','Scene','Harness'} or n.name.startswith('test_'))]
    original_tests = {n.name:ast.dump(n) for n in nodes if n.name.startswith('test_')}
    class ResourcePath(ast.NodeTransformer):
        changes = 0
        def visit_BinOp(self,node):
            if (isinstance(node.op,ast.Div) and isinstance(node.left,ast.Name) and node.left.id=='H'
                    and isinstance(node.right,ast.Constant)
                    and node.right.value=='candidate_m03_v90_stage/public_runtime_v90'):
                self.changes += 1
                return ast.copy_location(ast.Name(id='RUNTIME_ROOT',ctx=ast.Load()),node)
            return self.generic_visit(node)
    resources = ResourcePath()
    body = ast.Module(body=nodes,type_ignores=[])
    body = ast.fix_missing_locations(resources.visit(body))
    if resources.changes!=1 or any(ast.dump(n)!=original_tests[n.name] for n in body.body if n.name.startswith('test_')):
        raise ValueError('Only the public fixture resource path may be adapted')
    exec(compile(body,str(args.identity_tests),'exec'),namespace)
    own_names = list(original_tests)

    independent = ast.parse(args.identity_independent.read_bytes())
    independent_nodes = [n for n in independent.body if isinstance(n,ast.FunctionDef)
                         and (n.name=='derived_state' or n.name.startswith('test_'))]
    independent_names = [n.name for n in independent_nodes if n.name.startswith('test_')]
    exec(compile(ast.Module(body=independent_nodes,type_ignores=[]),str(args.identity_independent),'exec'),namespace)
    suite = unittest.TestSuite()
    counts = {}
    class PublicCases(unittest.TestCase):
        pass
    for group,names,expected in (('identity',own_names,47),('independent',independent_names,12)):
        count = 0
        for name in names:
            function = namespace[name]
            parameters = getattr(function,'public_parameters',[])
            combinations = itertools.product(*parameters) if parameters else [()]
            for i,parts in enumerate(combinations):
                values = {}
                for part in parts:
                    if set(values)&set(part):
                        raise ValueError('Duplicate public parameter')
                    values.update(part)
                def run(self,function=function,values=values):
                    def raises(exception,match=None):
                        return self.assertRaises(exception) if match is None else self.assertRaisesRegex(exception,match)
                    namespace['pytest'].raises = raises
                    with tempfile.TemporaryDirectory(prefix='identity-public-case-') as directory:
                        kwargs = dict(values)
                        if 'tmp_path' in function.__code__.co_varnames[:function.__code__.co_argcount]:
                            kwargs['tmp_path'] = Path(directory)
                        function(**kwargs)
                method = 'test_'+group+'_'+name.removeprefix('test_')+'_'+str(i)
                setattr(PublicCases,method,run)
                suite.addTest(PublicCases(method))
                count += 1
        if count != expected:
            raise ValueError('Public adapted case count changed: '+group)
        counts[group] = count
    return suite,dict(test_bodies_and_assertions_AST_unchanged=True,
        fixture_resource_paths_adapted=resources.changes,pytest_module_imported=False,counts=counts,
        adapters='tmp_path via TemporaryDirectory; mark.parametrize via Cartesian expansion; raises via assertRaises/Regex')
