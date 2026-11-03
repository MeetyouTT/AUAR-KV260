"""Read-only SQL COUNT diagnostics; vectors remain board-local SQL arguments."""
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time

root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()=='44e8f154c9dd72d3b7619160f7a2dac64fda529daba91a96a196c12f68c8a295'
private=Path('/home/root/.local/share/aura-board-business/speaker')
for name in ('speakers.sqlite3','anonymous-voices.sqlite3'):
    p=private/name
    assert p.is_file() and not p.is_symlink() and p.resolve()==p
db=sqlite3.connect((private/'speakers.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=1,isolation_level=None)
def vector(raw):
    try:
        x=json.loads(raw)
        if type(x) is not list or len(x)!=192 or any(type(v) not in (int,float) or not math.isfinite(v) for v in x):return None
        length=math.sqrt(sum(v*v for v in x))
        if not length>0:return None
        return [v/length for v in x]
    except (TypeError,ValueError):return None
def band(a,b):
    x,y=vector(a),vector(b)
    if x is None or y is None:return 'invalid'
    score=sum(v*w for v,w in zip(x,y))
    return 'negative' if score<0 else 'below_0_5' if score<.5 else '0_5_to_0_7' if score<.7 else '0_7_to_0_8' if score<.8 else 'at_least_0_8'
def current(raw):
    try:
        m=json.loads(raw)
        return int(m.get('board_boot_id')=='a6d4a069-e9b0-4065-8df7-dc23556b168e' and m.get('generation')==64)
    except (TypeError,ValueError,AttributeError):return 0
deadline=time.monotonic()+3
try:
    db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA application_id').fetchone()==(0x41555350,)
    db.execute('ATTACH DATABASE ? AS anon',((private/'anonymous-voices.sqlite3').as_uri()+'?mode=ro',))
    assert db.execute('PRAGMA anon.application_id').fetchone()==(0x4155414E,)
    db.create_function('valid_vector',1,lambda x:int(vector(x) is not None))
    db.create_function('score_band',2,band);db.create_function('current_probe',1,current)
    db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000);db.execute('BEGIN')
    result={'formal_templates':db.execute('SELECT COUNT(*) FROM templates').fetchone()[0],
        'valid_formal_vectors':db.execute('SELECT COUNT(*) FROM templates WHERE dimension=192 AND valid_vector(embedding)=1').fetchone()[0],
        'anonymous_anchors':db.execute('SELECT COUNT(*) FROM anon.anonymous_anchors').fetchone()[0],
        'current_capture_observations':db.execute('SELECT COUNT(*) FROM anon.anonymous_observations WHERE current_probe(owner)=1').fetchone()[0]}
    base='FROM anon.anonymous_observations o JOIN anon.anonymous_labels l USING(cluster_id) JOIN anon.anonymous_anchors a USING(cluster_id) CROSS JOIN templates t JOIN anon.anonymous_meta m ON m.key=\'model_id\' AND m.value=t.model_id WHERE current_probe(o.owner)=1 AND t.dimension=192'
    result['same_model_comparisons']=db.execute('SELECT COUNT(*) '+base).fetchone()[0]
    result['anchor_created_for_this_capture']=db.execute('SELECT COUNT(*) '+base+' AND l.created=o.received').fetchone()[0]
    result['similarity_range_counts']={label:db.execute('SELECT COUNT(*) '+base+' AND score_band(t.embedding,a.anchor)=?',(label,)).fetchone()[0] for label in ('invalid','negative','below_0_5','0_5_to_0_7','0_7_to_0_8','at_least_0_8')}
    db.execute('ROLLBACK')
finally:db.close()
print(json.dumps(dict(counts=result,exact_query_vector_available=result['anchor_created_for_this_capture']>0,
    caveat='Existing anonymous anchor is only a proxy unless created for this exact capture; no identity assumption.',
    read_only=True,aggregate_COUNT_queries_only=True,names_ids_vectors_exact_scores_audio_images_transcripts_exported=False,
    models_or_project_stores_constructed=False)))
