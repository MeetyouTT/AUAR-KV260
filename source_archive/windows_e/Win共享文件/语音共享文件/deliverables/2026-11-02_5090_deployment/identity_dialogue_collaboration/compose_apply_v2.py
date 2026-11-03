import ast,base64,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
payload=(HERE/'candidate/tools/unified_identity_binding.py').read_bytes()
assert hashlib.sha256(payload).hexdigest()=='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
template=HERE/'apply_identity_query_v2.template.py'
text=template.read_text(encoding='utf-8')
assert text.count('__CANDIDATE_BASE64__')==1
text=text.replace('__CANDIDATE_BASE64__',base64.b64encode(payload).decode('ascii'))
ast.parse(text)
output=HERE/'apply_identity_query_v2.py';assert not output.exists();output.write_text(text,encoding='utf-8',newline='')
result={'draft_path':str(output),'draft_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
    'template_sha256':hashlib.sha256(template.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(payload).hexdigest(),
    'startup_after_sha256':'0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f',
    'actual_board_execution':False,'default_action':'dry_run_requires_GUI_inactive',
    'explicit_apply_argument':'--apply-identity-query-v2'}
(HERE/'APPLY_DRAFT_V2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
