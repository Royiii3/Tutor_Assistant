import sys
import logging
from core import TutorAssistantCore
from wechat_listener import WeChatListener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TutorAssistant:
    def __init__(self, config_path: str = "config.json"):
        self.core = TutorAssistantCore(config_path)
        self.config = self.core.config

    def process_message(self, msg: dict):
        text = msg.get("text", "")
        group = msg.get("name", "")
        logger.info(f"收到群[{group}]消息: {text[:50]}...")

        results = self.core.process_text(text, source=group)

        for result in results:
            if result.status == "pushed":
                logger.info(f"[PUSHED] {result.job.address[:30]}...")
            elif result.status == "skipped":
                logger.info(f"[SKIPPED] {result.reason}")
            elif result.status == "mismatch":
                logger.info(f"[MISMATCH] {result.reason}")
            elif result.status == "too_far":
                logger.info(f"[TOO_FAR] {result.reason}")

    def _resolve_db_key(self) -> str:
        if self.config.db_key:
            return self.config.db_key
        try:
            from db.key_extractor import find_key, get_msg_db_path
            data_dir = getattr(self.config, "wechat_data_dir", "")
            db_path = get_msg_db_path(data_dir_override=data_dir)
            if db_path:
                key = find_key(str(db_path))
                if key:
                    logger.info("自动获取数据库密钥成功")
                    return key
        except Exception as e:
            logger.debug(f"密钥自动获取异常: {e}")
        return ""

    def _resolve_msg_db_path(self) -> str:
        try:
            from db.key_extractor import get_msg_db_path
            data_dir = getattr(self.config, "wechat_data_dir", "")
            p = get_msg_db_path(data_dir_override=data_dir)
            return str(p) if p else ""
        except Exception:
            return ""

    def run(self):
        logger.info("家教助手启动...")
        self.core.print_config()

        db_key = self._resolve_db_key()
        msg_db_path = self._resolve_msg_db_path()

        if db_key:
            logger.info(f"数据库密钥: {db_key[:8]}..., 路径: {msg_db_path}")
        else:
            logger.warning("未获取到数据库密钥")
            logger.warning("可能原因:")
            logger.warning("  1) pymem 未安装: pip install pymem")
            logger.warning("  2) 微信未运行 (需要微信在线才能提取密钥)")
            logger.warning("  3) 密钥提取失败 (可手动填入 config.json 的 db_key)")
            logger.warning("  4) sqlcipher3 未安装: pip install sqlcipher3")
            if not msg_db_path:
                logger.warning("  5) 未找到微信数据库目录")
                logger.warning("     WeChat 4.x 路径: <WeChat安装目录>/xwechat_files/<wxid>/db_storage/message/")
                logger.warning("     可在 config.json 设置 wechat_data_dir 手动指定")
                logger.warning("→ 将尝试 ComWeChatRobot Hook / 模拟模式")

        listener = WeChatListener(
            on_message=self.process_message,
            target_groups=self.config.target_groups,
            db_key=db_key,
            msg_db_path=msg_db_path,
        )

        try:
            listener.start()
            if listener.mode == "mock":
                logger.warning("所有消息源均不可用，系统处于模拟模式，不会收到实际消息")
        except KeyboardInterrupt:
            logger.info("收到退出信号，正在停止...")
            listener.stop()


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    app = TutorAssistant(config_path)
    app.run()
