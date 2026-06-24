"""
Astra AI Database Engine — промышленная СУБД.
SQLite + FTS5 + шифрование + кэш LRU + async flush + авто-бэкапы.
"""
import sqlite3, json, datetime, shutil, sys, time, threading, hashlib, base64, os, re, zlib, logging
from pathlib import Path
from collections import OrderedDict, defaultdict
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger("Astra.DB")

# ── Путь ──
if getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS'):
    _appdata = Path(os.environ.get('APPDATA', str(Path.home() / '.astra'))) / 'AstraAI'
    DATA_DIR = _appdata / 'data'
else:
    DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR / "assistant.db")
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA_VERSION = 10
_ENCRYPT_KEY = None

# ── Шифрование (XOR + SHA256) ──
def _get_key() -> bytes:
    global _ENCRYPT_KEY
    if _ENCRYPT_KEY is None:
        raw = (__file__ + "astra::db::v3::2026").encode()
        _ENCRYPT_KEY = hashlib.sha256(raw).digest()
    return _ENCRYPT_KEY

def encrypt(text: str) -> str:
    if not text:
        return text
    try:
        data = text.encode("utf-8")
        compressed = zlib.compress(data, level=6)
        key = _get_key()
        xored = bytes(c ^ key[i % len(key)] for i, c in enumerate(compressed))
        return base64.urlsafe_b64encode(xored).decode()
    except Exception:
        return text

def decrypt(token: str) -> str:
    if not token:
        return token
    try:
        xored = base64.urlsafe_b64decode(token.encode())
        key = _get_key()
        compressed = bytes(c ^ key[i % len(key)] for i, c in enumerate(xored))
        return zlib.decompress(compressed).decode("utf-8")
    except Exception:
        return token

# ── LRU-кэш ──
class LRUCache:
    def __init__(self, capacity=500):
        self._cache = OrderedDict()
        self._capacity = capacity
        self._hits = 0
        self._misses = 0

    def get(self, key):
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def set(self, key, value):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self._capacity:
            self._cache.popitem(last=False)

    def invalidate(self, pattern=None):
        if pattern:
            self._cache = OrderedDict((k, v) for k, v in self._cache.items() if pattern not in k)
        else:
            self._cache.clear()

    def stats(self):
        total = self._hits + self._misses
        return {"size": len(self._cache), "hits": self._hits, "misses": self._misses,
                "hit_rate": round(self._hits / total, 3) if total else 1.0}

# ── Пул соединений ──
class ConnectionPool:
    def __init__(self, db_path, max_conn=4):
        self._db_path = db_path
        self._max = max_conn
        self._pool = []
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            if self._pool:
                return self._pool.pop()
        conn = self._create_conn()
        return conn

    def release(self, conn):
        with self._lock:
            if len(self._pool) < self._max:
                self._pool.append(conn)
            else:
                conn.close()

    def _create_conn(self):
        conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA cache_size=-64000")
        conn.execute("PRAGMA mmap_size=268435456")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    def close_all(self):
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()

# ── Бэкграунд-флашер ──
class AsyncFlusher:
    def __init__(self, db):
        self._db = db
        self._queue = []
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def submit(self, fn, *args, **kwargs):
        with self._lock:
            self._queue.append((fn, args, kwargs))

    def _loop(self):
        while self._running:
            batch = []
            with self._lock:
                if self._queue:
                    batch = self._queue[:50]
                    self._queue = self._queue[50:]
            if batch:
                conn = self._db.pool.acquire()
                try:
                    for fn, args, kwargs in batch:
                        fn(conn, *args, **kwargs)
                    conn.commit()
                except Exception as e:
                    logger.warning("Flush: %s", e)
                finally:
                    self._db.pool.release(conn)
            time.sleep(0.1)

    def stop(self):
        self._running = False

# ── Миграции ──
MIGRATIONS = {}

def migration(ver):
    def dec(f):
        MIGRATIONS[ver] = f
        return f
    return dec

