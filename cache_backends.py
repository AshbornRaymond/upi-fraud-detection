# cache_backends.py
# Simple sqlite-backed JSON cache for orchestrator
import sqlite3, json, time
from pathlib import Path
from typing import Optional

class Cache:
    def __init__(self, sqlite_path: str = "orchestrator_cache.db"):
        self.path = Path(sqlite_path)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._ensure_table()

    def _ensure_table(self):
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                kind TEXT,
                value_json TEXT,
                ts INTEGER,
                ttl INTEGER
            )
        """)
        self._conn.commit()

    def _now(self):
        return int(time.time())

    def set(self, kind: str, key: str, value, ttl_seconds: int = 24*3600):
        cur = self._conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO cache (key, kind, value_json, ts, ttl)
            VALUES (?, ?, ?, ?, ?)
        """, (f"{kind}:{key}", kind, json.dumps(value, default=str), self._now(), int(ttl_seconds)))
        self._conn.commit()

    def get(self, kind: str, key: str) -> Optional[dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT value_json, ts, ttl FROM cache WHERE key = ?", (f"{kind}:{key}",))
        row = cur.fetchone()
        if not row:
            return None
        value_json, ts, ttl = row
        if ttl is not None and (self._now() - int(ts)) > int(ttl):
            # expired, delete
            cur.execute("DELETE FROM cache WHERE key = ?", (f"{kind}:{key}",))
            self._conn.commit()
            return None
        try:
            return json.loads(value_json)
        except Exception:
            return None

    def close(self):
        try:
            self._conn.close()
        except:
            pass
