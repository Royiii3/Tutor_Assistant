"""WeChat message listener — DB polling with legacy fallbacks."""

import time
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class WeChatListener:
    """
    Listens for new WeChat group messages and invokes `on_message` for each.

    Strategy (tried in order):
    1. Read the local encrypted SQLite DB directly (needs sqlcipher3 + key).
    2. Legacy ComWeChatRobot DLL hook.
    3. Mock mode (no-op loop).
    """

    def __init__(
        self,
        on_message: Optional[Callable[[dict], None]] = None,
        target_groups: Optional[list[str]] = None,
        db_key: str = "",
        msg_db_path: str = "",
    ):
        self.on_message = on_message
        self.target_groups = target_groups or []
        self.db_key = db_key
        self.msg_db_path = msg_db_path
        self._running = False
        self._reader = None
        self._client = None
        self._mode = ""

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    def start(self):
        if self._start_db():
            return
        if self._start_legacy():
            return
        self._start_mock()

    def _start_db(self) -> bool:
        if not self.db_key:
            return False

        try:
            from db.key_extractor import get_msg_db_path as find_msg
        except ImportError:
            logger.warning("db 模块导入失败")
            return False

        db_path = self.msg_db_path or find_msg()
        if not db_path:
            logger.warning("未找到微信数据库目录")
            return False

        try:
            from db.db_reader import WeChatDBReader
            self._reader = WeChatDBReader(str(db_path), self.db_key)
            self._reader.connect()
        except Exception as e:
            logger.warning(f"数据库模式启动失败: {e}")
            return False

        self._mode = "db"
        self._running = True
        logger.info("监听模式: 本地数据库轮询")
        self._poll_loop()
        return True

    def _start_legacy(self) -> bool:
        try:
            from com_wechat_robot import WeChatRobot  # type: ignore
            self._client = WeChatRobot()
            self._client.start()
            self._mode = "legacy"
            self._running = True
            logger.info("监听模式: ComWeChatRobot Hook")
            self._legacy_loop()
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.warning(f"ComWeChatRobot 启动失败: {e}")
            return False

    def _start_mock(self):
        self._mode = "mock"
        self._running = True
        logger.info("监听模式: 模拟 (无消息源)")

    # ------------------------------------------------------------------
    # Loops
    # ------------------------------------------------------------------

    def _poll_loop(self):
        """DB polling (every 2 s)."""
        while self._running:
            try:
                msgs = self._reader.get_new_messages()
                for m in msgs:
                    if self._should_process(m):
                        if self.on_message:
                            self.on_message(m)
            except Exception:
                logger.exception("轮询异常")
            time.sleep(2)

    def _legacy_loop(self):
        while self._running:
            try:
                for m in self._client.get_messages():
                    if self._should_process(m):
                        if self.on_message:
                            self.on_message(m)
            except Exception:
                logger.exception("Hook 监听异常")
                time.sleep(5)

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _should_process(self, msg: dict) -> bool:
        if not msg.get("is_group"):
            return False
        if not self.target_groups:
            return True
        return msg.get("name", "") in self.target_groups

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop(self):
        self._running = False
        if self._reader:
            try:
                self._reader.close()
            except Exception:
                pass
            self._reader = None
        if self._client:
            try:
                self._client.stop()
            except Exception:
                pass
            self._client = None

    def is_connected(self) -> bool:
        return self._running

    @property
    def mode(self) -> str:
        return self._mode
