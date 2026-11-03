import datetime,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
result=subprocess.run([sys.executable,'-B',str(HERE/'test_six_file_transaction.py')],capture_output=True,text=True,encoding='utf-8')
log=result.stdout+result.stderr
with (HERE/'TRANSACTION_TEMPLATE_TESTS.log').open('x',encoding='utf-8') as stream:stream.write(log)
assert result.returncode==0 and 'Ran 10 tests' in log and '\nOK\n' in log,log
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':10,'failures':0,'errors':0,
    'template_sha256':hashlib.sha256((HERE/'six_file_transaction_template.py').read_bytes()).hexdigest(),
    'test_source_sha256':hashlib.sha256((HERE/'test_six_file_transaction.py').read_bytes()).hexdigest(),
    'scope':'Isolated local filesystem fault/recovery and seed/plan metadata tests',
    'target_cli_or_live_guard_executed':False,'ssh_or_board_operations':False,
    'actual_native_reader_semantics_tested':False,'requires_root_review_and_target_dry_run':True}
with (HERE/'TRANSACTION_TEMPLATE_TESTS.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
print(json.dumps(receipt))
