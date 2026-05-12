"""Local paste-to-push tool — no browser needed.

Usage:
    python paste.py                     # paste in terminal, Enter, Ctrl+Z, Enter
    python paste.py file.txt            # read from file
    python paste.py --no-push           # parse only, skip push
    python paste.py --force-all         # push ALL parsed jobs (ignore filters)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core import TutorAssistantCore


def read_paste() -> str:
    """Read multi-line paste from stdin until EOF."""
    print("粘贴微信家教消息，然后：")
    print("  1. 按 Enter 换到新的一行")
    print("  2. 按 Ctrl+Z，再按 Enter")
    print("-" * 60)
    return sys.stdin.read()


def main():
    no_push = "--no-push" in sys.argv
    force_all = "--force-all" in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        path = Path(args[0])
        if path.exists():
            text = path.read_text(encoding="utf-8")
            print(f"从文件读取: {path} ({len(text)} 字符)")
        else:
            print(f"[ERROR] 文件不存在: {path}")
            sys.exit(1)
    else:
        text = read_paste()

    if not text.strip():
        print("没有内容。")
        sys.exit(0)

    print("\n" + "=" * 60)
    core = TutorAssistantCore()
    results = core.process_text(text)

    pushed = 0
    skipped = 0
    mismatch = 0
    too_far = 0
    push_failed = 0

    for i, r in enumerate(results, 1):
        job = r.job
        status = r.status

        subjects = " ".join(job.subjects) if job.subjects else "?"
        addr = (job.address or "无地址")[:30]
        salary = f"{job.salary}"
        if job.salary_max:
            salary += f"-{job.salary_max}"
        salary += "/h"

        commute_str = ""
        if job.commute_time:
            commute_str = f" | 通勤{job.commute_time}min"

        print(f"\n  [{i}] [{subjects}] {job.grade} | {addr}")
        print(f"      薪资: {salary}{commute_str}")

        if status == "pushed":
            print(f"      [PUSHED ✓]")
            pushed += 1
        elif status == "skipped":
            print(f"      [SKIPPED] {r.reason}")
            skipped += 1
        elif status == "mismatch":
            print(f"      [MISMATCH] {r.reason}")
            mismatch += 1
        elif status == "too_far":
            print(f"      [TOO FAR] {r.reason}")
            too_far += 1
        elif status == "push_failed":
            print(f"      [PUSH FAILED] Bark 推送未成功")
            push_failed += 1

        if force_all and status not in ("pushed", "push_failed"):
            print(f"      [FORCE PUSH] ", end="")
            if core.pusher.push(job):
                print("成功 ✓")
                pushed += 1
            else:
                print("失败 ✗")
                push_failed += 1

    print(f"\n{'=' * 60}")
    print(f"已推送: {pushed}  |  区域跳过: {skipped}  |  条件不符: {mismatch}")
    print(f"通勤太远: {too_far}  |  推送失败: {push_failed}")
    print(f"总计: {len(results)} 条")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
