"""Create an inspectable16fps candidate with source/evidence; no deployment."""
from pathlib import Path
import datetime,hashlib,json,zipfile

ab=Path(__file__).parent;phase=ab.parent;base=phase.parent
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    original=base/'isolated-yuki-candidate-20261030.zip'
    assert digest(original.read_bytes())=='2e033832a7e498a4afec67effa59aa11846a835da6f6cda78c0d7bf1b17cfeea'
    conclusion=json.loads((ab/'resource-conclusion-resume-v2.json').read_text(encoding='utf-8'))
    assert conclusion['production_deployed'] is False
    target=base/'isolated-yuki-candidate16-resource-20261030.zip';assert not target.exists()
    with zipfile.ZipFile(original) as old:
        files={name:old.read(name) for name in old.namelist() if name!='manifest.json'}
    config=json.loads(files['native_yuki.config.fragment.json']);assert config['native_yuki']['fps']==24
    config['native_yuki']['fps']=16;files['native_yuki.config.fragment.json']=json.dumps(config,indent=2).encode()
    files['verification.json']=(phase/'verification.json').read_bytes()
    files['README.txt']=((phase/'README.txt').read_text(encoding='utf-8')+'\n本包只供审阅/隔离验证，不是自动部署器。配置fragment使用本轮计量过的16fps；原24fps技术候选原包保留。部署须用户决定，并在当时业务源码上审阅合并GTK/worker两个补丁，重新核验入口、组件及实际负载。旧remote A/C对照复现还需要现有被pin的AURA runtime与renderer_snapshot；不把包内结果当成未来业务并发保证。\n').encode('utf-8')
    additions={
        'resource_ab/RESOURCE_AB_REPORT.txt':phase/'RESOURCE_AB_REPORT.txt',
        'resource_ab/analysis.json':ab/'analysis-formal-resume-v3/analysis.json',
        'resource_ab/runs.csv':ab/'analysis-formal-resume-v3/runs.csv',
        'resource_ab/raw-evidence.zip':base/'evidence/native_integration/paired_ab/formal-resume-v2-evidence.zip',
        'resource_ab/final-board-check.json':base/'evidence/native_integration/paired_ab/formal-resume-v2-final-board-check.json',
        'resource_ab/conclusion.json':ab/'resource-conclusion-resume-v2.json',
        'resource_ab/analysis-policy.json':ab/'analysis-policy-resume-v2.json',
        'resource_ab/analysis-source-manifest.json':ab/'analysis-source-manifest-resume-v2.json',
        'resource_ab/sealed-plan.json':ab/'suite-formal-resume-v2.json'}
    for name in ('analyze_results.py','quality_checks.py','quality-checks-freeze.json','paired_renderer_harness.py',
                 'old_renderer_harness.py','old_harness_support.py','telemetry.py','run_suite.py','finalize_resource_report.py'):
        additions['resource_ab/source/'+name]=ab/name
    for name,path in additions.items():files[name]=path.read_bytes()
    manifest=dict(schema='aura.yuki.isolated_candidate.v2',production_deployed=False,user_decision_required=True,
        scope='Yuki-only16fps native candidate plus matched resource evidence; no production/firmware/service mutation',
        original24fps_package_sha256=digest(original.read_bytes()),measured_fps=16,
        basis=json.loads((phase/'board_source/manifest.json').read_text(encoding='utf-8')),
        resource_conclusion=conclusion,files={name:digest(data) for name,data in sorted(files.items())})
    files['manifest.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as output:
        for name,data in sorted(files.items()):output.writestr(name,data)
    with zipfile.ZipFile(target) as check:
        assert check.testzip() is None
        assert all(digest(check.read(name))==h for name,h in manifest['files'].items())
    receipt=dict(package=str(target),sha256=digest(target.read_bytes()),bytes=target.stat().st_size,
        files=len(files),all_manifest_files_verified=True,original_package_preserved=True,
        production_deployed=False,configured_fps=16,created_at_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (ab/'resource-candidate-package.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt))

if __name__=='__main__':main()
