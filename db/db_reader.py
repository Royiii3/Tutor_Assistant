"""Read new messages from WeChat's local encrypted SQLite database.

Supports both WeChat 3.x (MsgStorage.db with MSG table) and
WeChat 4.x (message_0.db with message table).
"""

import re
import shutil
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class WeChatDBReader:
    """
    Connects to WeChat's encrypted message database via sqlcipher3,
    polls for new group-chat text messages, and maps wxids to
    display names.
    """

    def __init__(self, msg_db_path: str, key: str):
        self.msg_db_path = Path(msg_db_path)
        self.key = key
        self.conn = None
        self.last_local_id = 0
        self.group_names: dict[str, str] = {}
        self._temp_dir = None
        self._temp_db = None

        # Schema info — detected at connect time
        self._table = ""
        self._col_id = ""
        self._col_talker = ""
        self._col_content = ""
        self._col_time = ""

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def connect(self):
        """Open the encrypted DB, detect schema, load group names."""
        try:
            from sqlcipher3 import dbapi2 as sqlcipher
        except ImportError:
            raise RuntimeError(
                "需要 sqlcipher3 库。安装: pip install sqlcipher3\n"
                "若 Python 3.14 编译失败，可用 Python 3.12 venv。"
            )

        self.conn = self._open_db(sqlcipher)
        self._detect_schema()
        self._init_cursor()
        self._load_group_names()

        wxid = self.msg_db_path.parent.parent.parent.name
        logger.info(
            "数据库连接成功 (wxid=%s, table=%s, groups=%d)",
            wxid, self._table, len(self.group_names),
        )

    def _open_db(self, sqlcipher):
        """Try live read-only first, then temp-copy fallback."""
        # Attempt 1: read-only on live file (WAL allows concurrent readers)
        uri = self.msg_db_path.as_posix()
        conn = self._try_connect(sqlcipher, f"file:{uri}?mode=ro", uri=True)
        if conn:
            return conn

        # Attempt 2: copy to temp
        self._temp_dir = Path(tempfile.mkdtemp(prefix="wct_"))
        self._temp_db = self._temp_dir / self.msg_db_path.name
        self._refresh_copy()
        conn = self._try_connect(sqlcipher, str(self._temp_db), uri=False)
        if conn:
            return conn

        raise RuntimeError("无法连接微信数据库 — 密钥可能不正确或微信版本不支持")

    def _try_connect(self, sqlcipher, path, uri=False):
        for pragma in (
            f"PRAGMA key = \"x'{self.key}'\"",
            f"PRAGMA key = '{self.key}'",
            f"PRAGMA key = x'{self.key}'",
        ):
            try:
                conn = sqlcipher.connect(path, uri=uri)
                conn.execute(pragma)
                # Quick liveness check
                conn.execute("SELECT COUNT(*) FROM sqlite_master")
                return conn
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
        return None

    def _refresh_copy(self):
        """Copy live DB + WAL/SHM to temp."""
        shutil.copy2(self.msg_db_path, self._temp_db)
        for sfx in ("-wal", "-shm"):
            src = Path(str(self.msg_db_path) + sfx)
            if src.exists():
                shutil.copy2(src, Path(str(self._temp_db) + sfx))

    # ------------------------------------------------------------------
    # Schema detection
    # ------------------------------------------------------------------

    def _detect_schema(self):
        """Detect table/column names (WeChat 3.x vs 4.x)."""
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        tables = {r[0] for r in rows}

        # WeChat 3.x: MSG(localId, StrTalker, strContent, CreateTime, Type)
        if "MSG" in tables:
            cols = self._get_columns("MSG")
            col_set = {c[1] for c in cols}
            if "localId" in col_set and "StrTalker" in col_set:
                self._table = "MSG"
                self._col_id = "localId"
                self._col_talker = "StrTalker"
                self._col_content = "strContent"
                self._col_time = "CreateTime"
                self._col_type = "Type"
                return

        # WeChat 4.x: message(local_id, talker, content, create_time, type, …)
        if "message" in tables:
            cols = self._get_columns("message")
            col_set = {c[1] for c in cols}
            if "local_id" in col_set:
                self._table = "message"
                self._col_id = "local_id"
                self._col_talker = "talker" if "talker" in col_set else "talker_id"
                self._col_content = "content" if "content" in col_set else "message_content"
                self._col_time = "create_time" if "create_time" in col_set else "timestamp"
                self._col_type = "type" if "type" in col_set else "message_type"
                return

            # Alternative column naming
            if "localId" in col_set:
                self._table = "message"
                self._col_id = "localId"
                self._col_talker = self._find_col(col_set, ["StrTalker", "talker", "talker_id", "chat_id"])
                self._col_content = self._find_col(col_set, ["strContent", "content", "msg_content"])
                self._col_time = self._find_col(col_set, ["CreateTime", "create_time", "time"])
                self._col_type = self._find_col(col_set, ["Type", "type", "msg_type"])
                return

        # Generic fallback: scan all tables for message-like columns
        for table in tables:
            cols = self._get_columns(table)
            col_set = {c[1] for c in cols}
            if self._looks_like_message_table(col_set):
                self._table = table
                self._col_id = self._find_col(col_set, ["local_id", "localId", "id", "msg_id", "rowid"])
                self._col_talker = self._find_col(col_set, ["talker", "StrTalker", "talker_id", "chat_id", "sender_id"])
                self._col_content = self._find_col(col_set, ["content", "strContent", "msg_content", "text", "body"])
                self._col_time = self._find_col(col_set, ["create_time", "CreateTime", "timestamp", "time", "msg_time"])
                self._col_type = self._find_col(col_set, ["type", "Type", "msg_type", "message_type"])
                return

        raise RuntimeError(
            f"无法识别的数据库 schema。可用表: {tables}\n"
            "请在 GitHub 提 issue 并附上表结构信息。"
        )

    def _get_columns(self, table):
        return self.conn.execute(f"PRAGMA table_info({table})").fetchall()

    @staticmethod
    def _find_col(col_set, candidates):
        for c in candidates:
            if c in col_set:
                return c
        return candidates[0]

    @staticmethod
    def _looks_like_message_table(col_set) -> bool:
        """Heuristic: a message table has content + talker/chat columns."""
        content_hit = any(
            c in col_set for c in ("content", "strContent", "msg_content", "text", "body")
        )
        talker_hit = any(
            c in col_set for c in ("talker", "StrTalker", "talker_id", "chat_id", "sender_id")
        )
        return content_hit and talker_hit

    # ------------------------------------------------------------------
    # Group names
    # ------------------------------------------------------------------

    def _load_group_names(self):
        """Read group-chat display names from Contact table (MicroMsg.db or similar)."""
        # Try in same directory first (WeChat 4.x), then parent (WeChat 3.x)
        micro_candidates = [
            self.msg_db_path.parent / "MicroMsg.db",
            self.msg_db_path.parent.parent.parent / "MicroMsg.db",
        ]

        for micro in micro_candidates:
            if not micro.exists():
                continue

            tmp = Path(tempfile.gettempdir()) / "wct_micro_temp.db"
            try:
                from sqlcipher3 import dbapi2 as sqlcipher

                shutil.copy2(micro, tmp)
                for sfx in ("-wal", "-shm"):
                    src = Path(str(micro) + sfx)
                    if src.exists():
                        shutil.copy2(src, Path(str(tmp) + sfx))

                for pragma in (
                    f"PRAGMA key = \"x'{self.key}'\"",
                    f"PRAGMA key = '{self.key}'",
                ):
                    try:
                        conn = sqlcipher.connect(str(tmp))
                        conn.execute(pragma)

                        # Auto-detect Contact table columns
                        contact_table = "Contact"
                        contact_cols = {c[1] for c in conn.execute("PRAGMA table_info(Contact)").fetchall()}
                        if not contact_cols:
                            conn.close()
                            break

                        user_col = self._find_col(contact_cols, ["UserName", "user_name", "username"])
                        nick_col = self._find_col(contact_cols, ["NickName", "nick_name", "nickname", "display_name"])

                        rows = conn.execute(
                            f"SELECT {user_col}, {nick_col} FROM Contact WHERE Type=2"
                        ).fetchall()
                        self.group_names = {r[0]: r[1] for r in rows if r[0] and r[1]}
                        conn.close()
                        return
                    except Exception:
                        try:
                            conn.close()
                        except Exception:
                            pass
            except Exception:
                pass
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass

        logger.warning("未找到群名映射 — 群名将显示为原始 ID")

    # ------------------------------------------------------------------
    # Cursor init
    # ------------------------------------------------------------------

    def _init_cursor(self):
        try:
            row = self.conn.execute(
                f"SELECT MAX({self._col_id}) FROM {self._table}"
            ).fetchone()
            self.last_local_id = row[0] or 0
        except Exception:
            self.last_local_id = 0

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def get_new_messages(self) -> list[dict]:
        """Return new group text messages since the last call."""
        messages = []
        try:
            sql = (
                f"SELECT {self._col_id}, {self._col_talker}, {self._col_content}, "
                f"{self._col_time} "
                f"FROM {self._table} WHERE {self._col_id} > ? AND {self._col_type} = 1 "
                f"ORDER BY {self._col_id}"
            )
            rows = self.conn.execute(sql, (self.last_local_id,)).fetchall()
        except Exception:
            logger.warning("查询消息失败，尝试重新连接…")
            try:
                from sqlcipher3 import dbapi2 as sqlcipher
                self.conn = self._open_db(sqlcipher)
                self._detect_schema()
                self._init_cursor()
            except Exception:
                return []
            return []

        for row in rows:
            local_id = row[0]
            talker = row[1] or ""
            content = row[2] or ""
            create_time = row[3] or 0

            self.last_local_id = max(self.last_local_id, local_id)

            if "@chatroom" not in talker and "chatroom" not in talker.lower():
                continue

            text = self._strip_sender(content)
            if not text:
                continue

            name = self.group_names.get(talker, talker)
            messages.append({
                "text": text,
                "name": name,
                "is_group": True,
                "talker": talker,
                "time": create_time,
            })

        return messages

    @staticmethod
    def _strip_sender(content: str) -> str:
        """Group messages are prefixed with 'SenderName:\\n'. Strip that."""
        if not content:
            return ""
        m = re.match(r"^[^:：]+[：:]\n", content)
        if m:
            return content[m.end():]
        m = re.match(r"^[^:：]+[：:]", content)
        if m and len(content) > m.end() + 10:
            return content[m.end():]
        return content

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
