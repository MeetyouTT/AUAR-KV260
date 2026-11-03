"""One isolated process per pinned route version; no model/device/storage IO."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser();parser.add_argument('version',choices=['baseline','v1','v2'])
    args=parser.parse_args()
    root=HERE/'runtime_v16'
    overlay={'baseline':root,'v1':HERE/'candidate/after','v2':HERE/'candidate_v2/after'}[args.version]
    sys.path[:0]=[str(root),str(HERE),r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies']
    for name in ('common','tools','board.runtime','board.runtime.audio'):
        module=importlib.import_module(name)
        module.__path__=[str(overlay/name.replace('.','/'))]+list(module.__path__)
    import audit_routes
    path=overlay/'tools/yuki_jobs_candidate.py'
    route,_=audit_routes.route_function(path)
    review=json.loads((HERE/'ROOT_REVIEW.json').read_bytes())
    rows=[dict(id=row['id'],public_question=row['public_question'],observed=audit_routes.probe(route,row['public_question']))
          for row in review['cases']]
    output=dict(version=args.version,level='code_or_fake_verified',
        executor='Actual formal instance-bound tools/yuki_jobs_candidate._route; synthetic ready guard and inert handlers.',
        source=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cases=rows,
        models_or_devices_called=False,actual_production_feature_execution=False)
    destination=HERE/('PAIRED_ROUTE_'+args.version.upper()+'.json')
    destination.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(version=args.version,routes=[row['observed']['route'] for row in rows]),ensure_ascii=False))


if __name__=='__main__':main()
