import bootstrap
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from migration import archive_plan,cosine


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.db=self.root/'old.sqlite3';con=sqlite3.connect(self.db)
        con.executescript('CREATE TABLE metadata(key TEXT,value INTEGER);CREATE TABLE identities(id TEXT,name TEXT);'
                          'CREATE TABLE templates(identity_id TEXT,embedding TEXT,model_id TEXT,dimension INTEGER);')
        con.execute('INSERT INTO metadata VALUES (?,?)',('revision',3))
        con.execute('INSERT INTO identities VALUES (?,?)',('private-id','private-name'))
        con.execute('INSERT INTO templates VALUES (?,?,?,?)',('private-id',json.dumps([1.]*128),'old-model',128));con.commit();con.close()
        self.archive=self.root/'archive';self.folder=self.archive/('a'*32);self.folder.mkdir(parents=True)
        self.doc={'schema':'aura-enrollment-photos-1','outcome':'committed','database_revision_after':3,
                  'template_policy':'frontal_medoid_v1','truncated':False,'images':[],
                  'selected':{'filename':'selected.png','frame_id':1},'validation_frame_ids':[2,3,4,5,6]}
        raw=b'private-pixels';(self.folder/'selected.png').write_bytes(raw)
        self.doc['selected']['sha256']=hashlib.sha256(raw).hexdigest()
        for fid in range(1,7):
            name='frame_%010d.png'%fid;(self.folder/name).write_bytes(raw)
            self.doc['images'].append({'filename':name,'frame_id':fid,'sha256':hashlib.sha256(raw).hexdigest(),
                'decision':'collect' if fid==1 else 'validation_pass'})
        self.config={'database':str(self.db),'model_id':'old-model','enrollment_photos':{'directory':str(self.archive)}}
        self.write()

    def tearDown(self):self.temp.cleanup()
    def write(self):(self.folder/'manifest.json').write_text(json.dumps(self.doc))

    def test_archive_reproduces_one_identity_without_touching_original(self):
        before=self.db.read_bytes();plan=archive_plan(self.config)
        self.assertEqual(plan['revision'],3);self.assertEqual(len(plan['probes']),5)
        self.assertEqual(plan['person_id'],'private-id');self.assertEqual(plan['verified_images'],7)
        self.assertEqual(self.db.read_bytes(),before)
        self.assertAlmostEqual(cosine(plan['old_vector'],[2.]*128),1.)

    def test_uncommitted_or_wrong_revision_archive_is_rejected(self):
        for key,value in (('outcome','in_progress'),('database_revision_after',2)):
            old=self.doc[key];self.doc[key]=value;self.write()
            with self.assertRaises(ValueError):archive_plan(self.config)
            self.doc[key]=old

    def test_archive_cannot_alias_or_escape_original_directory(self):
        (self.folder/'selected.png').unlink();(self.folder/'selected.png').symlink_to(self.db)
        with self.assertRaises(ValueError):archive_plan(self.config)

    def test_duplicate_commit_for_revision_is_rejected(self):
        duplicate=self.archive/('b'*32);duplicate.mkdir();(duplicate/'manifest.json').write_text(json.dumps(self.doc))
        with self.assertRaises(ValueError):archive_plan(self.config)

    def test_altered_photo_checksum_is_rejected(self):
        (self.folder/'frame_0000000002.png').write_bytes(b'changed')
        with self.assertRaises(ValueError):archive_plan(self.config)

    def test_validation_is_disjoint_from_selected_crop(self):
        self.doc['validation_frame_ids']=[1,2,3,4,5];self.write()
        with self.assertRaises(ValueError):archive_plan(self.config)

    def test_missing_or_relabelled_validation_frame_is_rejected(self):
        self.doc['images'][2]['decision']='collect';self.write()
        with self.assertRaises(ValueError):archive_plan(self.config)

    def test_multiple_people_or_foreign_model_cannot_be_guessed(self):
        con=sqlite3.connect(self.db);con.execute('UPDATE templates SET model_id=?',('other',));con.commit();con.close()
        with self.assertRaises(ValueError):archive_plan(self.config)

    def test_invalid_vectors_and_nonfinite_scores_are_rejected(self):
        for vector in ([1.]*127,[0.]*128,[float('nan')]*128):
            with self.assertRaises(ValueError):cosine(vector,[1.]*128)


if __name__=='__main__':unittest.main()
