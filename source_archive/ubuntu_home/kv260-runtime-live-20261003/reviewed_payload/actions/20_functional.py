p=Path(CFG['agent_helpers'])
assert digest(p)==CFG['agent_helpers_sha256']
exec(compile(p.read_bytes(),str(p),'exec'))
begin_phase('20-official-functional')
query=dpu_query(OFFICIAL_APP,'official-query')
top5=classify(OFFICIAL_APP,'official-classification')
state=sample('official')
kernel_check('official-functional')
finish_phase({'query':query,'top5':top5,'sample':state})
