"""Standalone WeChat DB key extractor — aggressive memory scan.

Usage:
    python extract_key.py                    # auto-scan + save to config.json
    python extract_key.py --dump-candidates  # dump all candidate keys to file
    python extract_key.py --test KEY         # test a specific key against the DB
"""

import re
import sys
import json
import shutil
import tempfile
from pathlib import Path


def find_wechat_process():
    """Try to attach to the WeChat process. Returns (pymem.Pymem, process_name)."""
    try:
        import pymem
        import pymem.exception
    except ImportError:
        print("[ERROR] pymem 未安装: pip install pymem")
        return None, None

    for name in ("Weixin.exe", "XWeChat.exe", "WeChatApp.exe"):
        try:
            pm = pymem.Pymem(name)
            print(f"[OK] 找到微信进程: {name} (PID={pm.process_id})")
            return pm, name
        except pymem.exception.ProcessNotFound:
            continue
        except Exception as e:
            print(f"[WARN] 附加 {name} 失败: {e}")
            continue

    print("[ERROR] 未找到微信进程。请确认微信正在运行。")
    print("  如果微信确实在运行，请以管理员身份运行本脚本。")
    return None, None


def scan_all_memory(pm):
    """Targeted memory scan using anchors — phone number, wxid, DB markers.

    Avoids brute-force high-entropy sampling that produces 70K+ false positives.
    """
    candidates: set[str] = set()

    # Strategy A: Weixin.dll near database markers (key often in .data section)
    print("[INFO] 策略A: 扫描 Weixin.dll 模块中的数据库标记附近…")
    _scan_modules_near_markers(pm, candidates)
    print(f"  -> {len(candidates)} 个候选")

    # Strategy B: heap memory with phone-number anchor
    print("[INFO] 策略B: 扫描堆内存中的手机号锚点…")
    _scan_heap_with_phone_anchor(pm, candidates)
    print(f"  -> {len(candidates)} 个候选")

    # Strategy C: heap memory with wxid anchor
    print("[INFO] 策略C: 扫描堆内存中的wxid锚点…")
    _scan_heap_with_wxid_anchor(pm, candidates)
    print(f"  -> {len(candidates)} 个候选")

    # Strategy D: scan heap for WCDB cached key pattern x'<hex>'
    print("[INFO] 策略D: 扫描WCDB缓存密钥模式 x'...' …")
    _scan_heap_for_wcdb_key(pm, candidates)
    print(f"  -> {len(candidates)} 个候选")

    print(f"[INFO] 共找到 {len(candidates)} 个候选密钥")
    return list(candidates)


def _scan_modules_near_markers(pm, candidates: set):
    """Scan Weixin/WeChat DLLs near known string markers (small windows only)."""
    markers = (b"MicroMsg", b"message_0", b"MsgStorage", b"xwechat_files",
               b"db_storage", b"SetDBKey", b"sqlcipher")

    modules = list(pm.list_modules())
    for i, mod in enumerate(modules):
        name_lower = mod.name.lower()
        if not any(kw in name_lower for kw in ("weixin", "wechat", "wmp")):
            continue
        size = mod.SizeOfImage
        if size < 4096 or size > 500 * 1024 * 1024:
            continue

        print(f"  扫描模块: {mod.name} ({size / 1024 / 1024:.1f} MB)")
        try:
            data = pm.read_bytes(mod.lpBaseOfDll, size)
        except Exception:
            continue

        for marker in markers:
            pos = 0
            while True:
                idx = data.find(marker, pos)
                if idx < 0:
                    break
                pos = idx + len(marker)
                start = max(0, idx - 4096)
                end = min(len(data), idx + 4096)
                _extract_hex_candidates(data[start:end], candidates)

        for m in re.finditer(rb"wxid_[a-z0-9]+", data):
            start = max(0, m.start() - 4096)
            end = min(len(data), m.end() + 4096)
            _extract_hex_candidates(data[start:end], candidates)


