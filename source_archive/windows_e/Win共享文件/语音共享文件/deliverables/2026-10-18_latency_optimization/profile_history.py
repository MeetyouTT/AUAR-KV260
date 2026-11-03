"""Compare semantic-only and exact generated assistant history for cache reuse."""
import json
from pathlib import Path
from profile_llm import measure,MODEL

HERE=Path(__file__).resolve().parent
report={'model':MODEL,'actual_llm':True,'voice_synthesis':False,'cases':[]}
question='我叫小林，我喜欢蓝色。请记住。'
for index in range(2):
    for kind in ('plain_spoken_history','exact_json_history'):
        first=measure(question,variant='reply_first_keys')
        generated=json.loads(first['reply_json'])
        assistant=generated['a_reply_text'] if kind=='plain_spoken_history' else first['reply_json']
        history=[{'role':'user','content':question},{'role':'assistant','content':assistant}]
        second=measure('我叫什么名字，喜欢什么颜色？',variant='reply_first_keys',history=history)
        reply=json.loads(second['reply_json'])['a_reply_text']
        case={'round':index,'history_kind':kind,'first':first,'second':second,
              'name_and_color_correct':'小林' in reply and '蓝' in reply}
        report['cases'].append(case)
        (HERE/'history_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({key:value for key,value in case.items() if key!='first'},ensure_ascii=True),flush=True)
        if not case['name_and_color_correct']:raise SystemExit('Memory quality check failed')
