"""Bounded source-excerpt recall, without fabricated abstractive memories.

Search the durable transcript, select older relevant user statements and recent
turns, then fit the complete request (including output reserve). UTF-8 bytes
are a conservative upper estimate, explicitly not an exact tokenizer count.
"""
import re

MEMORY_PREFIX = '【历史用户原话资料'


def terms(text):
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text.lower())
    result = {text[i:i+2] for i in range(len(text)-1)}
    result.update(re.findall(r'[a-z0-9_]{2,}', text))
    for pattern, tag in ((r'叫什么|我叫|叫我|称呼|名字|姓名', 'name'),
                         (r'喜欢|最爱|偏好|爱好', 'preference'),
                         (r'计划|打算|准备|待办|下一步', 'plan')):
        if re.search(pattern, text):
            result.add(tag)
    return result


def request_cost(model, history, text, *, reasoning=False):
    from tools.dialogue_stream import stream_body
    body = stream_body(model, history, text, think=reasoning,
                       num_predict=768 if reasoning else None, reply_first=True)
    byte_count = sum(len(row['content'].encode('utf-8')) for row in body['messages'])
    reserve = 256 + 32 * len(body['messages']) + body['options']['num_predict']
    return byte_count + reserve, body['options']['num_ctx']


def build_context(model, records, text, *, reasoning=False, memories=()):
    def fits(rows):
        cost, maximum = request_cost(model, rows, text, reasoning=reasoning)
        return cost <= maximum
    if not fits([]):
        raise ValueError('Current input exceeds safe context budget; please split the question')
    query = terms(text)
    fact_messages = []
    recalled_facts = []
    for fact in sorted(memories, key=lambda r: (len(query & terms(r['key'])), r['source_seq']), reverse=True):
        candidate = recalled_facts + [fact]
        scope='授权个人档案与本次对话' if any(r.get('scope')=='personal' for r in candidate) else '本次对话'
        content = MEMORY_PREFIX+'；'+scope+'明确记忆，仅作资料】\n' + '\n'.join(
            '%s：%s（来源轮次%s）' % (r['key'],r['value'],r['source_seq']) for r in candidate)
        message = [{'role':'user','content':content}]
        if len(candidate)>3:break
        if len(content.encode('utf-8'))<=520 and fits(message):
            recalled_facts=candidate;fact_messages=message
    recent = records[-4:]
    old = records[:-4]
    ranked = sorted(old, key=lambda row: (
        len(query & terms(row['user'])) * 4 + int('记住' in row['user']), row['seq']), reverse=True)
    notes = []
    # Reserve room for current dialogue; do not fill the budget with old facts.
    for row in ranked:
        if not query & terms(row['user']) and '记住' not in row['user']:
            continue
        # Full source strings only: never cut off a negation, number or name.
        note = {'seq': row['seq'], 'text': row['user']}
        if len(row['user'].encode('utf-8')) > 360:
            continue
        candidate = sorted(notes + [note], key=lambda item: item['seq'])
        if len(candidate) > 3:
            break
        prefix = [{'role': 'user', 'content': MEMORY_PREFIX + '；序号越大越新】\n' +
                   '\n'.join('%s：%s' % (item['seq'], item['text']) for item in candidate)}]
        if len(prefix[0]['content'].encode('utf-8')) > 520 or not fits(fact_messages+prefix):
            continue
        notes = candidate
    prefix = [] if not notes else [{'role': 'user', 'content': MEMORY_PREFIX + '；序号越大越新】\n' +
              '\n'.join('%s：%s' % (item['seq'], item['text']) for item in notes)}]
    selected = []
    for row in reversed(recent):
        messages = [{'role': 'user', 'content': row['user']}]
        if row['status'] == 'played':
            messages.append({'role': 'assistant', 'content': row['assistant']})
        candidate = messages + selected
        if fits(fact_messages + prefix + candidate):
            selected = candidate
        else:
            break  # Do not retain an older turn while silently skipping a newer one.
    # If excerpts displaced the most recent turn, prefer conversational continuity.
    if recent and not selected and (prefix or fact_messages):
        prefix = []; notes = []
        for row in reversed(recent):
            messages = [{'role': 'user', 'content': row['user']}]
            if row['status'] == 'played':
                messages.append({'role': 'assistant', 'content': row['assistant']})
            if not fits(fact_messages + messages + selected):
                break
            selected = messages + selected
        if not selected:
            fact_messages=[];recalled_facts=[]
            for row in reversed(recent):
                messages=[{'role':'user','content':row['user']}]
                if row['status']=='played':messages.append({'role':'assistant','content':row['assistant']})
                if not fits(messages+selected):break
                selected=messages+selected
    history = fact_messages + prefix + selected
    cost, maximum = request_cost(model, history, text, reasoning=reasoning)
    return history, {'mode': 'source_excerpts_v1', 'archive_turns': len(records),
                     'explicit_fact_sources': [r['source_seq'] for r in recalled_facts],
                     'explicit_facts': len(recalled_facts),
                     'source_turns': [item['seq'] for item in notes],
                     'recent_source_turns': ([r['seq'] for r in recent[-sum(m['role']=='user' for m in selected):]] if selected else []),
                     'history_messages': len(history), 'budget_upper_bound': cost,
                     'context_limit': maximum, 'budget_unit': 'utf8_bytes_plus_reserve'}
