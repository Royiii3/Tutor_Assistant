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

# Add project root for imports
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from core import TutorAssistantCore
from config import UserConfig

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="家教信息筛选",
    page_icon="📚",
    layout="wide",
)


def _load_config():
    """Load config from config.json (local) or st.secrets (cloud)."""
    config_path = Path(__file__).parent / "config.json"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Override from Streamlit secrets if present
        if hasattr(st, "secrets") and st.secrets:
            for key in data:
                if key in st.secrets:
                    data[key] = st.secrets[key]
        return UserConfig(**data)

    # Cloud mode: build entirely from Streamlit secrets
    if hasattr(st, "secrets") and st.secrets:
        secrets = dict(st.secrets)
        return UserConfig(
            my_address=secrets["my_address"],
            my_coords=list(secrets["my_coords"]),
            min_salary=int(secrets["min_salary"]),
            subjects=list(secrets["subjects"]),
            grades=list(secrets["grades"]),
            max_commute_time=int(secrets["max_commute_time"]),
            commute_mode=secrets["commute_mode"],
            my_gender=secrets.get("my_gender", ""),
            my_identity=secrets.get("my_identity", ""),
            skip_districts=list(secrets["skip_districts"]),
            target_groups=list(secrets["target_groups"]),
            amap_key=secrets["amap_key"],
            deepseek_key=secrets.get("deepseek_key", ""),
            bark_key=secrets["bark_key"],
            db_key="",
            wechat_data_dir="",
        )

    raise FileNotFoundError(
        "config.json 未找到，且 Streamlit secrets 未配置。"
        "请在 Streamlit Cloud Dashboard → Settings → Secrets 中添加配置。"
    )


# ── Init session state ───────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = []
if "core" not in st.session_state:
    try:
        cfg = _load_config()
        st.session_state.core = TutorAssistantCore(config=cfg)
    except Exception as e:
        st.error(f"配置加载失败: {e}")
        st.stop()


def get_core():
    return st.session_state.core


# ── Sidebar: Config ──────────────────────────────────────────
core = get_core()
cfg = core.config

with st.sidebar:
    st.header("筛选配置")
    st.write(f"**位置**: {cfg.my_address}")
    st.write(f"**最低薪资**: {cfg.min_salary} 元/h")
    st.write(f"**科目**: {' / '.join(cfg.subjects)}")
    st.write(f"**年级**: {' / '.join(cfg.grades)}")
    st.write(f"**通勤**: ≤{cfg.max_commute_time} 分钟 ({cfg.commute_mode})")
    st.write(f"**跳过区域**: {' / '.join(cfg.skip_districts)}")
    st.write(f"**目标群**: {' / '.join(cfg.target_groups[:3])}...")

    st.divider()

    # Dev info
    st.caption("Bark 推送: " + ("已配置" if cfg.bark_key else "未配置"))
    if st.session_state.results:
        st.caption(f"上次解析: {len(st.session_state.results)} 条结果")

    st.divider()
    st.caption("部署: Streamlit Cloud 免费")
    st.caption("数据来源: 手动粘贴")

# ── Main: Input ──────────────────────────────────────────────
st.title("家教信息筛选系统")
st.caption("粘贴微信家教群消息 → 自动解析 → 筛选 → 推送到手机")

# Dynamic key to support clearing
if "clear_counter" not in st.session_state:
    st.session_state.clear_counter = 0

text_input = st.text_area(
    "粘贴微信消息",
    placeholder="在此粘贴微信家教群聊天记录...\n\n系统会自动拆分多条消息并逐条解析。\n支持混合格式：A杭州家教、欢杭、WY杭州、杭州ZN 等。",
    height=220,
    key=f"msg_input_{st.session_state.clear_counter}",
)

col1, col2, col3 = st.columns([1, 1, 6])
with col1:
    parse_btn = st.button("解析筛选", type="primary", use_container_width=True)
with col2:
    clear_btn = st.button("清空", use_container_width=True)

if clear_btn:
    st.session_state.clear_counter += 1
    st.session_state.results = []
    st.rerun()

# ── Parse logic ──────────────────────────────────────────────
if parse_btn and text_input.strip():
    with st.spinner("解析中..."):
        results = core.process_text(text_input)
        st.session_state.results = results

# ── Display results ──────────────────────────────────────────
results = st.session_state.results
if not results:
    st.info("上方粘贴消息后点击「解析筛选」")
else:
    # Stats row
    stats = {}
    for r in results:
        stats[r.status] = stats.get(r.status, 0) + 1

    labels = {
        "pushed": "已推送", "skipped": "区域跳过",
        "mismatch": "条件不符", "too_far": "通勤太远",
        "push_failed": "推送失败",
    }
    cols = st.columns(len(stats) if stats else 1)
    for i, (status, count) in enumerate(stats.items()):
        with cols[i]:
            color = {"pushed": "#34c759", "skipped": "#ff9500",
                     "mismatch": "#999", "too_far": "#ff3b30",
                     "push_failed": "#ff3b30"}.get(status, "#999")
            st.markdown(
                f"<div style='text-align:center;padding:12px;background:{color}15;"
                f"border-radius:8px;border:1px solid {color}40'>"
                f"<span style='font-size:24px;font-weight:700;color:{color}'>{count}</span><br>"
                f"<span style='font-size:12px;color:#666'>{labels.get(status, status)}</span></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # Per-job cards
    for i, r in enumerate(results):
        job = r.job
        status = r.status

        badge_color = {
            "pushed": "green", "skipped": "orange",
            "mismatch": "grey", "too_far": "red",
            "push_failed": "red",
        }.get(status, "grey")

        with st.container():
            cols = st.columns([6, 1])

            with cols[0]:
                # Title line
                title_parts = []
                if job.subjects:
                    title_parts.append(" ".join(job.subjects))
                if job.grade:
                    title_parts.append(job.grade)
                title = f"**{' · '.join(title_parts)}**" if title_parts else "**未分类**"
                st.markdown(f"### {i+1}. {title}  :{badge_color}[{labels.get(status, status)}]")

                # Details
                detail_items = []
                if job.address:
                    detail_items.append(f"**地址**: {job.address}")
                if job.salary:
                    s = f"**薪资**: {job.salary}"
                    if job.salary_max:
                        s += f"-{job.salary_max}"
                    s += " 元/h"
                    detail_items.append(s)
                if job.commute_time:
                    c = f"**通勤**: 约 {job.commute_time} 分钟"
                    if job.commute_distance:
                        c += f" ({job.commute_distance:.1f} km)"
                    detail_items.append(c)
                if job.time_requirement:
                    detail_items.append(f"**时间**: {job.time_requirement}")
                if r.reason:
                    detail_items.append(f"**原因**: {r.reason}")

                for item in detail_items:
                    st.markdown(item)

            with cols[1]:
                if status != "pushed":
                    push_key = f"push_{i}"
                    if st.button("📲 手动推送", key=push_key):
                        success = core.pusher.push(job)
                        if success:
                            st.toast(f"已推送到手机: {job.address[:20]}...", icon="✅")
                        else:
                            st.toast("推送失败，请检查 Bark 配置", icon="❌")

            st.divider()

# ── Footer ───────────────────────────────────────────────────
st.caption("Powered by Streamlit Cloud · 免费部署 · 国内可访问")
