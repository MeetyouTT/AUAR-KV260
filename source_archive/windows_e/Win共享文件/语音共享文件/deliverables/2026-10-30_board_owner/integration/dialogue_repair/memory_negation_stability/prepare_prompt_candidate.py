"""Prepare one prompt-only candidate and exact public model probe inputs."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
BASE=REPAIR/'feature_trigger_collaboration/board_integration_v17/local_runtime_v17'
SOURCE=REPAIR/'memory_observation_candidate_r2/after/board/runtime/board_memory_policy.py'
BEFORE='410e5b3eaf7986be6baa68d148469eb33443654ed0db597004518877732533c5'
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()==BEFORE
text=raw.decode('utf8')
needle="                  '区分计划与完成、用户陈述与相机观察，未听完的助手内容不写成已听到。不补造细节。')"
replacement=("                  '区分计划与完成、用户陈述与相机观察，未听完的助手内容不写成已听到。不补造细节。'\n"
             "                  '保留各条否定陈述的主语、对象和原否定表达。疑问句仍记为询问，保留原疑问形式。')")
assert text.count(needle)==1
updated=text.replace(needle,replacement)
old_tree=ast.parse(text)
new_tree=ast.parse(updated)
old_class=next(node for node in old_tree.body if isinstance(node,ast.ClassDef) and node.name=='BoardSummaryClient')
new_class=next(node for node in new_tree.body if isinstance(node,ast.ClassDef) and node.name=='BoardSummaryClient')
changed=[old.name for old,new in zip(old_class.body,new_class.body)
         if isinstance(old,ast.FunctionDef) and ast.dump(old,include_attributes=False)!=ast.dump(new,include_attributes=False)]
assert changed==['_messages']
old_class.body=[node for node in old_class.body if not (isinstance(node,ast.FunctionDef) and node.name=='_messages')]
new_class.body=[node for node in new_class.body if not (isinstance(node,ast.FunctionDef) and node.name=='_messages')]
assert ast.dump(old_tree,include_attributes=False)==ast.dump(new_tree,include_attributes=False)
output=HERE/'prompt_candidate'
before=output/'before/board/runtime/board_memory_policy.py'
after=output/'after/board/runtime/board_memory_policy.py'
before.parent.mkdir(parents=True,exist_ok=True)
after.parent.mkdir(parents=True,exist_ok=True)
before.write_bytes(raw)
after.write_bytes(updated.encode('utf8'))
sys.path.insert(0,str(BASE))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module
current=load('board.runtime.public_summary_prompt_before',before)
candidate=load('board.runtime.public_summary_prompt_after',after)
cases=[
    ('question_will',[dict(source='user_said',text='你会不会唱歌？',protected={})],
     '保持提问，明确记作询问会不会唱歌，不能写成已确定会唱或不会唱。'),
    ('question_can',[dict(source='user_said',text='你能不能识别声纹？',protected={})],
     '保持提问，明确记作询问能不能识别声纹，不能写成识别能力已确认。'),
    ('negative_capability',[dict(source='user_said',text='声纹尚未校准，不能可靠确认身份。',protected={'negated':True})],
     '同时保留尚未校准和不能可靠确认身份，两项均不能变成已完成或可可靠确认。'),
    ('contrasting_subjects',[dict(source='user_said',text='小林没有喝咖啡，小王已经喝了咖啡。',protected={'names':['小林','小王']})],
     '小林未喝与小王已喝应分别保留，不能调换主语或让无关否定词掩盖极性变化。'),
    ('question_identity',[dict(source='user_said',text='你是不是雪妃？',protected={'names':['雪妃']})],
     '保留询问是不是雪妃，不能把问题写成身份已确认。'),
    ('cancelled_plan',[dict(source='user_said',text='小林原计划下午3点买42个杯子，后来取消了，尚未购买。',
                     protected={'names':['小林'],'numbers':[3,42],'negated':True,'status':'cancelled'})],
     '保留小林、3点、42个杯子、原计划后来取消及尚未购买，不能写成完成采购。'),
]
rows=[]
for name,sources,rubric in cases:
    old=current.BoardSummaryClient(None,board_boot_id='public-negation-probe')
    new=candidate.BoardSummaryClient(None,board_boot_id='public-negation-probe')
    old_messages=old._messages(sources)
    new_messages=new._messages(sources)
    old_cost=current.message_cost(old_messages,old.reserve)
    new_cost=candidate.message_cost(new_messages,new.reserve)
    assert old_cost<=2048 and new_cost<=2048
    rows.append(dict(case=name,sources=sources,semantic_review_rubric=rubric,
        before_messages=old_messages,candidate_messages=new_messages,
        before_estimated_context_cost=old_cost,candidate_estimated_context_cost=new_cost))
manifest=dict(status='PROMPT_ONLY_LOCAL_CANDIDATE_REAL_MODEL_COMPARISON_PENDING',
    product_sources=1,source='board/runtime/board_memory_policy.py',
    before_sha256=BEFORE,after_sha256=hashlib.sha256(after.read_bytes()).hexdigest(),
    local_source=str(after),changed_methods=changed,other_ast_identical=True,
    validator_or_commit_logic_changed=False,context_limit=2048,output_reserve=384,
    source_refs_claims_or_provenance_logic_changed=False,production_modified=False)
(output/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
probes=dict(schema='aura.public-negation-prompt-comparison.v1',
    public_cases_only=True,model_requests_executed=False,options={'num_predict':384},
    task='summary',budget_ms=30000,context_limit=2048,
    execution_owner='root coordinates the existing admitted model and foreground turn boundary',
    adoption_requires='Complete valid JSON, current protected-field validator, and manual semantic rubric for every public case',
    candidate_source_sha256=manifest['after_sha256'],cases=rows)
(HERE/'PUBLIC_MODEL_PROBE_INPUTS.json').write_text(json.dumps(probes,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(manifest))
