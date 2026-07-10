"""Local voice-history store: SQLite + single background writer thread."""

from __future__ import annotations

import logging
import queue
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS history (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id    TEXT    NOT NULL,
  seq           INTEGER NOT NULL,
  created_at    INTEGER NOT NULL,
  raw_text      TEXT    NOT NULL DEFAULT '',
  polished_text TEXT    NOT NULL DEFAULT '',
  source        TEXT    NOT NULL DEFAULT '',
  duration_ms   INTEGER NOT NULL DEFAULT 0,
  target_app    TEXT    NOT NULL DEFAULT '',
  trigger_mode  TEXT    NOT NULL DEFAULT '',
  model         TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_history_session ON history(session_id);
CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at);
"""

_SESSION_SUMMARY_SQL = """
SELECT
  h.session_id,
  MIN(h.created_at) AS session_created,
  COUNT(*) AS segment_count,
  (
    SELECT source FROM history h2
    WHERE h2.session_id = h.session_id
    ORDER BY h2.seq ASC LIMIT 1
  ) AS source,
  (
    SELECT target_app FROM history h2
    WHERE h2.session_id = h.session_id
    ORDER BY h2.seq ASC LIMIT 1
  ) AS target_app,
  (
    SELECT CASE
      WHEN polished_text != '' THEN polished_text
      ELSE raw_text
    END
    FROM history h2
    WHERE h2.session_id = h.session_id
    ORDER BY h2.seq ASC LIMIT 1
  ) AS preview