def _has_column(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

@migration(10)
def migration_10(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memory_vectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL, vector TEXT NOT NULL,
            metadata TEXT DEFAULT '{}', created TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_vectors_key ON memory_vectors(key);
    """)
    for tbl in ("notes", "history", "reminders"):
        if not _has_column(conn, tbl, "encrypted"):
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN encrypted INTEGER DEFAULT 0")
    conn.commit()

# ─═ СХЕМА ═─
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY, text TEXT NOT NULL,
    created TEXT NOT NULL, done INTEGER DEFAULT 0,
    color TEXT DEFAULT NULL, priority INTEGER DEFAULT 0,
    encrypted INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS note_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL, color TEXT DEFAULT '#6c5ce7'
);
CREATE TABLE IF NOT EXISTS note_tag_map (
    note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES note_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL, text TEXT NOT NULL, time TEXT NOT NULL,
    session_id INTEGER DEFAULT NULL, encrypted INTEGER DEFAULT 0
);
CREATE VIRTUAL TABLE IF NOT EXISTS history_fts USING fts5(
    role, text, time, content='history', content_rowid='id',
    tokenize='unicode61'
);
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY, text TEXT NOT NULL,
    created TEXT NOT NULL, trigger_at TEXT NOT NULL,
    done INTEGER DEFAULT 0, category TEXT DEFAULT 'general',
    priority INTEGER DEFAULT 0, recurring TEXT DEFAULT NULL,
    encrypted INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS memory (
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY, value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL, ended_at TEXT DEFAULT NULL,
    message_count INTEGER DEFAULT 0,
    mood_avg TEXT DEFAULT 'neutral'
);
CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT PRIMARY KEY,
    messages INTEGER DEFAULT 0,
    commands INTEGER DEFAULT 0,
    queries INTEGER DEFAULT 0,
    voice_inputs INTEGER DEFAULT 0,
    screenshots INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS command_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL, plugin TEXT DEFAULT NULL,
    timestamp TEXT NOT NULL, duration_ms INTEGER DEFAULT 0,
    success INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS dialogue_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_text TEXT NOT NULL, response_text TEXT NOT NULL,
    rating INTEGER DEFAULT 0, timestamp TEXT NOT NULL,
    session_id INTEGER DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS mood_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mood TEXT NOT NULL, source TEXT DEFAULT 'detect',
    timestamp TEXT NOT NULL, note TEXT DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS learned_vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE NOT NULL, frequency INTEGER DEFAULT 1,
    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
    category TEXT DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS search_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL, results_count INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL, answer TEXT NOT NULL,
    category TEXT DEFAULT 'general', created TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS quick_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger TEXT UNIQUE NOT NULL, response TEXT NOT NULL,
    created TEXT NOT NULL, uses INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS plugin_config (
    plugin TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
    PRIMARY KEY (plugin, key)
);
CREATE TABLE IF NOT EXISTS memory_vectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL, vector TEXT NOT NULL,
    metadata TEXT DEFAULT '{}', created TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_time ON history(time DESC);
CREATE INDEX IF NOT EXISTS idx_reminders_trigger ON reminders(trigger_at);
CREATE INDEX IF NOT EXISTS idx_command_usage_time ON command_usage(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_mood_log_time ON mood_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_dialogue_feedback_rating ON dialogue_feedback(rating);
CREATE INDEX IF NOT EXISTS idx_vocabulary_freq ON learned_vocabulary(frequency DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_memory_vectors_key ON memory_vectors(key);
CREATE INDEX IF NOT EXISTS idx_history_session ON history(session_id);
CREATE INDEX IF NOT EXISTS idx_notes_done ON notes(done);
CREATE TRIGGER IF NOT EXISTS trg_history_delete_fts
    AFTER DELETE ON history
BEGIN
    INSERT INTO history_fts(history_fts, rowid, role, text, time)
    VALUES ('delete', OLD.id, OLD.role, OLD.text, OLD.time);
END;
CREATE TRIGGER IF NOT EXISTS trg_history_insert_fts
    AFTER INSERT ON history
BEGIN
    INSERT INTO history_fts(rowid, role, text, time)
    VALUES (NEW.id, NEW.role, NEW.text, NEW.time);
END;
CREATE TRIGGER IF NOT EXISTS trg_history_update_fts
    AFTER UPDATE ON history
BEGIN
    INSERT INTO history_fts(history_fts, rowid, role, text, time)
    VALUES ('delete', OLD.id, OLD.role, OLD.text, OLD.time);
    INSERT INTO history_fts(rowid, role, text, time)
    VALUES (NEW.id, NEW.role, NEW.text, NEW.time);
END;
"""

# ─═ ОСНОВНОЙ КЛАСС ═─
class Database:
    """Промышленная БД с кэшем, пулом, шифрованием, async-flush и авто-бэкапами."""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.pool = ConnectionPool(self.db_path, max_conn=4)
        self.cache = LRUCache(capacity=500)
        self._stats = defaultdict(int)
        self._lock = threading.Lock()

        # Инициализация
        conn = self.pool.acquire()
        try:
            conn.executescript(SCHEMA_SQL)
            self._migrate(conn)
            conn.commit()
            self._apply_runtime_pragmas(conn)
        finally:
            self.pool.release(conn)

        # Async flusher
        self._flusher = AsyncFlusher(self)

        # Backup timer (каждые 15 минут)
        self._last_backup = time.time()
        self._backup_interval = 900

        logger.info("Database ready: %s (%d tables)", self.db_path, self.table_count())

    def _apply_runtime_pragmas(self, conn):
        conn.execute("PRAGMA optimization=0x10002")
        conn.execute("PRAGMA automatic_index=ON")
        conn.execute("PRAGMA recursive_triggers=ON")

    def _migrate(self, conn):
        cur = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version")
        cur_ver = cur.fetchone()[0] or 0
        for ver in sorted(MIGRATIONS.keys()):
            if ver > cur_ver:
                try:
                    MIGRATIONS[ver](conn)
                    conn.execute(
                        "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                        (ver, datetime.datetime.now().isoformat()),
                    )
                    conn.commit()
                    logger.info("Migration %d applied", ver)
                except Exception as e:
                    logger.error("Migration %d failed: %s", ver, e)
                    raise
        if cur_ver < SCHEMA_VERSION:
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.datetime.now().isoformat()),
            )
            conn.commit()

    # ── Query Exec ──
    def execute(self, sql, params=None, use_cache=False):
        cache_key = f"{sql}:{params}" if use_cache else None
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                return cached

        conn = self.pool.acquire()
        try:
            cur = conn.execute(sql, params or ())
            result = cur.fetchall()
            if cache_key and result:
                self.cache.set(cache_key, result)
            self._stats["queries"] += 1
            return result
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("SQL: %s | params=%s | error=%s", sql[:100], params, e)
            raise
        finally:
            self.pool.release(conn)

    def execute_script(self, sql):
        conn = self.pool.acquire()
        try:
            conn.executescript(sql)
            conn.commit()
            self._stats["scripts"] += 1
        finally:
            self.pool.release(conn)

    def insert(self, table, data):
        """Вставка одной строки с авто-кешированием."""
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})"
        conn = self.pool.acquire()
        try:
            conn.execute(sql, list(data.values()))
            conn.commit()
            self.cache.invalidate(table)
            self._stats["inserts"] += 1
            return True
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("Insert %s: %s", table, e)
            return False
        finally:
            self.pool.release(conn)

    def insert_many(self, table, rows, batch_size=100):
        """Bulk insert с транзакциями."""
        if not rows:
            return True
        cols = ", ".join(rows[0].keys())
        placeholders = ", ".join("?" for _ in rows[0])
        sql = f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})"

        conn = self.pool.acquire()
        try:
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                conn.executemany(sql, [list(r.values()) for r in batch])
                conn.commit()
            self.cache.invalidate(table)
            self._stats["bulk_inserts"] += 1
            return True
        except Exception as e:
            logger.error("Bulk insert %s: %s", table, e)
            return False
        finally:
            self.pool.release(conn)

    def query(self, table, where=None, order_by=None, limit=None, offset=None):
        """Гибкий запрос с построением WHERE."""
        sql = f"SELECT * FROM {table}"
        params = []
        if where:
            clauses = []
            for k, v in where.items():
                if isinstance(v, tuple):
                    clauses.append(f"{k} {v[0]} ?")
                    params.append(v[1])
                elif v is None:
                    clauses.append(f"{k} IS NULL")
                else:
                    clauses.append(f"{k} = ?")
                    params.append(v)
            sql += " WHERE " + " AND ".join(clauses)
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"
        return self.execute(sql, params)

    def count(self, table, where=None):
        sql = f"SELECT COUNT(*) as cnt FROM {table}"
        params = []
        if where:
            clauses = [f"{k} = ?" for k in where]
            sql += " WHERE " + " AND ".join(clauses)
            params = list(where.values())
        r = self.execute(sql, params)
        return r[0]["cnt"] if r else 0

    def table_count(self):
        r = self.execute("SELECT COUNT(*) as cnt FROM sqlite_master WHERE type='table'")
        return r[0]["cnt"] if r else 0

    # ── FTS5 Full-Text Search ──
    def search(self, query, table="history_fts", limit=20):
        """Полнотекстовый поиск с подсветкой."""
        sql = f"""
            SELECT h.*, snippet({table}, 1, '<b>', '</b>', '...', 32) as highlighted
            FROM {table} fts
            JOIN history h ON fts.rowid = h.id
            WHERE {table} MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        # Подготовка запроса для FTS5
        fts_query = " OR ".join(f'"{w}"' for w in query.split() if len(w) > 1)
        if not fts_query:
            return []
        try:
            return self.execute(sql, [fts_query, limit])
        except Exception as e:
            logger.debug("FTS search: %s", e)
            return []

    # ── Шифрование ──
    def set_encrypted(self, table, record_id, text):
        """Сохраняет зашифрованный текст."""
        encrypted_text = encrypt(text)
        return self.execute(
            f"UPDATE {table} SET text = ?, encrypted = 1 WHERE id = ?",
            [encrypted_text, record_id]
        )

    def get_encrypted(self, table, record_id):
        """Читает и расшифровывает."""
        r = self.execute(f"SELECT text, encrypted FROM {table} WHERE id = ?", [record_id])
        if r:
            text = r[0]["text"]
            if r[0]["encrypted"]:
                text = decrypt(text)
            return text
        return None

    # ── Бэкапы ──
    def backup(self):
        """Создаёт резервную копию с ротацией (хранить 10 последних)."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"assistant_backup_{timestamp}.db"
        try:
            # VACUUM INTO (SQLite 3.27+)
            conn = self.pool.acquire()
            try:
                # Используем автономное копирование
                conn.execute(f"VACUUM INTO '{backup_path}'")
            except Exception:
                # Fallback: копируем файл
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                import shutil
                shutil.copy2(self.db_path, backup_path)
            finally:
                self.pool.release(conn)

            # Ротация: удаляем старые, оставляем 10
            backups = sorted(BACKUP_DIR.glob("assistant_backup_*.db"), reverse=True)
            for old in backups[10:]:
                old.unlink(missing_ok=True)

            self._last_backup = time.time()
            self._stats["backups"] += 1
            logger.info("Backup: %s", backup_path.name)
            return str(backup_path)
        except Exception as e:
            logger.error("Backup failed: %s", e)
            return None

    def list_backups(self):
        backups = sorted(BACKUP_DIR.glob("assistant_backup_*.db"), reverse=True)
        return [{"name": b.name, "size": b.stat().st_size,
                 "created": datetime.datetime.fromtimestamp(b.stat().st_mtime).isoformat()}
                for b in backups]

    def restore(self, backup_name):
        """Восстанавливает из бэкапа."""
        backup_path = BACKUP_DIR / backup_name
        if not backup_path.exists():
            return False
        try:
            self.pool.close_all()
            shutil.copy2(backup_path, self.db_path)
            logger.info("Restored: %s", backup_name)
            return True
        except Exception as e:
            logger.error("Restore failed: %s", e)
            return False

    # ── VACUUM / OPTIMIZE ──
    def optimize(self):
        """Полная оптимизация БД."""
        conn = self.pool.acquire()
        try:
            conn.execute("PRAGMA analysis_limit=400")
            conn.execute("PRAGMA optimize")
            conn.execute("REINDEX")
            conn.execute("ANALYZE")
            conn.commit()
            self._stats["optimizations"] += 1
            logger.info("Database optimized")
        finally:
            self.pool.release(conn)

    def vacuum(self):
        """Освобождает место (может быть долгим)."""
        conn = self.pool.acquire()
        try:
            conn.execute("VACUUM")
            self._stats["vacuums"] += 1
            logger.info("Database vacuumed")
        finally:
            self.pool.release(conn)

    # ── Статистика ──
    def health_check(self):
        try:
            conn = self.pool.acquire()
            try:
                conn.execute("SELECT 1")
                ver = conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
                size = Path(self.db_path).stat().st_size
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                page_count = conn.execute("PRAGMA page_count").fetchone()[0]
                page_size = conn.execute("PRAGMA page_size").fetchone()[0]
                wal_size = Path(self.db_path + "-wal").stat().st_size if Path(self.db_path + "-wal").exists() else 0
            finally:
                self.pool.release(conn)

            return {
                "status": "ok" if integrity == "ok" else "corrupt",
                "version": ver,
                "db_size_mb": round(size / 1024 / 1024, 2),
                "wal_size_mb": round(wal_size / 1024 / 1024, 2),
                "total_size_mb": round((size + wal_size) / 1024 / 1024, 2),
                "pages": page_count,
                "page_size": page_size,
                "integrity": integrity,
                "tables": self.table_count(),
                "cache": self.cache.stats(),
                "queries": self._stats["queries"],
                "inserts": self._stats["inserts"],
                "errors": self._stats["errors"],
                "backups": self._stats["backups"],
                "last_backup": datetime.datetime.fromtimestamp(self._last_backup).isoformat()
                    if self._last_backup else None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def table_stats(self):
        conn = self.pool.acquire()
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            stats = {}
            for r in rows:
                name = r[0]
                cnt = conn.execute(f"SELECT COUNT(*) as cnt FROM \"{name}\"").fetchone()[0]
                stats[name] = cnt
            return stats
        finally:
            self.pool.release(conn)

    # ── Daily rollup ──
    def log_daily(self, date_str=None):
        """Агрегирует дневную статистику."""
        if not date_str:
            date_str = datetime.date.today().isoformat()
        conn = self.pool.acquire()
        try:
            msg_count = conn.execute(
                "SELECT COUNT(*) FROM history WHERE date(time) = ?", [date_str]
            ).fetchone()[0]
            cmd_count = conn.execute(
                "SELECT COUNT(*) FROM command_usage WHERE date(timestamp) = ?", [date_str]
            ).fetchone()[0]
            conn.execute("""
                INSERT OR REPLACE INTO daily_stats (date, messages, commands)
                VALUES (?, ?, ?)
            """, [date_str, msg_count, cmd_count])
            conn.commit()
        finally:
            self.pool.release(conn)

    # ── Cleanup ──
    def close(self):
        self._flusher.stop()
        self.pool.close_all()
        self.cache.invalidate()
        logger.info("Database closed")

    # ── Stats ──
    def get_stats(self):
        return dict(self._stats)

    def reset_stats(self):
        self._stats.clear()

    # ── Backward-compat API (для assistant.py) ──
    def get_all_config(self):
        rows = self.query("config")
        return {r["key"]: r["value"] for r in rows}

    def set_config(self, key, value):
        self.insert("config", {"key": key, "value": str(value)})

    def get_history(self, limit=200):
        rows = self.query("history", order_by="id DESC", limit=limit)
        return [{"role": r["role"], "content": r["text"],
                 "time": r["time"]} for r in reversed(rows)]

    def add_history(self, role, content):
        now = datetime.datetime.now().isoformat()
        self.insert("history", {"role": role, "text": content, "time": now})

    def get_notes(self):
        rows = self.query("notes", where={"done": 0}, order_by="created DESC")
        return [{"id": r["id"], "text": r["text"], "done": bool(r["done"]),
                 "created": r["created"], "color": r["color"],
                 "priority": r["priority"]} for r in rows]

    def save_notes(self, notes):
        self.execute("DELETE FROM notes")
        if notes:
            self.insert_many("notes", [{
                "id": n.get("id", str(hash(n["text"]))),
                "text": n["text"], "created": n.get("created", datetime.datetime.now().isoformat()),
                "done": 1 if n.get("done") else 0,
                "color": n.get("color"), "priority": n.get("priority", 0),
            } for n in notes])

    def get_reminders(self):
        now = datetime.datetime.now().isoformat()
        rows = self.query("reminders", where={"done": 0}, order_by="trigger_at ASC")
        return [{"id": r["id"], "text": r["text"],
                 "created": r["created"], "trigger_at": r["trigger_at"],
                 "done": bool(r["done"]), "category": r["category"],
                 "priority": r["priority"], "recurring": r["recurring"]}
                for r in rows]

    def add_reminder(self, text, minutes):
        import uuid
        now = datetime.datetime.now()
        trigger = (now + datetime.timedelta(minutes=int(minutes))).isoformat()
        self.insert("reminders", {
            "id": str(uuid.uuid4())[:8], "text": text,
            "created": now.isoformat(), "trigger_at": trigger,
        })


# ─═ ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ═─
_instance = None

def get_db() -> Database:
    global _instance
    if _instance is None:
        _instance = Database()
    return _instance

def close_db():
    global _instance
    if _instance:
        _instance.close()
        _instance = None

# ── Compatibility alias ──
Storage = Database
