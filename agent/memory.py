"""Memory module — chat history, user profile, long-term memory (SQLite)."""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"

SENSITIVE_KEYWORDS: list[str] = [
    "mật khẩu", "password", "token", "api key", "secret",
    "số tài khoản", "số thẻ", "cvv", "otp", "pin",
]
VALID_MEMORY_TYPES = ("path", "preference", "schedule", "personal")


class Memory:
    """SQLite: chat history, user profile, long-term memory."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Schema ────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS history (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    role       TEXT    NOT NULL,
                    content    TEXT    NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS memories (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    key        TEXT    NOT NULL,
                    value      TEXT    NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_profile (
                    id                 INTEGER PRIMARY KEY CHECK(id = 1),
                    display_name       TEXT    DEFAULT '',
                    preferred_language TEXT    DEFAULT 'vi',
                    custom_shortcuts   TEXT    DEFAULT '{}',
                    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    key             TEXT    NOT NULL,
                    value           TEXT    NOT NULL,
                    type            TEXT    NOT NULL,
                    is_active       INTEGER NOT NULL DEFAULT 1,
                    access_count    INTEGER NOT NULL DEFAULT 0,
                    relevance_score REAL    DEFAULT 0.0,
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Đảm bảo luôn có đúng một hàng trong user_profile
            conn.execute(
                "INSERT OR IGNORE INTO user_profile "
                "(id, display_name, preferred_language, custom_shortcuts) "
                "VALUES (1, '', 'vi', '{}')"
            )

    # ── Chat History ──────────────────────────────────────────────────

    def save_message(self, role: str, content: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO history (role, content) VALUES (?, ?)",
                (role, content),
            )

    def get_recent_history(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT role, content FROM history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    # ── Legacy key-value memories ─────────────────────────────────────

    def save_memory(self, key: str, value: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories (key, value) VALUES (?, ?)",
                (key, value),
            )

    def get_memory(self, key: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM memories WHERE key = ? ORDER BY id DESC LIMIT 1",
                (key,),
            ).fetchone()
        return row[0] if row else None

    # ── User Profile ──────────────────────────────────────────────────

    def get_user_profile(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM user_profile WHERE id = 1"
            ).fetchone()
        if row:
            return dict(row)
        return {"id": 1, "display_name": "", "preferred_language": "vi",
                "custom_shortcuts": "{}"}

    def save_user_profile(
        self,
        display_name: str | None = None,
        preferred_language: str | None = None,
    ) -> bool:
        """Cập nhật user profile. Trả về True nếu tên bị cắt ngắn."""
        profile = self.get_user_profile()
        truncated = False
        if display_name is not None:
            if len(display_name) > 100:
                display_name = display_name[:100]
                truncated = True
            profile["display_name"] = display_name
        if preferred_language is not None:
            profile["preferred_language"] = preferred_language
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE user_profile
                   SET display_name = ?, preferred_language = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = 1""",
                (profile["display_name"], profile["preferred_language"]),
            )
        return truncated

    # ── Long-term Memory ──────────────────────────────────────────────

    @staticmethod
    def _is_sensitive(text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in SENSITIVE_KEYWORDS)

    def save_long_term_memory(self, key: str, value: str, mem_type: str) -> bool:
        """Lưu hoặc cập nhật bộ nhớ dài hạn. Trả về True nếu lưu thành công."""
        if mem_type not in VALID_MEMORY_TYPES:
            return False
        if self._is_sensitive(key) or self._is_sensitive(value):
            return False
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM long_term_memory WHERE key = ? AND is_active = 1",
                (key,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE long_term_memory SET value = ?, "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (value, existing[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO long_term_memory (key, value, type, is_active, access_count) "
                    "VALUES (?, ?, ?, 1, 0)",
                    (key, value, mem_type),
                )
        return True

    def get_all_long_term_memories(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, key, value, type, access_count, updated_at "
                "FROM long_term_memory WHERE is_active = 1 "
                "ORDER BY type, updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def deactivate_long_term_memory(self, search_term: str) -> str | None:
        """Vô hiệu hoá bộ nhớ khớp nhất. Trả về key nếu tìm thấy."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, key, value FROM long_term_memory WHERE is_active = 1"
            ).fetchall()
        best_id: int | None = None
        best_key: str | None = None
        best_score = 0
        term = search_term.lower()
        for r in rows:
            score = 0
            if term in r["key"].lower():
                score += 2
            if term in r["value"].lower():
                score += 1
            if score > best_score:
                best_score = score
                best_id = r["id"]
                best_key = r["key"]
        if best_id and best_score > 0:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE long_term_memory SET is_active = 0 WHERE id = ?",
                    (best_id,),
                )
            return best_key
        return None

    def search_long_term_memory(
        self, keywords: list[str], limit: int = 5
    ) -> list[dict]:
        """Tìm kiếm bộ nhớ dài hạn theo từ khoá, sắp xếp theo RelevanceScore."""
        if not keywords:
            return []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, key, value, type, access_count, updated_at "
                "FROM long_term_memory WHERE is_active = 1"
            ).fetchall()

        total_kw = len(keywords)
        results: list[dict] = []
        for row in rows:
            combined = (row["key"] + " " + row["value"]).lower()
            matched = sum(1 for kw in keywords if kw.lower() in combined)
            base_score = matched / total_kw if total_kw > 0 else 0.0
            access_bonus = min(0.2, row["access_count"] * 0.01)
            try:
                updated = datetime.fromisoformat(str(row["updated_at"]))
                days_ago = (datetime.now() - updated.replace(tzinfo=None)).days
                recency_bonus = (
                    min(0.1, max(0, 7 - days_ago) * 0.01)
                    if days_ago <= 7 else 0.0
                )
            except Exception:
                recency_bonus = 0.0
            score = min(1.0, base_score + access_bonus + recency_bonus)
            results.append({**dict(row), "relevance_score": score})

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]

    def increment_access_count(self, memory_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE long_term_memory SET access_count = access_count + 1 "
                "WHERE id = ?",
                (memory_id,),
            )
