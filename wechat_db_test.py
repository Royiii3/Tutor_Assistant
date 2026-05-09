import sqlite3
import os
import glob
from pathlib import Path

def find_wechat_db_path():
    """自动查找微信数据库路径"""
    # 可能的微信数据库路径
    possible_paths = []

    # 获取用户文档目录
    documents = Path.home() / "Documents"
    if documents.exists():
        wechat_files = documents / "WeChat Files"
        if wechat_files.exists():
            # 查找所有微信账号目录
            for account_dir in wechat_files.iterdir():
                if account_dir.is_dir():
                    msg_dir = account_dir / "Msg"
                    if msg_dir.exists():
                        possible_paths.append(msg_dir)

    # 也尝试直接搜索 MsgStorage.db
    search_patterns = [
        str(Path.home() / "Documents" / "WeChat Files" / "*" / "Msg" / "MsgStorage.db"),
        str(Path.home() / "Documents" / "WeChat Files" / "*" / "Msg" / "*.db"),
    ]

    return possible_paths

def list_db_files(msg_dir):
    """列出Msg目录下的所有数据库文件"""
    print(f"\n📁 数据库目录: {msg_dir}")
    print("-" * 50)

    db_files = list(msg_dir.glob("*.db"))
    if not db_files:
        print("❌ 未找到任何 .db 文件")
        return []

    print(f"找到 {len(db_files)} 个数据库文件:\n")
    for f in db_files:
        size = f.stat().st_size
        size_str = f"{size / (1024*1024):.2f} MB" if size > 1024*1024 else f"{size / 1024:.2f} KB"
        print(f"  📄 {f.name} ({size_str})")

    return db_files

def read_msg_storage(db_path):
    """读取 MsgStorage.db 的表结构"""
    print(f"\n🔍 分析数据库: {db_path}")
    print("=" * 50)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"\n📊 数据库包含 {len(tables)} 个表:\n")
        for table in tables:
            table_name = table[0]
            print(f"  📋 {table_name}")

            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            print(f"      字段: {', '.join(col_names[:10])}{'...' if len(col_names) > 10 else ''}")

            # 如果是MSG表，显示一些数据
            if table_name == 'MSG':
                print(f"\n  📬 MSG表内容预览 (最近10条):")
                cursor.execute("""
                    SELECT localId, TalkerId, StrTalker, nStatus, nMsgSeq,
                           nOffset, strContent, CreateTime, StrTime
                    FROM MSG
                    ORDER BY CreateTime DESC
                    LIMIT 10
                """)
                rows = cursor.fetchall()

                if rows:
                    for row in rows:
                        content = row[6] if row[6] else "(空)"
                        content = content[:50] + "..." if len(content) > 50 else content
                        print(f"\n  [{row[8]}] {row[2]}")
                        print(f"    {content}")
                else:
                    print("    (暂无数据)")

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ 读取失败: {e}")
        return False

def read_micro_msg(db_path):
    """读取 MicroMsg.db"""
    print(f"\n🔍 分析数据库: {db_path}")
    print("=" * 50)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"\n📊 数据库包含 {len(tables)} 个表:")
        for table in tables[:15]:  # 只显示前15个
            print(f"  📋 {table[0]}")

        if len(tables) > 15:
            print(f"  ... 还有 {len(tables) - 15} 个表")

        # 查找群聊相关的表
        print("\n🔍 查找群聊消息表...")
        for table in tables:
            table_name = table[0].lower()
            if 'chatroom' in table_name or 'group' in table_name or 'room' in table_name:
                print(f"  发现: {table[0]}")

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ 读取失败: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 微信数据库读取测试")
    print("=" * 60)

    # 查找微信数据库路径
    print("\n1️⃣ 查找微信数据库路径...")
    msg_dirs = find_wechat_db_path()

    if not msg_dirs:
        print("❌ 未找到微信数据库目录")
        print("\n可能原因:")
        print("  - 微信PC版未安装")
        print("  - 微信PC版未登录")
        print("  - 数据库路径不在默认位置")
        return

    print(f"✅ 找到 {len(msg_dirs)} 个微信账号的数据库目录")

    # 逐个分析每个账号的数据库
    for i, msg_dir in enumerate(msg_dirs, 1):
        print(f"\n{'='*60}")
        print(f"📱 微信账号 {i}: {msg_dir.parent.name}")
        print(f"{'='*60}")

        # 列出所有db文件
        db_files = list_db_files(msg_dir)

        # 尝试读取主要的数据库文件
        for db_file in db_files:
            if 'MsgStorage' in db_file.name:
                read_msg_storage(str(db_file))
            elif 'MicroMsg' in db_file.name:
                read_micro_msg(str(db_file))

    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)
    print("\n如果能看到数据，说明可以直接读取微信数据库。")
    print("接下来可以写一个监控脚本来实时获取新消息。")

if __name__ == "__main__":
    main()