def _scan_heap_with_phone_anchor(pm, candidates: set):
    """Enumerate heap regions, search for 11-digit phone numbers as anchors."""
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("PartitionId", wintypes.WORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    MEM_COMMIT = 0x1000
    MEM_PRIVATE = 0x20000
    PAGE_READWRITE = 4

    address = 0
    region_count = 0
    phone_hits = 0

    while True:
        mbi = MEMORY_BASIC_INFORMATION()
        result = kernel32.VirtualQueryEx(
            pm.process_handle, ctypes.c_void_p(address),
            ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if result == 0:
            break

        if (mbi.State == MEM_COMMIT
                and mbi.Type == MEM_PRIVATE
                and mbi.Protect & PAGE_READWRITE
                and 4096 < mbi.RegionSize < 200 * 1024 * 1024):
            region_count += 1

            try:
                data = pm.read_bytes(mbi.BaseAddress, mbi.RegionSize)
            except Exception:
                address = mbi.BaseAddress + mbi.RegionSize
                continue

            # Chinese mobile: 1[3-9] followed by 9 digits
            for m in re.finditer(rb"(?<!\d)(1[3-9]\d{9})(?!\d)", data):
                phone_hits += 1
                start = max(0, m.start() - 4096)
                end = min(len(data), m.end() + 4096)
                _extract_hex_candidates(data[start:end], candidates)

        address = mbi.BaseAddress + mbi.RegionSize

    print(f"    扫描了 {region_count} 个堆区域，{phone_hits} 个手机号命中")


def _scan_heap_with_wxid_anchor(pm, candidates: set):
    """Enumerate heap regions, search for wxid_ patterns as anchors."""
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("PartitionId", wintypes.WORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    MEM_COMMIT = 0x1000
    MEM_PRIVATE = 0x20000
    PAGE_READWRITE = 4

    address = 0
    wxid_hits = 0

    while True:
        mbi = MEMORY_BASIC_INFORMATION()
        result = kernel32.VirtualQueryEx(
            pm.process_handle, ctypes.c_void_p(address),
            ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if result == 0:
            break

        if (mbi.State == MEM_COMMIT
                and mbi.Type == MEM_PRIVATE
                and mbi.Protect & PAGE_READWRITE
                and 4096 < mbi.RegionSize < 200 * 1024 * 1024):
            try:
                data = pm.read_bytes(mbi.BaseAddress, mbi.RegionSize)
            except Exception:
                address = mbi.BaseAddress + mbi.RegionSize
                continue

            for m in re.finditer(rb"wxid_[a-z0-9]+", data):
                wxid_hits += 1
                start = max(0, m.start() - 4096)
                end = min(len(data), m.end() + 4096)
                _extract_hex_candidates(data[start:end], candidates)

        address = mbi.BaseAddress + mbi.RegionSize

    print(f"    扫描了堆区域，{wxid_hits} 个wxid命中")


def _scan_heap_for_wcdb_key(pm, candidates: set):
    """Scan heap for WCDB's cached key pattern: x'<96 hex chars>'"""
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("PartitionId", wintypes.WORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    MEM_COMMIT = 0x1000
    MEM_PRIVATE = 0x20000
    PAGE_READWRITE = 4

    address = 0
    hits = 0

    while True:
        mbi = MEMORY_BASIC_INFORMATION()
        result = kernel32.VirtualQueryEx(
            pm.process_handle, ctypes.c_void_p(address),
            ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if result == 0:
            break

        if (mbi.State == MEM_COMMIT
                and mbi.Type == MEM_PRIVATE
                and mbi.Protect & PAGE_READWRITE
                and 4096 < mbi.RegionSize < 200 * 1024 * 1024):
            try:
                data = pm.read_bytes(mbi.BaseAddress, mbi.RegionSize)
            except Exception:
                address = mbi.BaseAddress + mbi.RegionSize
                continue

            pos = 0
            while True:
                idx = data.find(b"x'", pos)
                if idx < 0:
                    break
                pos = idx + 2

                end = min(len(data), idx + 102)
                chunk = data[idx:end]

                m = re.match(rb"x'([0-9a-fA-F]{64,96})'", chunk)
                if m:
                    hits += 1
                    candidates.add(m.group(1).lower().decode("ascii"))

        address = mbi.BaseAddress + mbi.RegionSize

    print(f"    x'...' 模式命中: {hits}")


def _extract_hex_candidates(data: bytes, candidates: set):
    """Extract hex key candidates from a byte buffer.

    WeChat 4.x / WCDB caches keys in memory as:
      x'<64hex_key><32hex_salt>'   (100 bytes total)
    """
    text = data.decode("latin-1", errors="replace")
    # WCDB cached key: x'<96 hex chars>'
    for m in re.finditer(r"x'([0-9a-fA-F]{96})'", text):
        candidates.add(m.group(1).lower())
    # Bare 96-char hex (key + salt combined)
    for m in re.finditer(r"[0-9a-fA-F]{96}", text):
        candidates.add(m.group().lower())
    # Bare 64-char hex (just the key)
    for m in re.finditer(r"[0-9a-fA-F]{64}", text):
        candidates.add(m.group().lower())
    # Shorter keys (legacy)
    for m in re.finditer(r"[0-9a-fA-F]{32}", text):
        candidates.add(m.group().lower())


def find_msg_db():
    """Locate the WeChat message database."""
    from db.key_extractor import get_msg_db_path

    # Try with the configured data dir first
    config_path = Path("config.json")
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            override = cfg.get("wechat_data_dir", "")
            if override:
                db = get_msg_db_path(data_dir_override=override)
                if db:
                    return db
        except Exception:
            pass

    return get_msg_db_path()


def test_key(db_path, key):
    """Test if a key can decrypt the database.

    WeChat 4.x / WCDB requires specific PRAGMA settings:
      cipher_compatibility = 3, cipher_page_size = 4096.
    Without these, even the correct key will be rejected.
    """
    try:
        from sqlcipher3 import dbapi2 as sqlcipher
    except ImportError:
        print("[ERROR] sqlcipher3 未安装: pip install sqlcipher3")
        return None

    tmp = Path(tempfile.gettempdir()) / "wct_extract_test.db"
    try:
        shutil.copy2(db_path, tmp)
        for sfx in ("-wal", "-shm"):
            src = Path(str(db_path) + sfx)
            if src.exists():
                shutil.copy2(src, Path(str(tmp) + sfx))

        # (key_pragma, cipher_compat, page_size) combinations
        tests = []

        if len(key) == 96:
            tests.append((f"PRAGMA key = \"x'{key}'\"", 3, 4096))

        if len(key) == 64:
            tests.append((f"PRAGMA key = \"x'{key}'\"", 3, 4096))
            tests.append((f"PRAGMA key = \"x'{key}'\"", None, 4096))

        if len(key) == 32:
            tests.append((f"PRAGMA key = \"x'{key}'\"", 3, 4096))

        tests.append((f"PRAGMA key = \"x'{key}'\"", 3, 4096))
        tests.append((f"PRAGMA key = x'{key}'", 3, 4096))

        for key_pragma, compat, page_size in tests:
            try:
                conn = sqlcipher.connect(str(tmp))
                conn.execute(key_pragma)
                if compat is not None:
                    conn.execute(f"PRAGMA cipher_compatibility = {compat}")
                if page_size is not None:
                    conn.execute(f"PRAGMA cipher_page_size = {page_size}")
                try:
                    conn.execute("SELECT COUNT(*) FROM MSG")
                except Exception:
                    try:
                        conn.execute("SELECT COUNT(*) FROM message")
                    except Exception:
                        raise
                conn.close()
                return True
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
        return False
    except Exception:
        return False
    finally:
        try:
            tmp.unlink(missing_ok=True)
            for sfx in ("-wal", "-shm"):
                p = Path(str(tmp) + sfx)
                p.unlink(missing_ok=True)
        except Exception:
            pass


def save_key_to_config(key):
    """Write the key to config.json."""
    config_path = Path("config.json")
    if not config_path.exists():
        print("[WARN] config.json 不存在，无法保存密钥")
        return

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    cfg["db_key"] = key
    config_path.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[OK] 密钥已保存到 config.json -> db_key = {key[:8]}…")


def main():
    print("=" * 60)
    print("WeChat DB 密钥提取工具")
    print("=" * 60)

    # --test mode
    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        if idx + 1 < len(sys.argv):
            key = sys.argv[idx + 1]
            db = find_msg_db()
            if not db:
                print("[ERROR] 未找到微信数据库")
                return
            print(f"测试密钥: {key}")
            print(f"数据库:   {db}")
            if test_key(db, key):
                print("[OK] 密钥有效！")
                save_key_to_config(key)
            else:
                print("[FAIL] 密钥无效")
        return

    # Find database
    db = find_msg_db()
    if not db:
        print("[ERROR] 未找到微信数据库文件")
        print("  请在 config.json 中设置 wechat_data_dir 指向 xwechat_files 目录")
        return
    print(f"[OK] 数据库: {db}")

    # Find process
    pm, name = find_wechat_process()
    if pm is None:
        print()
        print("=" * 60)
        print("备选方案：手动提取密钥")
        print("=" * 60)
        print()
        print("方法 A — SharpWxDump (C# 工具):")
        print("  1. 下载: https://github.com/AdminTest0/SharpWxDump")
        print("  2. 编译或下载 release 中的 SharpWxDump.exe")
        print("  3. 管理员终端运行: SharpWxDump.exe")
        print("  4. 会输出类似: 密钥: a1b2c3... 这样的 64 位 hex 字符串")
        print("  5. 运行: python extract_key.py --test <密钥>")
        print()
        print("方法 B — 在线工具:")
        print("  搜索 'WeChat DB key extractor' 或 '微信数据库密钥提取'")
        print("  用工具提取后执行: python extract_key.py --test <密钥>")
        print()
        print("方法 C — 命令行直接测试:")
        print("  如果你知道密钥，直接: python extract_key.py --test <密钥>")
        return

    # Scan memory
    candidates = scan_all_memory(pm)

    # --dump-candidates mode
    if "--dump-candidates" in sys.argv:
        dump_path = Path("key_candidates.txt")
        dump_path.write_text("\n".join(candidates), encoding="utf-8")
        print(f"[INFO] 候选密钥已保存到 {dump_path}")
        print(f"  可以用 python extract_key.py --test <key> 逐个测试")
        return

    # Test candidates
    print(f"[INFO] 开始测试 {len(candidates)} 个候选密钥…")
    for i, key in enumerate(candidates):
        if i > 0 and i % 100 == 0:
            print(f"  进度: {i}/{len(candidates)} …")
        if test_key(db, key):
            print(f"\n[SUCCESS] 找到有效密钥: {key}")
            save_key_to_config(key)
            # Also cache
            cache_path = Path.home() / ".wechat_tutor_dbkey"
            cache_path.write_text(key)
            print(f"[OK] 密钥已缓存到 {cache_path}")
            return

    print(f"\n[FAIL] 测试了 {len(candidates)} 个候选，未找到有效密钥")
    print("这说明密钥格式可能与预期不同。")
    print()
    print("备选方案：")
    print("  1. 用 SharpWxDump 或其他工具提取密钥")
    print("  2. 运行: python extract_key.py --test <提取到的密钥>")


if __name__ == "__main__":
    main()
