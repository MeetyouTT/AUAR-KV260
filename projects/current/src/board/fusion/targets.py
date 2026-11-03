class TargetSelector:
    def __init__(self, policy="single_or_manual"):
        self.policy = policy
        self.current_key = None
        self.manual_key = None

    def select(self, tracks):
        candidates = [t for t in tracks if t.visible and t.confirmed]
        by_key = {t.target_key: t for t in candidates}
        if self.manual_key is not None:
            target = by_key.get(self.manual_key)
        elif self.current_key in by_key:
            target = by_key[self.current_key]
        elif len(candidates) == 1:
            target = candidates[0]
        elif candidates and self.policy == "largest":
            target = max(candidates, key=lambda t: (t.box[2] * t.box[3], -t.track_id))
        else:
            target = None
        self.current_key = target.target_key if target else None
        return target

    def reset(self):
        self.current_key = self.manual_key = None
