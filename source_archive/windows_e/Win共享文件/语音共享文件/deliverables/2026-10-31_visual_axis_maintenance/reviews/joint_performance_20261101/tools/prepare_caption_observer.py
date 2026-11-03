"""Add only lifecycle scalars and empty-body flags to the reviewed correlation observer."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parents[1]

def main():
 before=(HERE/'remote/live_observer_correlated.py').read_text('utf-8')
 assert hashlib.sha256(before.encode()).hexdigest()=='3c7ecd9ef97e5b67964735e138f3113522b06ae51b3a6e659be2f0b2b0411589'
 tree=ast.parse(before);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE' for t in n.targets))
 original=node.value.value;assert isinstance(original,str)
 extra="""
caption_lifecycle=state.get('presentation_lifecycle',{})
if not isinstance(caption_lifecycle,dict):caption_lifecycle={}
caption={key:(caption_lifecycle.get(key) if type(caption_lifecycle.get(key)) is int else None)
         for key in ('epoch','invalidations','expirations')}
caption['showing']=caption_lifecycle.get('showing') if type(caption_lifecycle.get('showing')) is bool else None
def empty_body_flag(container,key):
 if not isinstance(container,dict) or key not in container:return None
 value=container[key]
 return value is None or value=='' if value is None or isinstance(value,str) else None
caption['api_reply_empty']=empty_body_flag(state,'reply')
caption['api_transcript_empty']=empty_body_flag(state.get('local_transcription'),'text')
observed['caption_metadata']=caption
"""
 lines=before.splitlines(True);old=''.join(lines[node.lineno-1:node.end_lineno]);new='SOURCE='+repr(original+extra)+'\n'
 assert before.count(old)==1;after=before.replace(old,new,1);ast.parse(after)
 dest=HERE/'remote/live_observer_caption.py'
 with dest.open('x',encoding='utf-8',newline='\n') as f:f.write(after)
 manifest=dict(schema='aura-caption-metadata-observer-1',base_sha256=hashlib.sha256(before.encode()).hexdigest(),source_sha256=hashlib.sha256(after.encode()).hexdigest(),
               added_fields=['showing','epoch','invalidations','expirations','api_reply_empty','api_transcript_empty'],
               field_types='bool/int/null only',caption_text_or_widget_text_or_screenshot_exported=False,
               interval_seconds=1,maximum_seconds=180,first_request_ack_correlation_unchanged=True,
               showing_after_pause_may_be_false_by_design=True,source_path=str(dest))
 path=HERE/'remote/live_observer_caption_manifest.json'
 with path.open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2);f.write('\n')
 print(json.dumps(manifest))

if __name__=='__main__':main()
