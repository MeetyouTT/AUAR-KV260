"""Private local readback of the pinned *actual* INT8 gallery; never writes.

Used only on the voice network worker. It loads no camera/model/native runner.
The private embeddings are validated and hashed here, never returned or stored.
"""
import hashlib,json,sqlite3
from pathlib import Path
from board.identity.store import normalize
from board.interaction.ui_contract import millis,validate_snapshot
from common.face_binding_wire import validate_packet

class FaceGalleryReadback:
    def __init__(self,config,*,verify=None,clock=millis):
        if not isinstance(config,dict) or config.get('version')!=1 or config.get('enabled') is not True:
            raise ValueError('Pinned actual face gallery readback is disabled')
        self.config=dict(config);self.verify=verify or self._verify;self.clock=clock

    @classmethod
    def configured(cls):
        path=Path(__file__).resolve().parents[3]/'config/face_gallery_readback.local.json'
        try:return cls(json.loads(path.read_text(encoding='utf-8')))
        except (OSError,ValueError,TypeError):return None

    @staticmethod
    def _verify(config):
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if boot!=config['board_boot_id']:raise ValueError('Readback configuration belongs to another boot')
        proc=Path('/proc')/str(config['camera_pid'])
        cmd=proc.joinpath('cmdline').read_bytes()
        ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]
        if hashlib.sha256(cmd).hexdigest()!=config['camera_cmdline_sha256'] or ticks!=config['camera_start_ticks']:
            raise ValueError('Actual camera process owner changed')
        for name,digest in config['source_sha256'].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError('Pinned camera source changed')
        runtime=json.loads(Path(config['camera_config']).read_text())
        if runtime.get('identity')!={'enabled':True,'config':config['identity_config']}:
            raise ValueError('Actual camera selected a different identity source')
        identity=json.loads(Path(config['identity_config']).read_text())
        if (identity.get('database')!=config['database'] or identity.get('model_id')!=config['model_id']
            or identity.get('schema_version')!='aura-camera-identity-1'
            or identity.get('result_ttl_ms')!=config['result_ttl_ms']
            or identity.get('feature_backend',{}).get('kind')!='dpu_sface'
            or identity.get('feature_backend',{}).get('model_sha256')!=config['model_sha256']):
            raise ValueError('Actual INT8 model/gallery source changed')
        if config['dimension']!=128 or config['backend']!='DPU_SFACE_INT8':raise ValueError('Unexpected pinned INT8 dimension/backend')

    def read(self,meta,snapshot):
        c=self.config;self.verify(c)
        value=validate_snapshot(snapshot,meta['board_boot_id'],self.clock())
        identity=value['modules'].get('identity',{})
        if (value['source_kind']!='actual' or value['board_boot_id']!=c['board_boot_id']
           or identity.get('backend')!=c['backend']):raise ValueError('Actual identity backend is unavailable')
        path=Path(c['database']).expanduser()
        if path.is_symlink() or not path.is_file():raise ValueError('Actual private gallery is unavailable')
        resolved=path.resolve(strict=True)
        try:db=sqlite3.connect(resolved.as_uri()+'?mode=ro',uri=True,timeout=.03)
        except sqlite3.Error as exc:raise ValueError('Private face gallery readback unavailable') from exc
        try:
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA busy_timeout=30');db.execute('BEGIN')
            binding=db.execute('SELECT model_id,dimension FROM identity_model_binding').fetchall()
            if binding!=[(c['model_id'],c['dimension'])]:raise ValueError('Wrong INT8 gallery model binding')
            foreign=db.execute('SELECT DISTINCT model_id,dimension FROM templates').fetchall()
            if any(row!=(c['model_id'],c['dimension']) for row in foreign):raise ValueError('Mixed face models in actual gallery')
            revision=db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()
            if (revision is None or type(revision[0]) is not int or revision[0]!=identity.get('db_version')):
                raise ValueError('Actual gallery revision changed during capture')
            rows=db.execute('SELECT t.identity_id,t.embedding FROM templates t JOIN identities i ON i.id=t.identity_id '
                'WHERE t.model_id=? AND t.dimension=? ORDER BY t.identity_id',(c['model_id'],c['dimension'])).fetchmany(33)
            if len(rows)>32:raise ValueError('Original face gallery limit exceeded')
            inventory=[]
            for identity_id,raw in rows:
                if not isinstance(raw,str) or len(raw)>200000:raise ValueError('Invalid private face template')
                vector=json.loads(raw)
                try:normalize(vector,c['dimension'])
                finally:vector=None
                inventory.append([identity_id,hashlib.sha256(raw.encode()).hexdigest()])
            raw=None;rows=None
            current=None
            if identity.get('state')=='KNOWN' and identity.get('person_id'):
                matches=[row for row in inventory if row[0]==identity['person_id']]
                if len(matches)==1:current=dict(identity_id=matches[0][0],template_fingerprint=matches[0][1])
            gallery=dict(store_id='gallery-'+hashlib.sha256((str(resolved)+'\0'+c['model_id']+'\0'+str(c['dimension'])).encode()).hexdigest()[:32],
                model_id=c['model_id'],revision=revision[0],source_kind='actual')
            return validate_packet(dict(version=1,context=dict(meta),gallery=gallery,current=current,inventory=inventory),meta)
        except sqlite3.Error as exc:raise ValueError('Private face gallery readback unavailable') from exc
        finally:db.close()
