"""Extract WeChat database encryption key and locate the message DB.

Supports both WeChat 3.x (Documents/WeChat Files/<wxid>/Msg/MsgStorage.db)
and WeChat 4.x (<install>/xwechat_files/<wxid>/db_storage/message/message_0.db).
"""

import re
import os
import shutil
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_PATH = Path.home() / ".wechat_tutor_dbkey"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_key(msg_db_path: str) -> str | None:
    """
    Find the WeChat DB encryption key. Tries, in order:
    1. Cached key from a previous successful extraction.
    2. Memory scan via pymem (reads key from running WeChat process).
    3. Known derivation methods (older WeChat versions).
    Returns None if all methods fail.
    """
    db_path = Path(msg_db_path)
    if not db_path.exists():
        logger.error(f"数据库文件不存在: {msg_db_path}")
        return None

    key = _read_cached()
    if key and _test_key(db_path, key):
        logger.info("使用缓存的数据库密钥")
        return key

    key = _extract_from_memory(db_path)
    if key:
        _write_cached(key)
        logger.info("密钥已缓存到 %s", CACHE_PATH)
        return key

    key = _try_derived_keys(db_path)
    if key:
        _write_cached(key)
        return key

    # The above methods all failed — give the user clear guidance
    logger.warning("=" * 50)
    logger.warning("自动提取密钥失败。手动获取密钥的方法：")
    logger.warning("")
    logger.warning("方法1 — 用工具提取（推荐）：")
    logger.warning("  下载 SharpWxDump 或类似工具，从微信进程内存中提取密钥")
    logger.warning("  得到密钥后填入 config.json 的 db_key 字段")
    logger.warning("")
    logger.warning("方法2 — 给 pymem 管理员权限：")
    logger.warning("  以管理员身份运行终端，再执行 python main.py")
    logger.warning("=" * 50)

    return None


def get_msg_db_path(data_dir_override: str = "") -> Path | None:
    """
    Locate the WeChat message database on this machine.

    WeChat 4.x: <install>/xwechat_files/<wxid>/db_storage/message/message_0.db
    WeChat 3.x: Documents/WeChat Files/<wxid>/Msg/MsgStorage.db
    """
    if data_dir_override:
        p = _find_msg_db_in(Path(data_dir_override))
        if p:
            return p

    # 1) Try registry-derived install path
    install_root = _get_wechat_install_from_registry()
    if install_root:
        for sub in ("xwechat_files", "WeChat Files"):
            d = install_root / sub
            if d.exists():
                p = _find_msg_db_in(d) if sub == "xwechat_files" else _find_msg_db_in_legacy(d)
                if p:
                    return p

    # 2) Try process-derived path
    proc_root = _get_wechat_install_from_process()
    if proc_root:
        for sub in ("xwechat_files", "WeChat Files"):
            d = proc_root / sub
            if d.exists():
                p = _find_msg_db_in(d) if sub == "xwechat_files" else _find_msg_db_in_legacy(d)
                if p:
                    return p

    # 3) Search common data roots
    for base in _common_data_roots():
        p = _find_msg_db_in(base) if "xwechat" in base.name else _find_msg_db_in_legacy(base)
        if p:
            return p

    # 4) Broad search: scan Tencent directories for xwechat_files
    for base in _broad_search_roots():
        for found in _walk_for_xwechat(base, depth=3):
            p = _find_msg_db_in(found)
            if p:
                return p

    return None


def _broad_search_roots() -> list[Path]:
    """Candidate parent directories to walk for xwechat_files."""
    roots = []
    for drive in ("C:/", "D:/", "E:/", "F:/"):
        for parent in (
            "Tencent",
            "Tencent/WeChat",
            "Program Files/Tencent",
            "Program Files (x86)/Tencent",
        ):
            p = Path(drive) / parent
            if p.exists():
                roots.append(p)

    appdata = os.environ.get("APPDATA", "")
    if appdata:
        tencent = Path(appdata) / "Tencent"
        if tencent.exists():
            roots.append(tencent)

    localappdata = os.environ.get("LOCALAPPDATA", "")
    if localappdata:
        tencent = Path(localappdata) / "Tencent"
        if tencent.exists():
            roots.append(tencent)

    docs = Path.home() / "Documents"
    if docs.exists():
        roots.append(docs)

    return roots


def _walk_for_xwechat(root: Path, depth: int) -> list[Path]:
    """Walk `root` up to `depth` levels looking for xwechat_files directories."""
    found = []
    try:
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            if entry.name == "xwechat_files":
                found.append(entry)
            elif depth > 1:
                found.extend(_walk_for_xwechat(entry, depth - 1))
    except (PermissionError, OSError):
        pass
    return found


