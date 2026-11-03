"""Local monitoring preference; explicit pause survives restarts."""
import json
import os
from pathlib import Path
import uuid


class HandsFreeSettings:
    def __init__(self,path):self.path=Path(path)

    def read(self):
        if not self.path.exists():return True
        value=json.loads(self.path.read_text(encoding='utf-8'))
        if (not isinstance(value,dict) or set(value)!={'version','enabled'}
                or type(value['version']) is not int or value['version']!=1
                or type(value['enabled']) is not bool):
            raise ValueError('Invalid hands-free preference')
        return value['enabled']

    def write(self,enabled):
        if type(enabled) is not bool:raise ValueError('Expected boolean monitoring choice')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_name(self.path.name+'.tmp-'+uuid.uuid4().hex)
        try:
            with os.fdopen(os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as out:
                json.dump({'version':1,'enabled':enabled},out);out.flush();os.fsync(out.fileno())
            os.replace(tmp,self.path)
        finally:tmp.unlink(missing_ok=True)
