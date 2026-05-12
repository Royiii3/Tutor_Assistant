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

# ── Global CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}

    /* Base font */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Helvetica Neue", "PingFang SC", "Microsoft YaHei",
                     sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #fafafa;
        border-right: 1px solid #eee;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdown"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdown"] h3 {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #1a1a1a !important;
        letter-spacing: -0.01em;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] p {
        font-size: 13px !important;
        color: #555 !important;
        line-height: 1.6 !important;
    }

    /* Main title */
    .main-title {
        font-size: 28px;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 4px;
        letter-spacing: -0.02em;
    }
    .main-subtitle {
        font-size: 14px;
        color: #888;
        margin-bottom: 24px;
    }

    /* Stat cards */
    .stat-card {
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 8px;
    }
    .stat-num {
        font-size: 28px;
        font-weight: 700;
        line-height: 1;
    }
    .stat-label {
        font-size: 12px;
        margin-top: 4px;
        opacity: 0.7;
    }

    /* Job card */
    .job-card {
        background: #fff;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
        transition: box-shadow 0.15s ease;
    }
    .job-card:hover {
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }
    .job-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
    }
    .job-num {
        width: 28px;
        height: 28px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 600;
        flex-shrink: 0;
    }
    .job-title {
        font-size: 16px;
        font-weight: 600;
        color: #1a1a1a;
    }
    .job-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        margin-left: auto;
        flex-shrink: 0;
    }
    .badge-pushed    { background: #e8f5e9; color: #2e7d32; }
    .badge-skipped   { background: #fff3e0; color: #e65100; }
    .badge-mismatch  { background: #f5f5f5; color: #757575; }
    .badge-too_far   { background: #fce4ec; color: #c62828; }
    .badge-push_fail { background: #fce4ec; color: #c62828; }

    .job-details {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px 24px;
        font-size: 13px;
        color: #555;
    }
    .job-details span {
        line-height: 1.8;
    }
    .detail-label {
        color: #999;
        margin-right: 6px;
    }
    .job-reason {
        font-size: 12px;
        color: #999;
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid #f0f0f0;
    }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #bbb;
    }
    .empty-icon {
        font-size: 48px;
        margin-bottom: 12px;
    }
    .empty-text {
        font-size: 14px;
    }

    /* Section header */
    .section-header {
        font-size: 13px;
        font-weight: 600;
        color: #999;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin: 24px 0 12px 0;
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


# ── Sidebar ──────────────────────────────────────────────────
core = get_core()
cfg = core.config

with st.sidebar:
    st.markdown("###  ")
    st.markdown(f"**{cfg.my_address}**")

    st.markdown("---")

    st.markdown("####  筛选规则")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**{cfg.min_salary}元+**")
        st.caption("最低时薪")
    with col_b:
        st.markdown(f"**≤{cfg.max_commute_time}min**")
        st.caption(f"{cfg.commute_mode}")

    st.markdown(f"**{'、'.join(cfg.grades)}**")
    st.caption("目标年级")

    st.markdown(f"**{'、'.join(cfg.subjects[:4])}{'等' if len(cfg.subjects) > 4 else ''}**")
    st.caption("目标科目")

    st.markdown("---")

    st.markdown("####  推送通道")
    keys = core.pusher.device_keys
    if keys:
        st.markdown(f"Bark · {len(keys)} 台设备")
        if st.button("发送测试通知", use_container_width=True, key="test_bark"):
            import requests as req
            from urllib.parse import quote
            try:
                url = f"https://api.day.app/{keys[0]}/{quote('测试')}/{quote('收到即配置成功')}"
                r = req.get(url, timeout=100)
                if r.json().get("code") == 200:
                    st.toast("已发送，请查看手机")
                else:
                    st.toast(f"返回异常: {r.json()}")
            except Exception as ex:
                st.toast(f"发送失败: {ex}")
    else:
        st.markdown("<span style='color:#c62828'>未配置</span>", unsafe_allow_html=True)
        st.caption("在 Secrets 中设置 bark_key")

    st.markdown("---")
    st.markdown(f"<div style='font-size:11px;color:#ccc'>Streamlit Cloud · 手动粘贴模式</div>",
                unsafe_allow_html=True)


# ── Main area ────────────────────────────────────────────────
st.markdown('<div class="main-title">家教筛选</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">粘贴群消息，自动解析匹配，一键推送到手机</div>', unsafe_allow_html=True)

# Input area
if "clear_counter" not in st.session_state:
    st.session_state.clear_counter = 0

text_input = st.text_area(
    "消息内容",
    placeholder="将微信家教群的聊天记录粘贴到这里...\n\n支持混贴多条消息，系统会自动拆分解析。",
    height=200,
    key=f"input_{st.session_state.clear_counter}",
    label_visibility="collapsed",
)

col_btn1, col_btn2, col_spacer = st.columns([1, 1, 4])
with col_btn1:
    parse_btn = st.button("开始解析", type="primary", use_container_width=True)
with col_btn2:
    clear_btn = st.button("清空", use_container_width=True)

if clear_btn:
    st.session_state.clear_counter += 1
    st.session_state.results = []
    st.rerun()

# ── Parse ────────────────────────────────────────────────────
if parse_btn and text_input.strip():
    with st.spinner("正在解析..."):
        st.session_state.results = core.process_text(text_input)

# ── Results ──────────────────────────────────────────────────
results = st.session_state.results

if not results:
    st.markdown(
        '<div class="empty-state">'
        '<div class="empty-icon"> </div>'
        '<div class="empty-text">粘贴家教消息后点击「开始解析」</div>'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    # Stats
    stats = {}
    for r in results:
        stats[r.status] = stats.get(r.status, 0) + 1

    status_cfg = {
        "pushed":      ("  已推送",   "#e8f5e9", "#2e7d32"),
        "skipped":     ("  跳过",     "#fff3e0", "#e65100"),
        "mismatch":    ("  不符",     "#f5f5f5", "#757575"),
        "too_far":     ("  太远",     "#fce4ec", "#c62828"),
        "push_failed": ("  失败", "#fce4ec", "#c62828"),
    }

    st.markdown('<div class="section-header">解析结果</div>', unsafe_allow_html=True)

    stat_cols = st.columns(len(stats) if stats else 1)
    for i, (status, count) in enumerate(stats.items()):
        label, bg, fg = status_cfg.get(status, ("", "#f5f5f5", "#999"))
        with stat_cols[i]:
            st.markdown(
                f'<div class="stat-card" style="background:{bg}">'
                f'<div class="stat-num" style="color:{fg}">{count}</div>'
                f'<div class="stat-label" style="color:{fg}">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-header">详细信息</div>', unsafe_allow_html=True)

    # Job cards
    for i, r in enumerate(results):
        job = r.job
        status = r.status
        label, _, _ = status_cfg.get(status, ("", "", ""))
        badge_cls = f"badge-{status}"

        title_parts = []
        if job.subjects:
            title_parts.append(" ".join(job.subjects))
        if job.grade:
            title_parts.append(job.grade)
        title = " · ".join(title_parts) if title_parts else "未分类"

        # Build details grid
        details = []
        if job.address:
            details.append(f'<span><span class="detail-label">地址</span>{job.address}</span>')
        if job.salary:
            s = f'{job.salary}'
            if job.salary_max:
                s += f'-{job.salary_max}'
            s += ' 元/h'
            details.append(f'<span><span class="detail-label">薪资</span>{s}</span>')
        if job.commute_time:
            c = f'约 {job.commute_time} 分钟'
            if job.commute_distance:
                c += f'（{job.commute_distance:.1f} km）'
            details.append(f'<span><span class="detail-label">通勤</span>{c}</span>')
        if job.time_requirement:
            details.append(f'<span><span class="detail-label">时间</span>{job.time_requirement}</span>')

        details_html = "\n".join(details)
        reason_html = ""
        if r.reason:
            reason_html = f'<div class="job-reason">{r.reason}</div>'

        # Push button
        push_html = ""
        if status not in ("pushed",):
            push_html = f'<div style="margin-top:12px"><a href="#" style="font-size:13px;color:#1976d2;text-decoration:none">  手动推送</a></div>'

        st.markdown(
            f'<div class="job-card">'
            f'<div class="job-header">'
            f'<div class="job-num" style="background:#f5f5f5;color:#666">{i+1}</div>'
            f'<div class="job-title">{title}</div>'
            f'<span class="job-badge {badge_cls}">{label}</span>'
            f'</div>'
            f'<div class="job-details">{details_html}</div>'
            f'{reason_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Push button (real Streamlit button under the card)
        if status not in ("pushed",):
            if st.button("  推送到手机", key=f"push_{i}", type="secondary"):
                try:
                    if core.pusher.push(job):
                        st.toast(f"已推送: {job.address[:20]}...")
                    else:
                        st.toast("推送失败，请检查 Bark 配置")
                except Exception as ex:
                    st.toast(f"异常: {ex}")

        # Small spacer between cards
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Summary footer
    total = len(results)
    pushed_n = stats.get("pushed", 0)
    if pushed_n > 0:
        st.markdown(
            f"<div style='text-align:center;color:#888;font-size:12px;margin-top:20px'>"
            f"共 {total} 条 · 已推送 {pushed_n} 条</div>",
            unsafe_allow_html=True,
        )