def get_wxid() -> str | None:
    """Return the WeChat user ID (wxid_xxx) found on this machine."""
    for root in _all_possible_roots():
        for d in sorted(root.iterdir()):
            if d.is_dir() and 'wxid_' in d.name:
                if (d / "db_storage" / "message").exists() or (d / "Msg").exists():
                    return d.name
    return None


# ---------------------------------------------------------------------------
# Path discovery helpers
# ---------------------------------------------------------------------------

def _find_msg_db_in(root: Path) -> Path | None:
    """Search a root directory for WeChat 4.x message_0.db files."""
    if not root.exists():
        return None
    for d in sorted(root.iterdir()):
        if not d.is_dir() or 'wxid_' not in d.name:
            continue
        msg_dir = d / "db_storage" / "message"
        if msg_dir.exists():
            db = msg_dir / "message_0.db"
            if db.exists():
                return db
    return None


def _find_msg_db_in_legacy(root: Path) -> Path | None:
    """Search a root directory for WeChat 3.x MsgStorage.db files."""
    if not root.exists():
        return None
    for d in sorted(root.iterdir()):
        if not d.is_dir() or 'wxid_' not in d.name:
            continue
        msg_dir = d / "Msg"
        if msg_dir.exists():
            db = msg_dir / "MsgStorage.db"
            if db.exists():
                return db
            multi = msg_dir / "Multi"
            if multi.exists():
                dbs = sorted(multi.glob("MSG*.db"))
                if dbs:
                    return dbs[-1]
    return None


def _all_possible_roots() -> list[Path]:
    roots: list[Path] = []
    install = _get_wechat_install_from_registry()
    if install:
        roots.append(install / "xwechat_files")
    roots.extend(_common_data_roots())
    proc = _get_wechat_install_from_process()
    if proc:
        roots.append(proc / "xwechat_files")
    docs_wf = Path.home() / "Documents" / "WeChat Files"
    if docs_wf.exists():
        roots.append(docs_wf)
    return roots


def _common_data_roots() -> list[Path]:
    """Return paths to search for xwechat_files or WeChat Files."""
    candidates = []

    # WeChat 4.x data dir — same level as xwechat_files
    for drive in ("C:/", "D:/", "E:/", "F:/"):
        for sub in (
            "Tencent/WeChat/WeChat",
            "Program Files/Tencent/WeChat",
            "Program Files (x86)/Tencent/WeChat",
        ):
            p = Path(drive) / sub / "xwechat_files"
            if p.exists():
                candidates.append(p)

    appdata = os.environ.get("APPDATA", "")
    if appdata:
        for sub in ("Tencent/WeChat", "Tencent/WeChat/WeChat"):
            p = Path(appdata) / sub / "xwechat_files"
            if p.exists():
                candidates.append(p)

    localappdata = os.environ.get("LOCALAPPDATA", "")
    if localappdata:
        for sub in ("Tencent/WeChat", "Tencent/WeChat/WeChat"):
            p = Path(localappdata) / sub / "xwechat_files"
            if p.exists():
                candidates.append(p)

    docs = Path.home() / "Documents"
    candidates.append(docs / "xwechat_files")
    candidates.append(docs / "WeChat Files")

    return [c for c in candidates if c.exists()]


def _get_wechat_install_from_registry() -> Path | None:
    """Read WeChat install path from Windows Registry."""
    try:
        import winreg
    except ImportError:
        return None
    for hkey, path in [
        (winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat"),
        (winreg.HKEY_CURRENT_USER, r"Software\Tencent\XWeChat"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Tencent\WeChat"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Tencent\XWeChat"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Tencent\WeChat"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Tencent\XWeChat"),
    ]:
        try:
            key = winreg.OpenKey(hkey, path)
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            p = Path(install_path)
            if p.exists():
                return p
        except OSError:
            pass
    return None


def _get_wechat_install_from_process() -> Path | None:
    """Get WeChat.exe directory by querying the running process."""
    try:
        import pymem
        pm = None
        for name in ("Weixin.exe", "WeChatApp.exe", "WeChat.exe"):
            try:
                pm = pymem.Pymem(name)
                break
            except Exception:
                continue
        if pm is None:
            return None
        pid = pm.process_id
    except Exception:
        return None

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        PROCESS_QUERY_LIMITED_INFO = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFO, False, pid)
        if not handle:
            return None

        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            kernel32.CloseHandle(handle)
            exe = Path(buf.value)
            return exe.parent
        kernel32.CloseHandle(handle)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Memory extraction — anchor-based targeted scanning
