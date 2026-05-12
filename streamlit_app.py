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
st.set_page_config(page_title="家教筛选", page_icon=" ", layout="centered")

# ── Minimal CSS ──────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {max-width: 660px; padding-top: 1.2rem;}
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
    st.header("筛选规则")

    st.write(f"**位置**  {cfg.my_address}")

    col1, col2 = st.columns(2)
    col1.metric("最低时薪", f"{cfg.min_salary} 元")
    col2.metric("通勤上限", f"{cfg.max_commute_time} min")

    st.write(f"**年级**  {'、'.join(cfg.grades)}")
    st.write(f"**科目**  {'、'.join(cfg.subjects)}")
    st.write(f"**跳过**  {'、'.join(cfg.skip_districts)}")


# ── Main ─────────────────────────────────────────────────────
st.title("家教筛选")
st.caption("粘贴群消息，自动拆分解析，匹配筛选")

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
    parse_btn = st.button("解析", type="primary", use_container_width=True)
with c2:
    clear_btn = st.button("清空", use_container_width=True)

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
    st.info("粘贴家教消息后点击「解析」")
else:
    stats = {}
    for r in results:
        stats[r.status] = stats.get(r.status, 0) + 1

    status_label = {
        "pushed": "已推送", "skipped": "已跳过",
        "mismatch": "条件不符", "too_far": "通勤太远",
        "push_failed": "推送失败",
    }

    # Stats row
    cols = st.columns(max(len(stats), 1))
    for i, (status, count) in enumerate(stats.items()):
        with cols[i]:
            st.metric(status_label.get(status, status), count)

    st.divider()

    # Job cards
    for i, r in enumerate(results):
        job = r.job
        status = r.status

        parts = []
        if job.subjects:
            parts.append(" ".join(job.subjects))
        if job.grade:
            parts.append(job.grade)
        title = " · ".join(parts) if parts else "未分类"
        tag = status_label.get(status, status)

        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                st.markdown(f"**{i+1}. {title}**")
            with right:
                st.caption(tag)

            lines = []
            if job.address:
                lines.append(f"地址 {job.address}")
            if job.salary:
                s = f"{job.salary}"
                if job.salary_max:
                    s += f"-{job.salary_max}"
                lines.append(f"薪资 {s} 元/h")
            if job.commute_time:
                c = f"约 {job.commute_time} 分钟"
                if job.commute_distance:
                    c += f"（{job.commute_distance:.1f} km）"
                lines.append(f"通勤 {c}")
            if job.time_requirement:
                lines.append(f"时间 {job.time_requirement}")
            if r.reason:
                lines.append(f"原因 {r.reason}")

            st.markdown("  ".join(lines))

    st.caption(f"共 {len(results)} 条 · 推送请使用终端 python paste.py")
