"""UI-only guarded deployment; keep the active enrollment photo camera running."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
prior=HERE.parent/'2026-10-19_identity_query_routing'
raw=(prior/'activate.py').read_text(encoding='utf-8')
raw=raw.replace("all(p[k] for k in ('real_models_passed','bootstrap_passed','widget_passed'))",
                "all(p[k] for k in ('capture_source_passed','bootstrap_passed'))")
raw=raw.replace('/home/root/aura-spoken-identity-routing-20261019','/home/root/aura-identity-capture-snapshot-20261019')
raw=raw.replace("assert not s['automatic_conversation']['enabled'];return s",
                "assert not s['automatic_conversation']['enabled'];assert not s['local_transcription']['service']['voice_enrollment']['active'];return s")
raw=raw.replace('SPOKEN_IDENTITY_QUERY_DEPLOYED_AWAITING_REAL_USER','IDENTITY_CAPTURE_SOURCE_FIXED_PHOTO_CAMERA_PRESERVED')
raw=raw.replace("assert pc['identity_features']['ready']", "assert camera['identity']['enrollment_photos']['enabled'] and camera['identity']['enrollment_photos']['ready']\nassert pc['identity_features']['ready']")
(HERE/'activate.py').write_text(raw,encoding='utf-8')
raw=(prior/'rollback.py').read_text(encoding='utf-8').replace('PREVIOUS_UI_WITHOUT_QUERY_STARTING','PREVIOUS_UI_STARTING_PHOTO_CAMERA_PRESERVED')
(HERE/'rollback.py').write_text(raw,encoding='utf-8')
print('UI-only activation and rollback prepared')
