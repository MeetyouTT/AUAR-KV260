"""Startup-only selection of the existing face source's 200 ms option.

The original worker, retry/admission rounds, frame ownership, optical-flow
measurements, detector and identity callbacks remain the inherited functions.
This module never opens a camera, model, database or native context.
"""

POLICY = {
    'target_period_ms': 200,
    'inherited_period_ms': 100,
    'optical_flow': True,
    'scope': 'successful outer detector rounds; original retry/recovery unchanged',
    'recovery_interval_ms': 50,
    'identity_ttl_ms': 1000,
    'measurement_anchor_max_age_ms': 500,
    'measurement_max_age_ms': 250,
}


def install(source):
    """Interpose once, before the original camera wrapper installs the source."""
    if getattr(source, '_face_budget_candidate', None) is not None:
        raise RuntimeError('Face budget candidate already installed')
    original = source.install
    if not callable(original):
        raise RuntimeError('Inherited face source installer unavailable')
    state = {'installed': False, 'calls': 0}

    def install_200(camera, *, interval_ms=100, optical_flow=False):
        if (state['calls'] or getattr(camera, '_edge_face_source_installed', False)
                or getattr(camera, '_edge_face_raw_capture_v11', False)):
            raise RuntimeError('Face budget requires a fresh single startup')
        if type(interval_ms) is not int or interval_ms != 100 or optical_flow is not True:
            raise RuntimeError('Inherited face source selection changed')
        state['calls'] += 1
        result = original(camera, interval_ms=200, optical_flow=True)
        if (not getattr(camera, '_edge_face_source_installed', False)
                or not getattr(camera, '_edge_face_raw_capture_v11', False)):
            raise RuntimeError('Inherited face source/raw capture hooks were not installed')
        state['installed'] = True
        camera._face_budget_candidate = dict(POLICY)
        return result

    source.install = install_200
    source._face_budget_candidate = state
    return state
