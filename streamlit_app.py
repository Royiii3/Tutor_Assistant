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

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide only Streamlit branding, NOT the header (sidebar toggle lives there) */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stStatusWidget"] {visibility: hidden;}

/* Base */
.stApp {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                 "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f2f2f7;
}

/* Main container */
.block-container {
    max-width: 680px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #fff;
    border-right: 1px solid #e5e5ea;
}
[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem;
}

/* ── Cards ── */
.card {
    background: #fff;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 10px;
    border: 1px solid #e5e5ea;
}
.card-sm {
    background: #f9f9fb;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 8px;
    border: 1px solid #ebebf0;
}

/* ── Hero ── */
.hero {
    margin-bottom: 24px;
}
.hero h1 {
    font-size: 26px;
    font-weight: 700;
    color: #1c1c1e;
    letter-spacing: -0.02em;
    margin: 0;
    line-height: 1.2;
}
.hero p {
    font-size: 14px;
    color: #8e8e93;
    margin: 4px 0 0 0;
}

/* ── Stat pills ── */
.stat-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 20px;
}
.stat-pill {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    padding: 8px 14px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
}
.stat-pill .n {
    font-size: 20px;
    font-weight: 700;
    line-height: 1;
}

/* ── Job cards ── */
.job {
    background: #fff;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 10px;
    border: 1px solid #e5e5ea;
}
.job-head {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}
.job-idx {
    width: 26px;
    height: 26px;
    border-radius: 8px;
    background: #f2f2f7;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    color: #636366;
    flex-shrink: 0;
}
.job-title {
    font-size: 15px;
    font-weight: 600;
    color: #1c1c1e;
    flex: 1;
    min-width: 0;
}
.tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    flex-shrink: 0;
}
.tag-pushed    { background: #d4edda; color: #155724; }
.tag-skipped   { background: #fff3cd; color: #856404; }
.tag-mismatch  { background: #e9ecef; color: #6c757d; }
.tag-too_far   { background: #f8d7da; color: #721c24; }
.tag-push_fail { background: #f8d7da; color: #721c24; }

.info-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 2px 10px;
    font-size: 13px;
    line-height: 1.9;
}
.info-grid .k {
    color: #8e8e93;
    white-space: nowrap;
}
.info-grid .v {
    color: #3a3a3c;
}
.job-note {
    font-size: 12px;
    color: #aeaeb2;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid #f2f2f7;
}

/* ── Empty state ── */
.empty {
    text-align: center;
    padding: 56px 20px;
}
.empty-icon {
    font-size: 40px;
    margin-bottom: 10px;
}
.empty-text {
    font-size: 14px;
    color: #aeaeb2;
}

/* ── Section title ── */
.sec-title {
    font-size: 11px;
    font-weight: 700;
    color: #aeaeb2;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 24px 0 10px 2px;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 8px 16px !important;
    border: none !important;
    height: auto !important;
    min-height: 38px !important;
    transition: all 0.12s ease !important;
}
.stButton > button[kind="primary"] {
    background: #007aff !important;
    color: #fff !important;
}
.stButton > button[kind="primary"]:active {
    background: #0056b3 !important;
    transform: scale(0.98);
}
.stButton > button[kind="secondary"] {
    background: #f2f2f7 !important;
    color: #3a3a3c !important;
    border: 1px solid #d1d1d6 !important;
}
.stButton > button[kind="secondary"]:active {
    background: #e5e5ea !important;
    transform: scale(0.98);
}

/* ── Textarea ── */
.stTextArea textarea {
    border-radius: 12px !important;
    border: 1px solid #d1d1d6 !important;
    background: #fff !important;
    font-size: 14px !important;
    padding: 12px 14px !important;
    line-height: 1.6 !important;
}
.stTextArea textarea:focus {
    border-color: #007aff !important;
    box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.12) !important;
}

/* ── Sidebar items ── */
.sb-block {
    margin-bottom: 14px;
}
.sb-label {
    font-size: 11px;
    font-weight: 600;
    color: #aeaeb2;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 3px;
}
.sb-value {
    font-size: 14px;
    font-weight: 500;
    color: #1c1c1e;
    line-height: 1.4;
}
.sb-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
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
    st.markdown('<div style="font-size:20px;font-weight:700;color:#1c1c1e;margin-bottom:16px">家教筛选</div>',
                unsafe_allow_html=True)

    st.markdown(
        f'<div class="sb-block">'
        f'<div class="sb-label">我的位置</div>'
        f'<div class="sb-value">{cfg.my_address}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sb-grid">'
        f'<div class="sb-block"><div class="sb-label">最低时薪</div><div class="sb-value">{cfg.min_salary} 元</div></div>'
        f'<div class="sb-block"><div class="sb-label">通勤上限</div><div class="sb-value">{cfg.max_commute_time} 分钟</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sb-block">'
        f'<div class="sb-label">目标年级</div>'
        f'<div class="sb-value">{"、".join(cfg.grades)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sb-block">'
        f'<div class="sb-label">目标科目</div>'
        f'<div class="sb-value">{"、".join(cfg.subjects)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sb-block">'
        f'<div class="sb-label">跳过区域</div>'
        f'<div class="sb-value" style="font-size:13px">{"、".join(cfg.skip_districts)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<hr style="margin:16px 0;border:none;border-top:1px solid #e5e5ea">', unsafe_allow_html=True)

    keys = core.pusher.device_keys
    push_text = f"Bark · {len(keys)} 台设备" if keys else "未配置"
    push_color = "#34c759" if keys else "#ff3b30"
    st.markdown(
        f'<div class="sb-block">'
        f'<div class="sb-label">推送通道（终端）</div>'
        f'<div class="sb-value" style="color:{push_color}">{push_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<hr style="margin:16px 0;border:none;border-top:1px solid #e5e5ea">', unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center;font-size:11px;color:#c7c7cc;padding:4px 0'>"
        "手动粘贴 · 仅解析</div>",
        unsafe_allow_html=True,
    )


# ── Main ─────────────────────────────────────────────────────
st.markdown(
    '<div class="hero">'
    '<h1>家教筛选</h1>'
    '<p>粘贴群消息 · 自动拆分解析 · 匹配筛选</p>'
    '</div>',
    unsafe_allow_html=True,
)

if "clear_counter" not in st.session_state:
    st.session_state.clear_counter = 0

text_input = st.text_area(
    "消息内容",
    placeholder="将微信家教群的聊天记录粘贴到这里...\n\n支持混贴多条消息，系统会自动拆分解析。",
    height=200,
    key=f"input_{st.session_state.clear_counter}",
    label_visibility="collapsed",
)

c1, c2, _ = st.columns([1, 1, 5])
with c1:
    parse_btn = st.button("开始解析", type="primary", use_container_width=True)
with c2:
    clear_btn = st.button("清空", type="secondary", use_container_width=True)

if clear_btn:
    st.session_state.clear_counter += 1
    st.session_state.results = []
    st.rerun()

if parse_btn and text_input.strip():
    with st.spinner("解析中..."):
        st.session_state.results = core.process_text(text_input)

# ── Results ──────────────────────────────────────────────────
results = st.session_state.results

if not results:
    st.markdown(
        '<div class="empty">'
        '<div class="empty-icon"> </div>'
        '<div class="empty-text">粘贴家教消息后点击「开始解析」</div>'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    stats = {}
    for r in results:
        stats[r.status] = stats.get(r.status, 0) + 1

    tag_info = {
        "pushed":      ("已推送",   "tag-pushed",   "#d4edda"),
        "skipped":     ("已跳过",   "tag-skipped",  "#fff3cd"),
        "mismatch":    ("条件不符", "tag-mismatch", "#e9ecef"),
        "too_far":     ("通勤太远", "tag-too_far",  "#f8d7da"),
        "push_failed": ("推送失败", "tag-push_fail","#f8d7da"),
    }

    # Stats
    st.markdown('<div class="sec-title">统计</div>', unsafe_allow_html=True)
    pills = '<div class="stat-row">'
    for status, count in stats.items():
        label, _, bg = tag_info.get(status, ("", "", "#eee"))
        pills += f'<span class="stat-pill" style="background:{bg}"><span class="n">{count}</span>{label}</span>'
    pills += '</div>'
    st.markdown(pills, unsafe_allow_html=True)

    # Job list
    st.markdown('<div class="sec-title">详情</div>', unsafe_allow_html=True)

    for i, r in enumerate(results):
        job = r.job
        status = r.status
        tag_label, tag_cls, _ = tag_info.get(status, ("", "", ""))

        parts = []
        if job.subjects:
            parts.append(" ".join(job.subjects))
        if job.grade:
            parts.append(job.grade)
        title = " · ".join(parts) if parts else "未分类"

        rows = []
        if job.address:
            rows.append(("地址", job.address))
        if job.salary:
            s = f'{job.salary}'
            if job.salary_max:
                s += f'-{job.salary_max}'
            rows.append(("薪资", f"{s} 元/h"))
        if job.commute_time:
            c = f'约 {job.commute_time} 分钟'
            if job.commute_distance:
                c += f'（{job.commute_distance:.1f} km）'
            rows.append(("通勤", c))
        if job.time_requirement:
            rows.append(("时间", job.time_requirement))

        grid = ""
        for k, v in rows:
            grid += f'<span class="k">{k}</span><span class="v">{v}</span>'

        note = ""
        if r.reason:
            note = f'<div class="job-note">{r.reason}</div>'

        st.markdown(
            f'<div class="job">'
            f'<div class="job-head">'
            f'<div class="job-idx">{i+1}</div>'
            f'<div class="job-title">{title}</div>'
            f'<span class="tag {tag_cls}">{tag_label}</span>'
            f'</div>'
            f'<div class="info-grid">{grid}</div>'
            f'{note}'
            f'</div>',
            unsafe_allow_html=True,
        )

    n = len(results)
    pn = stats.get("pushed", 0)
    st.markdown(
        f"<div style='text-align:center;color:#c7c7cc;font-size:12px;margin-top:12px'>"
        f"共 {n} 条 · 已推送 {pn} 条 · 推送请使用终端 python paste.py</div>",
        unsafe_allow_html=True,
    )
