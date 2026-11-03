"""Derive an isolated 50ms failed-round recovery trial with unchanged rollback."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
text=(ROOT/'build_gap3_live.py').read_text()
text=text.replace('aura-yunet-retry-gap-audit-20261023','aura-yunet-recovery-20261023')
text=text.replace("for name in constants['RETRY_PAYLOAD']}",
                  "for name in list(constants['RETRY_PAYLOAD'])+['tests/test_recovery.py']}")
text=text.replace('"assert checked_result[\'run\']==85"','"assert checked_result[\'run\']==89"')
text=text.replace('/gap3-preflight/99e52c483594cd2f/', '/recovery-preflight/f5e984bd7d38d89a/')
text=text.replace('99e52c483594cd2fcb9921b2d8aeda6f955bafbc429aa43070e1955ca55af89f',
                  'f5e984bd7d38d89afc0ceb8256fdd74261287d784dfaca8068cbb729f04fbc1d')
text=text.replace('YUNET_RETRY_GAP3_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED',
                  'YUNET_RECOVERY50_GAP3_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED')
text=text.replace("('gap3-'+str(os.getpid()))", "('recovery50-'+str(os.getpid()))")
text=text.replace('postpower-gap3-launches','postpower-recovery50-launches')
text=text.replace('aura-postpower-gap3-live-','aura-postpower-recovery50-live-')
text=text.replace('board_gap3_live_20261023.py','board_recovery50_live_20261023.py')
text=text.replace('gap3-live-manifest.json','recovery50-live-manifest.json')
text=text.replace("'tests':85", "'tests':89,'recovery_interval_ms':50")
marker='newtree=ast.parse(source)'
assert text.count(marker)==1
extra='''replace("slot_retry=True,freshness_metrics=True)","slot_retry=True,freshness_metrics=True,retry_recovery_ms=50)")
replace("        assert state['face_targets']['slot_retry']['enabled']", "        assert state['face_targets']['slot_retry']['enabled']\\n        assert state['face_targets']['slot_retry']['recovery_interval_ms']==50")
'''
text=text.replace(marker,extra+marker)
exec(compile(text,str(__file__),'exec'),{'__file__':str(__file__),'__name__':'__main__'})
