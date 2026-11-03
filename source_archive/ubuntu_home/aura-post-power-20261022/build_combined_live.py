"""Derive the combined one-millisecond trial from the reviewed retry-only builder."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
text=(ROOT/'build_retry_live.py').read_text()
def replace(old,new):
 global text
 assert text.count(old)==1,(old[:90],text.count(old))
 text=text.replace(old,new)
replace("candidate=Path('/home/ghmd/aura-yunet-retry-integration-20261022')",
    "candidate=Path('/home/ghmd/aura-yunet-retry-light-20261022')")
replace("(candidate/'candidate-manifest.json')", "(candidate/'manifest.json')")
replace("+['tests/bootstrap.py','tests/test_yunet_retry.py']", "+['tests/bootstrap.py','tests/test_yunet_retry.py','tests/test_light.py','tests/test_service.py','tests/test_combined.py']")
text=text.replace('YUNET_RETRY_5MS_DUAL_MODEL_120S_ALWAYS_RESTORED','YUNET_RETRY_LIGHT_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED')
replace("assert checked_result['run']==39", "assert checked_result['run']==82")
replace("minimum_pixels=config['minimum_face_pixels'],slot_retry=True)",
        "minimum_pixels=config['minimum_face_pixels'],slot_retry=True,freshness_metrics=True)")
replace('AURA_EXPERIMENT_GIL_MS=5','AURA_EXPERIMENT_GIL_MS=1')
replace("startup['actual_start_seconds']==startup['previous_seconds']==.005", "startup['actual_start_seconds']==.001 and startup['previous_seconds']==.005")
text=text.replace("'gil_seconds':.005", "'gil_seconds':.001")
replace("pattern='test_yunet_retry.py'", "pattern='test_*.py'")
replace("report['passed']=all(0<=age<1000 for age in ages)", """light=state['face_targets']['freshness_metrics']
        assert light['schema_version']=='aura-face-freshness-light-2' and light['collecting']
        assert not light['observer_failures']
        assert all(light['counters'][key]==0 for key in ('process_errors','callback_errors',
            'invalid_source_ages','source_clock_pairs_rejected','counter_saturation'))
        assert light['summaries']['clipped_gap_upper_bound_ms']['count']>0
        report['freshness_final']=light
        report['passed']=all(0<=age<1000 for age in ages) and not light['counters']['observed_gap_intervals']
""")
replace("'RETRY_5MS_SHORT_WITH_SEPARATE_FRESHNESS_GATE_NOT_SPEEDUP_PROOF'", "'RETRY_LIGHT_1MS_SHORT_WITH_SEPARATE_FRESHNESS_GATE_NOT_SPEEDUP_PROOF'")
replace("target=HELPERS/'board_postpower_retry_live_usb3_20261022.py'", "target=HELPERS/'board_postpower_combined_live_v3_20261022.py'")
replace("(ROOT/'retry-live-manifest.json')", "(ROOT/'combined-live-manifest.json')")
replace("'freshness_observer_enabled':False", "'freshness_observer_enabled':True")
# The fake test gate and original rollback stay intact. Check measured cost
# against this exact merged observer before any production unit mutation.
anchor="source=source.replace('THREAD_SWITCH_DUAL_MODEL_120S_ALWAYS_RESTORED','YUNET_RETRY_LIGHT_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED')"
insert='''
marker="    before=camera();healthy(before);single_owner(before['pid']);idle=ui_idle()"
assert source.count(marker)==1
source=source.replace(marker,marker+"\\n    cost=json.loads(Path('/home/root/aura-post-power-20261022/light2-preflight/9b7373edd1316069/report.json').read_text())\\n    assert cost['passed'] and cost['assessment']['passed']\\n    for name,expected in RETRY_HASHES.items():\\n        if name.startswith('candidate/aura/'):assert cost['benchmark_report']['source_sha256'][name]==expected")
'''
replace(anchor,anchor+'\n'+insert)
needle="    check_source=FAKE_TEST_WORKER.replace('ROOT_VALUE',repr(str(folder))).replace('AURA_VALUE',repr(str(candidate)))"
prefix='''    # Some frozen tests load by ROOT/candidate/aura rather than import path.
    # Keep a byte-identical, source-only fixture layout; no models are copied.
    for name,expected in RETRY_HASHES.items():
        if name.startswith('candidate/aura/'):
            actual=candidate/name[len('candidate/aura/'):]
            fixture=folder/name;fixture.parent.mkdir(parents=True,exist_ok=True)
            assert not fixture.is_symlink();fixture.write_bytes(actual.read_bytes())
            assert digest(fixture)==expected
'''
replace(needle,prefix+needle)
compile(text,'<combined-trial-builder>','exec')
exec(compile(text,'<combined-trial-builder>','exec'),{'__file__':str(__file__),'__name__':'__main__'})