# ---------------------------------------------------------------------------
#
# WeChat 4.x stores the DB encryption key as a 64-char hex string (32 bytes)
# in process memory. Instead of brute-force scanning all memory (which produces
# 70K+ false positives from high-entropy sampling), we use three targeted
# strategies:
#
#  A) Scan Weixin.dll near database filename references (key often in .data section)
#  B) Scan heap memory with phone-number anchor (key near user-info struct)
#  C) Scan heap memory with wxid anchor (fallback)
#
# This reduces candidates from ~70K to typically < 200.

def _extract_from_memory(db_path: Path) -> str | None:
    try:
        import pymem
        import pymem.exception
    except ImportError:
        logger.info("pymem 未安装 (pip install pymem)")
        return None

    pm = None
    for name in ("Weixin.exe", "WeChatApp.exe"):
        try:
            pm = pymem.Pymem(name)
            logger.info("找到微信进程: %s (PID=%d)", name, pm.process_id)
            break
        except pymem.exception.ProcessNotFound:
            continue
        except Exception as e:
            logger.warning("附加 %s 失败: %s", name, e)
            continue

    if pm is None:
        logger.warning("未找到微信进程。请确认微信正在运行。")
        logger.warning("如果微信确实在运行，请以管理员身份运行终端。")
        return None

    logger.info("正在从微信内存搜索数据库密钥（锚点定位法）…")

    candidates: set[str] = set()

    # Strategy A: Weixin.dll near database markers
    _scan_modules_near_markers(pm, candidates)
    logger.info("  模块标记扫描: %d 个候选", len(candidates))

    # Strategy B: heap memory with phone-number anchor
    _scan_heap_with_phone_anchor(pm, candidates)
    logger.info("  堆内存手机号锚点: %d 个候选", len(candidates))

    # Strategy C: heap memory with wxid anchor
    _scan_heap_with_wxid_anchor(pm, candidates)
    logger.info("  堆内存wxid锚点: %d 个候选", len(candidates))

    # Strategy D: scan heap for WCDB cached key pattern: x'<hex>'
    _scan_heap_for_wcdb_key(pm, candidates)
    logger.info("  WCDB缓存密钥模式: %d 个候选", len(candidates))

    logger.info("扫描完成，候选密钥 %d 个，开始测试…", len(candidates))

    for i, key in enumerate(sorted(candidates)):
        if i > 0 and i % 50 == 0:
            logger.info("  已测试 %d/%d …", i, len(candidates))
        if _test_key(db_path, key):
            logger.info("有效密钥: %s…", key[:8])
            return key

    logger.warning("已测试全部 %d 个候选，未找到有效密钥", len(candidates))
    return None


def _scan_modules_near_markers(pm, candidates: set):
    """Scan Weixin.dll and related modules near known string markers.

    Only reads small windows (~4KB) around each marker hit instead of the
    entire module. Skips high-entropy sampling entirely.
    """
    markers = (b"MicroMsg", b"message_0", b"MsgStorage", b"xwechat_files",
               b"db_storage", b"SetDBKey", b"sqlcipher")

    for mod in pm.list_modules():
        name_lower = mod.name.lower()
        if not any(kw in name_lower for kw in ("weixin", "wechat", "wmp")):
            continue
        size = mod.SizeOfImage
        if size < 4096 or size > 500 * 1024 * 1024:
            continue

        # Read only the .data/.rdata sections by scanning with markers
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

        # Also try wxid pattern in module data
        for m in re.finditer(rb"wxid_[a-z0-9]+", data):
            start = max(0, m.start() - 4096)
            end = min(len(data), m.end() + 4096)
            _extract_hex_candidates(data[start:end], candidates)


def _scan_heap_with_phone_anchor(pm, candidates: set):
    """Enumerate heap regions and search for 11-digit phone number anchors.

    WeChat 4.x stores user info (including phone number) in a C++ struct
    on the heap. The DB key lives nearby. Searching for \d{11} patterns
    in MEM_PRIVATE regions and extracting nearby hex strings is highly
    selective — typically < 100 candidates.
    """
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

            # Search for 11-digit phone numbers (Chinese mobile)
            for m in re.finditer(rb"(?<!\d)(1[3-9]\d{9})(?!\d)", data):
                phone_hits += 1
                start = max(0, m.start() - 4096)
                end = min(len(data), m.end() + 4096)
                _extract_hex_candidates(data[start:end], candidates)

        address = mbi.BaseAddress + mbi.RegionSize

    logger.info("    扫描了 %d 个堆区域，%d 个手机号命中",
                region_count, phone_hits)


