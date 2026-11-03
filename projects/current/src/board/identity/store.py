"""SQLite identities: no automatic enrollment; templates are model-specific."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sqlite3
from common.contracts import finite, integer


@dataclass(frozen=True)
class IdentityMatch:
    state: str
    identity_id: str = ""
    name: str = ""
    score: float = 0.0
    revision: int = 0


def normalize(embedding, dimension):
    values = tuple(embedding)
    if len(values) != dimension or not all(finite(v) for v in values):
        raise ValueError("Embedding dimension/non-finite mismatch")
    norm = math.sqrt(sum(v * v for v in values))
    if norm <= 1e-12:
        raise ValueError("Zero embedding")
    return tuple(v / norm for v in values)


class IdentityStore:
    def __init__(self, path, model_id, dimension, threshold, ambiguity_margin, *, allow_cross_thread=False):
        if not model_id or not integer(dimension, 1) or not -1 <= threshold <= 1 or not 0 <= ambiguity_margin <= 2:
            raise ValueError("Invalid identity model/threshold")
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.model_id, self.dimension = model_id, dimension
        self.threshold, self.ambiguity_margin = threshold, ambiguity_margin
        # A cross-thread connection requires its single owning service's lock.
        self.db = sqlite3.connect(str(path), check_same_thread=not allow_cross_thread)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS identities (id TEXT PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS templates (
                identity_id TEXT NOT NULL REFERENCES identities(id) ON DELETE CASCADE,
                model_id TEXT NOT NULL, dimension INTEGER NOT NULL, embedding TEXT NOT NULL,
                PRIMARY KEY(identity_id, model_id));
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
            INSERT OR IGNORE INTO metadata VALUES ('revision', 0);
        """)
        self.db.commit()

    @property
    def revision(self):
        return self.db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]

    def people(self):
        return [{'person_id': key, 'display_name': name} for key, name in self.db.execute(
            'SELECT i.id, i.name FROM identities i JOIN templates t ON i.id=t.identity_id '
            'WHERE t.model_id=? AND t.dimension=? ORDER BY i.name, i.id', (self.model_id, self.dimension))]

    def enroll(self, identity_id, name, embedding, *, consent=False, expected_revision=None, max_people=None):
        if consent is not True or not identity_id or not isinstance(name, str) or not name.strip():
            raise ValueError("Explicit enrollment with a name and consent required")
        vector = normalize(embedding, self.dimension)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if expected_revision is not None and self.revision != expected_revision:
                raise ValueError('身份库版本已变化，请刷新后重试')
            people=self.people()
            if max_people is not None and len(people) >= max_people and identity_id not in [r['person_id'] for r in people]:
                raise ValueError('身份库已满，请先删除不再使用的身份')
            self.db.execute("INSERT INTO identities VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name",
                            (identity_id, name.strip()))
            self.db.execute("INSERT OR REPLACE INTO templates VALUES (?, ?, ?, ?)",
                            (identity_id, self.model_id, self.dimension, json.dumps(vector)))
            self.db.execute("UPDATE metadata SET value=value+1 WHERE key='revision'")

    def delete(self, identity_id, *, expected_revision=None):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if expected_revision is not None and self.revision != expected_revision:
                raise ValueError('身份库版本已变化，请刷新后重试')
            count = self.db.execute("DELETE FROM identities WHERE id=?", (identity_id,)).rowcount
            if count:
                self.db.execute("UPDATE metadata SET value=value+1 WHERE key='revision'")
        return bool(count)

    def match(self, embedding):
        vector = normalize(embedding, self.dimension)
        rows = self.db.execute("""SELECT i.id, i.name, t.embedding FROM identities i
            JOIN templates t ON i.id=t.identity_id WHERE t.model_id=? AND t.dimension=?""",
            (self.model_id, self.dimension))
        scored = sorted(((sum(a * b for a, b in zip(vector, normalize(json.loads(raw), self.dimension))), key, name)
                         for key, name, raw in rows), reverse=True)
        rev = self.revision
        if not scored or scored[0][0] < self.threshold:
            return IdentityMatch("UNKNOWN", score=scored[0][0] if scored else 0.0, revision=rev)
        score, key, name = scored[0]
        if len(scored) > 1 and score - scored[1][0] < self.ambiguity_margin:
            return IdentityMatch("AMBIGUOUS", score=score, revision=rev)
        return IdentityMatch("KNOWN", key, name, score, rev)

    def best_other_score(self, embedding, exclude_id=''):
        """Future-gallery check for an explicitly selected replacement."""
        vector=normalize(embedding,self.dimension)
        rows=self.db.execute('SELECT identity_id,embedding FROM templates WHERE model_id=? AND dimension=?',
                             (self.model_id,self.dimension))
        scores=[sum(a*b for a,b in zip(vector,normalize(json.loads(raw),self.dimension)))
                for identity_id,raw in rows if identity_id!=exclude_id]
        return max(scores) if scores else None

    def close(self):
        self.db.close()
