"""Read-only metadata inside the owning node; never returns a template vector.

The path/model/dimension come from the pinned actual service configuration, never
from an LLM or a user HTTP body. This is also usable on the board without loading
the camera model or restarting its service.
"""
import hashlib,json,sqlite3
from pathlib import Path
from board.identity.store import normalize

def private_gallery_reference(path,model_id,dimension,*,identity_id=None,expected_application_id=None):
    path=Path(path).resolve(strict=True)
    if type(dimension) is not int or not 1<=dimension<=4096 or not isinstance(model_id,str) or not model_id:
        raise ValueError('Pinned model metadata required')
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=.03)
    try:
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA busy_timeout=30');db.execute('BEGIN')
        if expected_application_id is not None and db.execute('PRAGMA application_id').fetchone()[0]!=expected_application_id:
            raise ValueError('Wrong original gallery application')
        revision=db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()
        if revision is None or type(revision[0]) is not int or revision[0]<0:raise ValueError('No original gallery revision')
        result=dict(store_id='gallery-'+hashlib.sha256((str(path)+'\0'+model_id+'\0'+str(dimension)).encode()).hexdigest()[:32],
          model_id=model_id,revision=revision[0],source_kind='actual')
        if identity_id is not None:
            row=db.execute('SELECT i.name,t.embedding FROM identities i JOIN templates t ON i.id=t.identity_id WHERE i.id=? AND t.model_id=? AND t.dimension=?',
              (identity_id,model_id,dimension)).fetchone()
            if row is None or not isinstance(row[1],str) or len(row[1])>200000:raise ValueError('Original model-specific template unavailable')
            normalize(json.loads(row[1]),dimension)
            result.update(identity_id=identity_id,display_name=row[0],template_fingerprint=hashlib.sha256(row[1].encode()).hexdigest())
        return result
    finally:db.close()

def gallery_fields(reference):
    return {key:reference[key] for key in ('store_id','model_id','revision')}
