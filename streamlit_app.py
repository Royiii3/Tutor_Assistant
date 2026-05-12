"""Streamlit web app for tutor job filtering system.

Usage:
    streamlit run streamlit_app.py                    # local run
    streamlit run streamlit_app.py --server.port 8080 # custom port

Deploy for free on Streamlit Community Cloud:
    1. Create a private GitHub repository with the project files
    2. Visit https://share.streamlit.io → "New app"
    3. Connect GitHub repo, set main file: streamlit_app.py
    4. Add secrets in the dashboard (see .streamlit/secrets.example.toml)
    5. Deploy — free HTTPS URL, accessible from China

Security note:
    config.json contains API keys — DO NOT commit it to a public repo.
    Use Streamlit secrets for cloud deployment instead.
    For local use, config.json works normally.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from core import TutorAssistantCore
from config import UserConfig

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="家教筛选",
    page_icon=" ",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Global CSS — iOS 26 Liquid Glass ─────────────────────────
st.markdown("""
<style>
    /* ── Reset Streamlit defaults ── */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 2rem; max-width: 720px;}

    /* ── Base ── */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                     "SF Pro Text", "Helvetica Neue", "PingFang SC",
                     "Microsoft YaHei", sans-serif;
        background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 50%, #fff5f5 100%);
    }

    /* ── Sidebar — frosted glass ── */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.55) !important;
        backdrop-filter: blur(40px) saturate(180%);
        -webkit-backdrop-filter: blur(40px) saturate(180%);
        border-right: 1px solid rgba(255, 255, 255, 0.5) !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] p {
        font-size: 13px !important;
        color: #444 !important;
        line-height: 1.6 !important;
    }

    /* ── Glass card ── */
    .glass {
        background: rgba(255, 255, 255, 0.45);
        backdrop-filter: blur(30px) saturate(150%);
        -webkit-backdrop-filter: blur(30px) saturate(150%);
        border: 1px solid rgba(255, 255, 255, 0.6);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04),
                    0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .glass-sm {
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(20px) saturate(150%);
        -webkit-backdrop-filter: blur(20px) saturate(150%);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 16px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
    }

    /* ── Title ── */
    .hero-title {
        font-size: 34px;
        font-weight: 700;
        color: #1a1a2e;
        letter-spacing: -0.03em;
        line-height: 1.1;
        margin-bottom: 6px;
    }
    .hero-sub {
        font-size: 15px;
        color: #8e8ea0;
        font-weight: 400;
        margin-bottom: 28px;
    }

    /* ── Stat pill ── */
    .stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 18px;
        border-radius: 14px;
        margin-right: 8px;
        margin-bottom: 8px;
        font-size: 14px;
        font-weight: 600;
    }
    .stat-pill .num {
        font-size: 22px;
        font-weight: 700;
        line-height: 1;
    }

    /* ── Job card ── */
    .job-card {
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(24px) saturate(160%);
        -webkit-backdrop-filter: blur(24px) saturate(160%);
        border: 1px solid rgba(255, 255, 255, 0.55);
        border-radius: 18px;
        padding: 20px 22px;
        margin-bottom: 14px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04),
                    0 1px 3px rgba(0, 0, 0, 0.02);
        transition: box-shadow 0.2s ease, transform 0.2s ease;
    }
    .job-card:hover {
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.07),
                    0 2px 6px rgba(0, 0, 0, 0.03);
        transform: translateY(-1px);
    }

    .job-top {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
    }
    .job-num {
        width: 30px;
        height: 30px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 700;
        flex-shrink: 0;
        background: rgba(0, 0, 0, 0.04);
        color: #555;
    }
    .job-name {
        font-size: 16px;
        font-weight: 600;
        color: #1a1a2e;
        flex: 1;
    }
    .job-tag {
        padding: 3px 12px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 500;
        flex-shrink: 0;
    }
    .tag-pushed    { background: rgba(52, 199, 89, 0.12);  color: #1b8a3e; }
    .tag-skipped   { background: rgba(255, 149, 0, 0.12);  color: #c27600; }
    .tag-mismatch  { background: rgba(0, 0, 0, 0.05);     color: #888;    }
    .tag-too_far   { background: rgba(255, 59, 48, 0.10);  color: #c0392b; }
    .tag-push_fail { background: rgba(255, 59, 48, 0.10);  color: #c0392b; }

    .job-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 4px 20px;
        font-size: 13px;
        color: #555;
        line-height: 2;
    }
    .job-grid .lbl {
        color: #aaa;
        font-size: 12px;
    }
    .job-note {
        font-size: 12px;
        color: #b0b0b0;
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid rgba(0,0,0,0.04);
    }

    /* ── Sidebar glass items ── */
    .sb-item {
        background: rgba(255,255,255,0.5);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 10px;
        border: 1px solid rgba(255,255,255,0.5);
    }
    .sb-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #aaa;
        margin-bottom: 4px;
    }
    .sb-value {
        font-size: 14px;
        font-weight: 600;
        color: #333;
    }
    .sb-row {
        display: flex;
        gap: 10px;
    }
    .sb-row .sb-item { flex: 1; }

    /* ── Empty state ── */
    .empty-wrap {
        text-align: center;
        padding: 48px 20px;
    }
    .empty-circle {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: rgba(255,255,255,0.5);
        backdrop-filter: blur(20px);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 16px;
        font-size: 36px;
    }
    .empty-msg {
        font-size: 15px;
        color: #b0b0b0;
    }

    /* ── Section label ── */
    .sec-label {
        font-size: 12px;
        font-weight: 600;
        color: #b0b0b0;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 28px 0 14px 4px;
    }

    /* ── Buttons — rounded, iOS style ── */
    .stButton > button {
        border-radius: 14px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 24px !important;
        border: none !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 24px rgba(99, 102, 241, 0.4) !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.6) !important;
        color: #555 !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(0,0,0,0.06) !important;
    }

    /* ── Textarea — glass style ── */
    .stTextArea textarea {
        border-radius: 16px !important;
        border: 1px solid rgba(0,0,0,0.06) !important;
        background: rgba(255,255,255,0.5) !important;
        backdrop-filter: blur(10px) !important;
        font-size: 14px !important;
        padding: 14px 16px !important;
    }
    .stTextArea textarea:focus {
        border-color: rgba(99, 102, 241, 0.4) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-top-color: #6366f1 !important;
    }

    /* ── Divider ── */
    hr {
        border: none !important;
        border-top: 1px solid rgba(0,0,0,0.05) !important;
        margin: 8px 0 !important;
    }

    /* ── Sidebar title ── */
    [data-testid="stSidebar"] h3 {
        font-size: 15px !important;
        font-weight: 700 !important;
        color: #1a1a2e !important;
        margin-bottom: 4px !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Load config ──────────────────────────────────────────────
def _load_config():
    config_path = Path(__file__).parent / "config.json"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if hasattr(st, "secrets") and st.secrets:
            for key in data:
                if key in st.secrets:
                    data[key] = st.secrets[key]
        return UserConfig(**data)

    if hasattr(st, "secrets") and st.secrets:
        s = dict(st.secrets)
        return UserConfig(
            my_address=s["my_address"], my_coords=list(s["my_coords"]),
            min_salary=int(s["min_salary"]), subjects=list(s["subjects"]),
            grades=list(s["grades"]), max_commute_time=int(s["max_commute_time"]),
            commute_mode=s["commute_mode"], my_gender=s.get("my_gender", ""),
            my_identity=s.get("my_identity", ""), skip_districts=list(s["skip_districts"]),
            target_groups=list(s["target_groups"]), amap_key=s["amap_key"],
            deepseek_key=s.get("deepseek_key", ""), bark_key=s["bark_key"],
            db_key="", wechat_data_dir="",
        )

    raise FileNotFoundError("配置未加载")


# ── Init ─────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = []
if "core" not in st.session_state:
    try:
        st.session_state.core = TutorAssistantCore(config=_load_config())
    except Exception as e:
        st.error(f"配置加载失败: {e}")
        st.stop()


def get_core():
    return st.session_state.core


# ── Sidebar ──────────────────────────────────────────────────
core = get_core()
cfg = core.config

with st.sidebar:
    st.markdown("###  家教筛选")

    st.markdown(
        f'<div class="sb-item">'
        f'<div class="sb-label">我的位置</div>'
        f'<div class="sb-value">{cfg.my_address}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sb-row">'
        f'<div class="sb-item"><div class="sb-label">最低时薪</div>'
        f'<div class="sb-value">{cfg.min_salary} 元</div></div>'
        f'<div class="sb-item"><div class="sb-label">通勤上限</div>'
        f'<div class="sb-value">{cfg.max_commute_time} min</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sb-item">'
        f'<div class="sb-label">目标年级</div>'
        f'<div class="sb-value">{"、".join(cfg.grades)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sb-item">'
        f'<div class="sb-label">目标科目</div>'
        f'<div class="sb-value">{"、".join(cfg.subjects)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sb-item">'
        f'<div class="sb-label">跳过区域</div>'
        f'<div class="sb-value" style="font-size:12px">{"、".join(cfg.skip_districts)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    keys = core.pusher.device_keys
    push_status = f"{len(keys)} 台设备" if keys else "未配置"
    push_color = "#1b8a3e" if keys else "#c0392b"
    st.markdown(
        f'<div class="sb-item">'
        f'<div class="sb-label">推送通道（终端使用）</div>'
        f'<div class="sb-value" style="color:{push_color}">Bark · {push_status}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;font-size:11px;color:#ccc;padding:8px 0'>"
        "Streamlit Cloud · 仅解析模式</div>",
        unsafe_allow_html=True,
    )


# ── Main ─────────────────────────────────────────────────────
st.markdown('<div class="hero-title">家教筛选</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">粘贴群消息 · 自动拆分解析 · 匹配筛选</div>', unsafe_allow_html=True)

# Input
if "clear_counter" not in st.session_state:
    st.session_state.clear_counter = 0

text_input = st.text_area(
    "消息内容",
    placeholder="将微信家教群的聊天记录粘贴到这里...\n\n支持混贴多条消息，系统会自动拆分解析。",
    height=200,
    key=f"input_{st.session_state.clear_counter}",
    label_visibility="collapsed",
)

c1, c2, _ = st.columns([1, 1, 4])
with c1:
    parse_btn = st.button("开始解析", type="primary", use_container_width=True)
with c2:
    clear_btn = st.button("清空", use_container_width=True)

if clear_btn:
    st.session_state.clear_counter += 1
    st.session_state.results = []
    st.rerun()

# Parse
if parse_btn and text_input.strip():
    with st.spinner("解析中..."):
        st.session_state.results = core.process_text(text_input)

# ── Results ──────────────────────────────────────────────────
results = st.session_state.results

if not results:
    st.markdown(
        '<div class="empty-wrap">'
        '<div class="empty-circle"> </div>'
        '<div class="empty-msg">粘贴家教消息后点击「开始解析」</div>'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    stats = {}
    for r in results:
        stats[r.status] = stats.get(r.status, 0) + 1

    tag_cfg = {
        "pushed":      ("已推送",   "tag-pushed",   "rgba(52,199,89,0.10)"),
        "skipped":     ("已跳过",   "tag-skipped",  "rgba(255,149,0,0.10)"),
        "mismatch":    ("条件不符", "tag-mismatch", "rgba(0,0,0,0.04)"),
        "too_far":     ("通勤太远", "tag-too_far",  "rgba(255,59,48,0.08)"),
        "push_failed": ("推送失败", "tag-push_fail","rgba(255,59,48,0.08)"),
    }

    # Stat pills
    st.markdown('<div class="sec-label">统计</div>', unsafe_allow_html=True)
    pills = ""
    for status, count in stats.items():
        label, _, bg = tag_cfg.get(status, ("", "", "rgba(0,0,0,0.04)"))
        pills += (
            f'<span class="stat-pill" style="background:{bg}">'
            f'<span class="num">{count}</span>{label}</span>'
        )
    st.markdown(pills, unsafe_allow_html=True)

    # Job cards
    st.markdown('<div class="sec-label">详情</div>', unsafe_allow_html=True)

    for i, r in enumerate(results):
        job = r.job
        status = r.status
        tag_label, tag_cls, _ = tag_cfg.get(status, ("", "", ""))

        title_parts = []
        if job.subjects:
            title_parts.append(" ".join(job.subjects))
        if job.grade:
            title_parts.append(job.grade)
        title = " · ".join(title_parts) if title_parts else "未分类"

        grid = []
        if job.address:
            grid.append(f'<span><span class="lbl">地址</span>{job.address}</span>')
        if job.salary:
            s = f'{job.salary}'
            if job.salary_max:
                s += f'-{job.salary_max}'
            grid.append(f'<span><span class="lbl">薪资</span>{s} 元/h</span>')
        if job.commute_time:
            c = f'约 {job.commute_time} 分钟'
            if job.commute_distance:
                c += f'（{job.commute_distance:.1f} km）'
            grid.append(f'<span><span class="lbl">通勤</span>{c}</span>')
        if job.time_requirement:
            grid.append(f'<span><span class="lbl">时间</span>{job.time_requirement}</span>')

        grid_html = "\n".join(grid)
        note_html = ""
        if r.reason:
            note_html = f'<div class="job-note">{r.reason}</div>'

        st.markdown(
            f'<div class="job-card">'
            f'<div class="job-top">'
            f'<div class="job-num">{i+1}</div>'
            f'<div class="job-name">{title}</div>'
            f'<span class="job-tag {tag_cls}">{tag_label}</span>'
            f'</div>'
            f'<div class="job-grid">{grid_html}</div>'
            f'{note_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Summary
    total = len(results)
    pushed_n = stats.get("pushed", 0)
    st.markdown(
        f"<div style='text-align:center;color:#c0c0c0;font-size:12px;margin-top:16px'>"
        f"共 {total} 条 · 已推送 {pushed_n} 条 · 推送请使用终端 python paste.py</div>",
        unsafe_allow_html=True,
    )
