"""One explicit opt-in hook for the existing private-root CPU device Hub."""
from common.anonymous_voice import AnonymousVoiceStore,AnonymousPolicy
from tools.progressive_speaker import ProgressiveSpeakerAnalyzer

def install_anonymous(hub,config):
    if not isinstance(config,dict) or set(config)-{'enabled','threshold','margin','retention_seconds','max_clusters'}:
        raise ValueError('Unexpected anonymous speaker configuration')
    enabled=config.get('enabled',False)
    if type(enabled) is not bool:raise ValueError('Anonymous collection needs explicit boolean configuration')
    if not enabled:return None
    if hub.speaker is None:raise ValueError('Initialize the existing CPU speaker model first')
    policy=AnonymousPolicy(threshold=config.get('threshold',.90),margin=config.get('margin',.10),
      ttl_seconds=config.get('retention_seconds',86400),max_clusters=config.get('max_clusters',32))
    # The existing Hub root is the production private AppData root. It must
    # never be replaced by a source-package or weight-directory path.
    store=AnonymousVoiceStore(hub.root/'anonymous-voices.sqlite3',hub.speaker.encoder.model_id,
      hub.speaker.encoder.dimension,policy=policy)
    return ProgressiveSpeakerAnalyzer(hub.speaker,store,enabled=True)
