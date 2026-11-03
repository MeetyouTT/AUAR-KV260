"""Verify the self-contained shared Linux host snapshot without board access."""
import argparse,hashlib,json,platform,re,subprocess,sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parent
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','AMD64'):
        raise RuntimeError('Offline snapshot requires Linux x86_64; no board execution')
    checked=0
    for manifest,base in ((root/'SOURCE_SHA256.txt',root),(root.parent/'DEPENDENCY_SHA256.txt',root.parent)):
        for line in manifest.read_text().splitlines():
            digest,relative=line.split('  ',1);p=(base/relative).resolve()
            p.relative_to(root.parent)
            if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise RuntimeError('Snapshot changed: '+relative)
            checked+=1
    for p in root.glob('*.py'):compile(p.read_text(),str(p),'exec')
    result=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(root),'-p','test_*.py'],
                          capture_output=True,text=True,timeout=30)
    if result.returncode:raise RuntimeError(result.stderr[-4000:])
    count=int(re.search(r'Ran (\d+) tests',result.stderr).group(1))
    report=dict(status='OFFLINE_VERIFICATION_PASS',files_checked=checked,tests_passed=count,
                scope='host FakeDevice, timing, face-only rules and native trajectory math',
                board_accessed=False,physical_follow_validated=False,summary=result.stderr.strip())
    with args.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ('status','files_checked','tests_passed','board_accessed')}))


if __name__=='__main__':main()