def _scan_heap_with_wxid_anchor(pm, candidates: set):
    """Enumerate heap regions and search for wxid_ patterns as anchors."""
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
    region_count = 0

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

            for m in re.finditer(rb"wxid_[a-z0-9]+", data):
                wxid_hits += 1
                start = max(0, m.start() - 4096)
                end = min(len(data), m.end() + 4096)
                _extract_hex_candidates(data[start:end], candidates)

        address = mbi.BaseAddress + mbi.RegionSize

    logger.info("    扫描了 %d 个堆区域，%d 个wxid命中",
                region_count, wxid_hits)


def _scan_heap_for_wcdb_key(pm, candidates: set):
    """Scan heap memory for WCDB's cached key pattern: x'<96 hex chars>'

    WCDB caches the database key in process memory in the exact format
    used by the PRAGMA statement. Searching for the 'x'' byte sequence
    and validating the following bytes is highly selective.
    """
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

            # Search for x' hex-encoded key pattern
            pos = 0
            while True:
                idx = data.find(b"x'", pos)
                if idx < 0:
                    break
                pos = idx + 2

                # Try to read up to 100 hex chars + closing quote
                end = min(len(data), idx + 102)
                chunk = data[idx:end]

                # Validate: x' + hex(96) + '  or  x' + hex(64) + '
                m = re.match(rb"x'([0-9a-fA-F]{64,96})'", chunk)
                if m:
                    hits += 1
                    candidates.add(m.group(1).lower().decode("ascii"))

        address = mbi.BaseAddress + mbi.RegionSize

    logger.info("    x'...' 模式命中: %d", hits)


def _extract_hex_candidates(data: bytes, candidates: set):
    """Extract hex key candidates from a byte buffer.

    WeChat 4.x / WCDB caches keys in memory as:
      x'<64hex_key><32hex_salt>'   (100 bytes total)
    The hex part is 96 chars (64 key + 32 salt). We also extract bare
    64-char keys and 96-char blobs.
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


# ---------------------------------------------------------------------------
# Derived keys (legacy WeChat versions)
# ---------------------------------------------------------------------------

def _try_derived_keys(db_path: Path) -> str | None:
    wxid = get_wxid()
    if not wxid:
        return None
    import hashlib

    for raw in (wxid, wxid + "test", wxid.replace("wxid_", "")):
        h = hashlib.md5(raw.encode()).hexdigest()
        if _test_key(db_path, h):
            return h
        h2 = hashlib.md5(h.encode()).hexdigest()
        if _test_key(db_path, h2):
            return h2
    return None


# ---------------------------------------------------------------------------
# Key testing
# ---------------------------------------------------------------------------

def _test_key(db_path: Path, key: str) -> bool:
    """Test a candidate key against the database.

    WeChat 4.x / WCDB uses SQLCipher with non-standard settings:
      - PRAGMA cipher_compatibility = 3
      - PRAGMA cipher_page_size = 4096
      - Key may be 64-char hex (32-byte raw key) or 96-char hex (key + salt)

    Without cipher_compatibility, even the correct key will be rejected.
    """
    tmp = Path(tempfile.gettempdir()) / "wct_key_test.db"
    try:
        try:
            from sqlcipher3 import dbapi2 as sqlcipher
        except ImportError:
            return False

        shutil.copy2(db_path, tmp)
        for sfx in ("-wal", "-shm"):
            src = Path(str(db_path) + sfx)
            if src.exists():
                shutil.copy2(src, Path(str(tmp) + sfx))

        # Build a list of (key_expr, cipher_compat, page_size) combinations
        tests = []

        # For 96-char keys (64key+32salt combined), use directly as hex blob
        if len(key) == 96:
            tests.append((f"PRAGMA key = \"x'{key}'\"", 3, 4096))

        # For 64-char keys (32 bytes), try as raw key
        if len(key) == 64:
            tests.append((f"PRAGMA key = \"x'{key}'\"", 3, 4096))
            # Also try without cipher_compatibility (SQLCipher 4 default)
            tests.append((f"PRAGMA key = \"x'{key}'\"", None, 4096))

        # For 32-char keys (legacy)
        if len(key) == 32:
            tests.append((f"PRAGMA key = \"x'{key}'\"", 3, 4096))

        # Generic tests for any length
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
                # Probe: try both WeChat 3.x and 4.x table names
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


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _read_cached() -> str | None:
    if CACHE_PATH.exists():
        try:
            return CACHE_PATH.read_text().strip()
        except Exception:
            pass
    return None


def _write_cached(key: str):
    try:
        CACHE_PATH.write_text(key)
    except Exception:
        pass