FROM history h
"""


@dataclass(frozen=True)
class SegmentRecord:
    session_id: str
    seq: int
    created_at: int
    raw_text: str = ""
    polished_text: str = ""
    source: str = ""
    duration_ms: int = 0
    target_app: str = ""
    trigger_mode: str = ""
    model: str = ""


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    created_at: int
    segment_count: int
    source: str
    target_app: str
    preview: str


def _rows_to_summaries(rows: list[tuple]) -> list[SessionSummary]:
    return [
        SessionSummary(
            session_id=r[0],
            created_at=r[1],
            segment_count=r[2],
            source=r[3] or "",
            target_app=r[4] or "",
            preview=r[5] or "",
        )
        for r in rows
    ]


class HistoryStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.disabled = False
        self._queue: queue.Queue[Any] = queue.Queue()
        self._stop = object()
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._init_error: BaseException | None = None

        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            # Bootstrap schema on a short-lived connection, then hand exclusive
            # write ownership to the daemon writer thread.
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.executescript(_DDL)
                conn.execute("PRAGMA user_version=1;")
                conn.commit()
        except Exception:
            logger.exception("HistoryStore init failed; disabling history")
            self.disabled = True
            return

        self._thread = threading.Thread(
            target=self._writer_loop, name="HistoryStoreWriter", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(timeout=5.0):
            logger.error("HistoryStore writer thread failed to start")
            self.disabled = True
            return
        if self._init_error is not None:
            logger.exception(
                "HistoryStore writer connection failed; disabling history",
                exc_info=self._init_error,
            )
            self.disabled = True

    def enqueue(self, record: SegmentRecord) -> None:
        if self.disabled:
            return
        self._queue.put(("insert", record))

    def enqueue_delete_sessions(self, session_ids: list[str]) -> None:
        if self.disabled:
            return
        self._queue.put(("delete_sessions", list(session_ids)))

    def enqueue_delete_all(self) -> None:
        if self.disabled:
            return
        self._queue.put(("delete_all", None))

    def enqueue_cleanup(
        self,
        retention_days: int,
        max_entries: int,
        active_session_id: str | None,
    ) -> None:
        if self.disabled:
            return
        self._queue.put(
            ("cleanup", (retention_days, max_entries, active_session_id))
        )

    def close(self, timeout: float = 2.0) -> None:
        if self.disabled:
            return
        thread = self._thread
        if thread is None:
            return
        self._thread = None
        self._queue.put(self._stop)
        thread.join(timeout=timeout)
        if thread.is_alive():
            logger.warning(
                "HistoryStore writer did not finish within %.1fs; "
                "leaving connection with writer thread",
                timeout,
            )

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[SessionSummary]:
        if self.disabled:
            return []
        try:
            with self._readonly_conn() as conn:
                rows = conn.execute(
                    _SESSION_SUMMARY_SQL
                    + """
                    GROUP BY h.session_id
                    ORDER BY session_created DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            return _rows_to_summaries(rows)
        except Exception:
            logger.exception("HistoryStore list_sessions failed")
            return []

    def search_sessions(self, q: str) -> list[SessionSummary]:
        if self.disabled or not q:
            return []
        pattern = f"%{q}%"
        try:
            with self._readonly_conn() as conn:
                rows = conn.execute(
                    _SESSION_SUMMARY_SQL
                    + """
                    WHERE h.session_id IN (
                      SELECT DISTINCT session_id FROM history
                      WHERE raw_text LIKE ? OR polished_text LIKE ?
                    )
                    GROUP BY h.session_id
                    ORDER BY session_created DESC
                    """,
                    (pattern, pattern),
                ).fetchall()
            return _rows_to_summaries(rows)
        except Exception:
            logger.exception("HistoryStore search_sessions failed")
            return []

    def get_session_segments(self, session_id: str) -> list[SegmentRecord]:
        if self.disabled:
            return []
        try:
            with self._readonly_conn() as conn:
                rows = conn.execute(
                    """
                    SELECT session_id, seq, created_at, raw_text, polished_text,
                           source, duration_ms, target_app, trigger_mode, model
                    FROM history
                    WHERE session_id = ?
                    ORDER BY seq ASC
                    """,
                    (session_id,),
                ).fetchall()
            return [
                SegmentRecord(
                    session_id=r[0],
                    seq=r[1],
                    created_at=r[2],
                    raw_text=r[3],
                    polished_text=r[4],
                    source=r[5],
                    duration_ms=r[6],
                    target_app=r[7],
                    trigger_mode=r[8],
                    model=r[9],
                )
                for r in rows
            ]
        except Exception:
            logger.exception("HistoryStore get_session_segments failed")
            return []

    def _readonly_conn(self) -> sqlite3.Connection:
        # Short-lived read-only URI connection (WAL allows concurrent readers).
        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.execute("PRAGMA query_only=ON;")
        return conn

    def _writer_loop(self) -> None:
        conn: sqlite3.Connection | None = None
        try:
            # Writer thread exclusively owns this connection for its lifetime.
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL;")
        except Exception as exc:
            self._init_error = exc
            self._ready.set()
            return
        self._ready.set()

        try:
            while True:
                item = self._queue.get()
                if item is self._stop:
                    while True:
                        try:
                            more = self._queue.get_nowait()
                        except queue.Empty:
                            break
                        if more is self._stop:
                            continue
                        self._dispatch(conn, more)
                    return
                self._dispatch(conn, item)
        finally:
            try:
                conn.close()
            except Exception:
                logger.exception("HistoryStore writer connection close failed")

    def _dispatch(self, conn: sqlite3.Connection, item: Any) -> None:
        try:
            op, payload = item
            if op == "insert":
                self._do_insert(conn, payload)
            elif op == "delete_sessions":
                self._do_delete_sessions(conn, payload)
            elif op == "delete_all":
                self._do_delete_all(conn)
            elif op == "cleanup":
                retention_days, max_entries, active_session_id = payload
                self._do_cleanup(conn, retention_days, max_entries, active_session_id)
        except Exception:
            logger.exception("HistoryStore writer op failed")
            try:
                conn.rollback()
            except Exception:
                logger.exception("HistoryStore rollback after writer failure failed")

    def _do_insert(self, conn: sqlite3.Connection, record: SegmentRecord) -> None:
        conn.execute(
            """
            INSERT INTO history (
              session_id, seq, created_at, raw_text, polished_text,
              source, duration_ms, target_app, trigger_mode, model
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.session_id,
                record.seq,
                record.created_at,
                record.raw_text,
                record.polished_text,
                record.source,
                record.duration_ms,
                record.target_app,
                record.trigger_mode,
                record.model,
            ),
        )
        conn.commit()

    def _do_delete_sessions(self, conn: sqlite3.Connection, session_ids: list[str]) -> None:
        if not session_ids:
            return
        placeholders = ",".join("?" for _ in session_ids)
        conn.execute(
            f"DELETE FROM history WHERE session_id IN ({placeholders})",
            session_ids,
        )
        conn.commit()

    def _do_delete_all(self, conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM history")
        conn.commit()

    def _do_cleanup(
        self,
        conn: sqlite3.Connection,
        retention_days: int,
        max_entries: int,
        active_session_id: str | None,
    ) -> None:
        if retention_days > 0:
            cutoff_ms = int(time.time() * 1000 - retention_days * 86_400_000)
            rows = conn.execute(
                """
                SELECT session_id
                FROM history
                GROUP BY session_id
                HAVING MIN(created_at) < ?
                """,
                (cutoff_ms,),
            ).fetchall()
            to_delete = [r[0] for r in rows if r[0] != active_session_id]
            if to_delete:
                placeholders = ",".join("?" for _ in to_delete)
                conn.execute(
                    f"DELETE FROM history WHERE session_id IN ({placeholders})",
                    to_delete,
                )
                conn.commit()

        if max_entries > 0:
            # Delete oldest non-active sessions until within limit (ADR-0005).
            # Active session is never deleted, even if that leaves us briefly
            # unable to shrink further when only active remains.
            while True:
                rows = conn.execute(
                    """
                    SELECT session_id
                    FROM history
                    GROUP BY session_id
                    ORDER BY MIN(created_at) ASC
                    """
                ).fetchall()
                session_ids = [r[0] for r in rows]
                if len(session_ids) <= max_entries:
                    break
                victim = next(
                    (s for s in session_ids if s != active_session_id),
                    None,
                )
                if victim is None:
                    break
                conn.execute(
                    "DELETE FROM history WHERE session_id = ?",
                    (victim,),
                )
                conn.commit()
