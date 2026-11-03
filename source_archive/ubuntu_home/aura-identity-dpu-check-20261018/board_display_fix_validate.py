import hashlib,json,subprocess
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
roots=list(Path('/home/root/aura-display-startup-fix-20261020').iterdir());assert len(roots)==1
root=roots[0]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=root/"install.py";assert sha(p)=='9307598b0e34e6f939661dd6f8ee25454b579ab3a588940ccede507fe71f151e'
s=p.read_text();assert s.count("            replace(Path(record['target']), (here/record['source']).read_bytes(), record['mode'])\n            applied.append(record)\n")==1
s=s.replace("            replace(Path(record['target']), (here/record['source']).read_bytes(), record['mode'])\n            applied.append(record)\n","            applied.append(record)\n            replace(Path(record['target']), (here/record['source']).read_bytes(), record['mode'])\n");compile(s,str(p),"exec");p.write_text(s)
p=root/"test_install.py";assert sha(p)=='9499a2c6276d3f4ca56a09ef9d17d922e4823b95494942aaa51458d1b4aba5d4'
s=p.read_text();s=s[:3997]+"\n    def test_failure_after_atomic_rename_still_rolls_back(self):\n        original=install.replace\n        def replace(path,data,mode):\n            original(path,data,mode)\n            if path==self.old and data==b'new launcher':raise OSError('fixture directory fsync failure')\n        with patch.object(install,'replace',side_effect=replace):\n            with self.assertRaises(OSError):self.run_action('apply')\n        self.assertEqual(self.old.read_bytes(),b'old launcher')\n        self.assertEqual(self.xorg.read_bytes(),b'old xorg')\n"+s[3997:];compile(s,str(p),"exec");p.write_text(s)
expected={'install.py': 'c4bddf817479b317ce0561702ad95d7e43d18a3ed4a59fdb5f44ea3ee2727640', 'launcher.py': 'ea68cb074bef23f5c71ec80d020fbac38c597009ab430cd3bd89eb836ef3105c', 'manifest.json': 'ced8db32b63160825d6e3637a0e61e40811e5083d7b86e16c3a02617a4252d24', 'test_display_fallback.py': 'b5ccc64e9ec73281a4af5eb7c0f449d5e9bf72efb30228017da5861c56839c08', 'test_display_startup.py': 'a2877bb3d9787d30e1b22e523e65652b97fc0c765617ddff785ec1d08c5fef8e', 'test_install.py': 'a11d5a273a46c39d630f6a4a4a7f46b826608a67cc5ce56c7dd37995fc9687c2', 'test_retrain_results.py': '10c4c6e79d97f90aed0326de0291dc432c75ebbef4745cd1d7119098800d20b8', 'xorg.conf': '64457c25a844ef95cd4ae62bacba80b0cbec5ae1a54efdc15e3ec02775c0555a'}
assert all(sha(root/n)==v for n,v in expected.items())
p=subprocess.run(["python3","-B","-m","unittest","discover","-s",str(root),"-q"],cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
assert p.returncode==0,p.stdout
v={"status":"PASS_BOARD_SOFTWARE_ONLY","release":str(root),"files":expected,"tests":p.stdout,"display_commands_sent":0,"movement_commands_sent":0,"files_activated":False}
(root/"candidate-validated.json").write_text(json.dumps(v,indent=2)+"\n")
print(json.dumps(v),flush=True)
