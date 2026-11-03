import hashlib,json,tempfile,unittest
from pathlib import Path
import follow_readback as f

class ReadbackTests(unittest.TestCase):
    def test_only_exact_stopped_receipt_passes_and_never_expands_jog_bounds(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);gui=root/'gui';(gui/'config').mkdir(parents=True)
            consumer=root/'consumer';(consumer/'runs').mkdir(parents=True)
            source=consumer/'a.py';source.write_text('pinned source')
            digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            mp=consumer/'deployment-manifest.json'
            mp.write_text(json.dumps({'files':[{'destination':str(source),'sha256':digest(source)}]}))
            cfg={'release_root':str(consumer),'manifest_sha256':digest(mp)}
            (gui/'config/pan_face.local.json').write_text(json.dumps(cfg))
            state=dict(flags=0,lease_left_ms=0,width_us=1490,target_us=1490,ack_seq=8,epoch=3,session=17,reference_us=1445)
            report=dict(status='FINITE_FACE_EDGE_SESSION_STOPPED',boot_id='boot',target_kind='face',
                range_us=[1425,1505],consumer_manifest_sha256=digest(mp),result={'stopped':state})
            rp=consumer/'runs/trial.json';rp.write_text(json.dumps(report))
            (root/'face-stopped-readback.json').write_text(json.dumps({'report':str(rp),'sha256':digest(rp)}))
            oldroot,oldgui=f.ROOT,f.GUI;f.ROOT,f.GUI=root,gui
            try:
                manual=dict(boot_id='boot',manual_minimum_us=1425,manual_maximum_us=1445)
                self.assertTrue(f.verified_stopped_face_command(manual,state))
                self.assertEqual(manual['manual_maximum_us'],1445)
                active=root/'new-consumer';active.mkdir();new_manifest=active/'deployment-manifest.json'
                new_manifest.write_text(json.dumps({'files':[]}))
                updated=dict(release_root=str(active),manifest_sha256=digest(new_manifest),
                    stopped_readback_predecessors=[{'root':str(consumer),'sha256':digest(mp)}])
                (gui/'config/pan_face.local.json').write_text(json.dumps(updated))
                self.assertTrue(f.verified_stopped_face_command(manual,state))
                (gui/'config/pan_face.local.json').write_text(json.dumps(dict(updated,stopped_readback_predecessors=[])))
                self.assertFalse(f.verified_stopped_face_command(manual,state))
                (gui/'config/pan_face.local.json').write_text(json.dumps(updated))
                for key,value in [('flags',15),('width_us',1491),('epoch',4),('ack_seq',9)]:
                    self.assertFalse(f.verified_stopped_face_command(manual,dict(state,**{key:value})))
                source.write_text('changed')
                self.assertFalse(f.verified_stopped_face_command(manual,state))
            finally:f.ROOT,f.GUI=oldroot,oldgui

if __name__=='__main__':unittest.main()
