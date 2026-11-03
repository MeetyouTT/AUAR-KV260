"""One-time reviewable source transform: extract unchanged joined snapshot."""
from pathlib import Path

target = Path(__file__).parent / 'after/common/board_memory.py'
text = target.read_text(encoding='utf-8')
start = text.index('    def check_prepared_turn_current(')
end = text.index('    def bind_audio_receipt(', start)
method = text[start:end]
body = method[method.index('            row = db.execute('):].rstrip()
body = '\n'.join(line[4:] if line.startswith('    ') else line for line in body.splitlines())
replacement = '''    def _prepared_read_authority(self, turn_id):
        grant = self._turn_grants.get(turn_id)
        return (self._scope({"kind": "profile", "id": getattr(grant, "profile_id", None), "grant": grant})
                if grant is not None else nullcontext(None))

    def check_prepared_turn_current(self, turn_id, *, generation):
        """Original standalone API: one new connection and fresh read snapshot."""
        _identifier(turn_id, "turn id"); _generation(generation)
        with self._prepared_read_authority(turn_id) as selected, self._db() as db:
            return self._check_prepared_snapshot(db, turn_id, generation, selected)

    def prepared_turn_checker(self, turn_id, *, generation):
        """Explicit owner-thread context manager for one audio production turn.

        Only the connection is reused. Every callable check independently takes
        the original profile grant, begins and ends a fresh read transaction,
        and validates the complete joined snapshot. Nothing grants future
        playback authority or retains a SQLite snapshot across packets.
        """
        _identifier(turn_id, "turn id"); _generation(generation)
        return _PreparedTurnReadSession(self, turn_id, generation)

    @staticmethod
    def _check_prepared_snapshot(db, turn_id, generation, selected):
'''+body+'\n\n'
target.write_text(text[:start]+replacement+text[end:], encoding='utf-8', newline='\n')
