"""Web interface for tutor job filtering system.

Usage:
    python web_app.py                    # local dev on http://127.0.0.1:5000
    python web_app.py --host 0.0.0.0     # accessible from LAN
    python web_app.py --port 8080         # custom port

Deploy on cloud server:
    pip install gunicorn
    gunicorn -b 0.0.0.0:5000 web_app:app
"""

import sys
import json
import logging
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Lazy init
_core = None


def get_core():
    global _core
    if _core is None:
        from core import TutorAssistantCore
        _core = TutorAssistantCore()
    return _core


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>家教信息筛选</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #f5f5f5; color: #333; padding: 16px; max-width: 800px; margin: 0 auto; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .subtitle { color: #888; font-size: 13px; margin-bottom: 16px; }
  textarea { width: 100%; height: 200px; padding: 12px; border: 1px solid #ddd;
             border-radius: 8px; font-size: 14px; resize: vertical; font-family: inherit; }
  .btn-row { display: flex; gap: 8px; margin: 12px 0; }
  button { padding: 10px 24px; border: none; border-radius: 8px; font-size: 15px;
           cursor: pointer; font-weight: 600; }
  .btn-parse { background: #007aff; color: #fff; }
  .btn-parse:hover { background: #0056cc; }
  .btn-clear { background: #e5e5e5; color: #333; }
  .btn-clear:hover { background: #ccc; }
  .config { background: #fff; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;
            font-size: 13px; color: #666; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .config strong { color: #333; }
  .result { background: #fff; border-radius: 8px; padding: 16px; margin-top: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .job { border-bottom: 1px solid #eee; padding: 12px 0; }
  .job:last-child { border-bottom: none; }
  .job-header { display: flex; justify-content: space-between; align-items: center;
                margin-bottom: 6px; }
  .job-title { font-weight: 600; font-size: 15px; }
  .job-detail { font-size: 13px; color: #555; line-height: 1.6; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px;
           font-weight: 600; }
  .badge-pushed { background: #34c759; color: #fff; }
  .badge-skipped { background: #ff9500; color: #fff; }
  .badge-mismatch { background: #e5e5e5; color: #888; }
  .badge-too_far { background: #ff3b30; color: #fff; }
  .badge-push_failed { background: #ff3b30; color: #fff; }
  .stats { display: flex; gap: 12px; flex-wrap: wrap; margin: 8px 0 16px; }
  .stat { background: #f0f0f0; border-radius: 8px; padding: 8px 14px; font-size: 13px; }
  .stat b { font-size: 18px; }
  .push-btn { padding: 4px 14px; background: #007aff; color: #fff; border: none;
              border-radius: 6px; font-size: 12px; cursor: pointer; }
  .push-btn:hover { background: #0056cc; }
  .push-btn:disabled { background: #ccc; cursor: default; }
  .loading { color: #888; text-align: center; padding: 24px; }
  .empty { color: #aaa; text-align: center; padding: 32px; font-size: 14px; }
  .error { background: #fff3f3; color: #c00; padding: 12px; border-radius: 8px;
           margin-top: 8px; font-size: 13px; }
  hr { border: none; border-top: 1px solid #eee; margin: 8px 0; }
  .push-status { font-size: 12px; margin-left: 8px; }
  .push-status.ok { color: #34c759; }
  .push-status.fail { color: #ff3b30; }
</style>
</head>
<body>

<h1>家教信息筛选系统</h1>
<div class="subtitle">粘贴微信家教群消息，自动解析筛选并推送到手机</div>

<div class="config" id="config-panel">加载配置中...</div>

<textarea id="msg-input" placeholder="在此粘贴微信家教群消息...&#10;&#10;支持多条消息混合粘贴，系统会自动拆分和解析"></textarea>

<div class="btn-row">
  <button class="btn-parse" onclick="parseMessages()">解析筛选</button>
  <button class="btn-clear" onclick="clearAll()">清空</button>
</div>

<div class="stats" id="stats" style="display:none;"></div>
<div id="results"></div>

<script>
function _(id) { return document.getElementById(id); }

async function loadConfig() {
  try {
    const r = await fetch('/api/config');
    const cfg = await r.json();
    _('config-panel').innerHTML =
      '位置: <strong>' + cfg.my_address + '</strong> | ' +
      '最低薪资: <strong>' + cfg.min_salary + '元/h</strong> | ' +
      '科目: <strong>' + cfg.subjects.join(',') + '</strong> | ' +
      '年级: <strong>' + cfg.grades.join(',') + '</strong> | ' +
      '最大通勤: <strong>' + cfg.max_commute_time + '分钟(' + cfg.commute_mode + ')</strong> | ' +
      '跳过区域: <strong>' + cfg.skip_districts.join(',') + '</strong>';
  } catch(e) {
    _('config-panel').textContent = '加载配置失败: ' + e.message;
  }
}

async function parseMessages() {
  const text = _('msg-input').value.trim();
  if (!text) return;

  _('results').innerHTML = '<div class="loading">解析中...</div>';
  _('stats').style.display = 'none';

  try {
    const r = await fetch('/api/parse', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: text})
    });
    const data = await r.json();
    renderResults(data);
  } catch(e) {
    _('results').innerHTML = '<div class="error">请求失败: ' + e.message + '</div>';
  }
}

function renderResults(data) {
  const {results, stats} = data;

  // Stats bar
  let statHtml = '';
  const labels = {pushed:'已推送', skipped:'区域跳过', mismatch:'条件不符', too_far:'通勤太远', push_failed:'推送失败'};
  for (const [k, v] of Object.entries(stats)) {
    if (v > 0) statHtml += '<div class="stat"><b>' + v + '</b> ' + (labels[k]||k) + '</div>';
  }
  _('stats').innerHTML = statHtml || '<div class="stat">无匹配结果</div>';
  _('stats').style.display = 'flex';

  if (!results.length) {
    _('results').innerHTML = '<div class="empty">没有解析出有效家教信息</div>';
    return;
  }

  let html = '<div class="result">';
  results.forEach((r, i) => {
    const j = r.job;
    const badgeClass = 'badge-' + r.status;
    const statusLabel = labels[r.status] || r.status;

    let body = '';
    if (j.address) body += '地址: ' + j.address + '<br>';
    if (j.subjects && j.subjects.length) body += '科目: ' + j.subjects.join(' ') + '<br>';
    if (j.grade) body += '年级: ' + j.grade + '<br>';
    if (j.salary) {
      let s = '薪资: ' + j.salary;
      if (j.salary_max) s += '-' + j.salary_max;
      s += '元/h<br>';
      body += s;
    }
    if (j.commute_time) {
      let c = '通勤: 约' + j.commute_time + '分钟';
      if (j.commute_distance) c += ' (' + j.commute_distance + 'km)';
      body += c + '<br>';
    }
    if (j.time_requirement) body += '时间: ' + j.time_requirement + '<br>';
    if (r.reason) body += '原因: ' + r.reason + '<br>';

    html += '<div class="job">';
    html += '<div class="job-header">';
    html += '<span class="job-title">#' + (i+1) + ' <span class="badge ' + badgeClass + '">' + statusLabel + '</span></span>';
    if (r.status !== 'pushed' && r.status !== 'push_failed') {
      html += '<button class="push-btn" onclick="manualPush(' + i + ')" id="push-btn-' + i + '">手动推送</button>';
    }
    html += '</div>';
    html += '<div class="job-detail">' + body + '</div>';
    html += '</div>';
  });
  html += '</div>';
  _('results').innerHTML = html;

  // Store results for manual push
  window._results = results;
}

async function manualPush(idx) {
  const btn = _('push-btn-' + idx);
  btn.disabled = true;
  btn.textContent = '推送中...';

  try {
    const r = await fetch('/api/push', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({index: idx})
    });
    const data = await r.json();
    if (data.success) {
      btn.textContent = '已推送';
      btn.style.background = '#34c759';
    } else {
      btn.textContent = '推送失败';
      btn.style.background = '#ff3b30';
    }
  } catch(e) {
    btn.textContent = '推送失败';
    btn.style.background = '#ff3b30';
  }
}

function clearAll() {
  _('msg-input').value = '';
  _('results').innerHTML = '';
  _('stats').style.display = 'none';
}

// Init
loadConfig();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/config")
def api_config():
    core = get_core()
    cfg = core.config
    return jsonify({
        "my_address": cfg.my_address,
        "my_coords": cfg.my_coords,
        "min_salary": cfg.min_salary,
        "subjects": cfg.subjects,
        "grades": cfg.grades,
        "max_commute_time": cfg.max_commute_time,
        "commute_mode": cfg.commute_mode,
        "skip_districts": cfg.skip_districts,
        "target_groups": cfg.target_groups,
    })


@app.route("/api/parse", methods=["POST"])
def api_parse():
    data = request.get_json()
    text = data.get("text", "")
    if not text.strip():
        return jsonify({"results": [], "stats": {}})

    core = get_core()
    results = core.process_text(text)

    # Store last parse results for manual push
    app.config["_last_results"] = results

    stats = {}
    out = []
    for r in results:
        stats[r.status] = stats.get(r.status, 0) + 1
        out.append({
            "status": r.status,
            "reason": r.reason,
            "job": {
                "address": r.job.address,
                "subjects": r.job.subjects,
                "grade": r.job.grade,
                "salary": r.job.salary,
                "salary_max": r.job.salary_max,
                "commute_time": r.job.commute_time,
                "commute_distance": r.job.commute_distance,
                "time_requirement": r.job.time_requirement,
            },
        })

    return jsonify({"results": out, "stats": stats})


@app.route("/api/push", methods=["POST"])
def api_push():
    data = request.get_json()
    idx = data.get("index", 0)

    results = app.config.get("_last_results", [])
    if idx >= len(results):
        return jsonify({"success": False, "error": "索引无效"})

    result = results[idx]
    core = get_core()
    success = core.pusher.push(result.job)
    return jsonify({"success": success})


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5000

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        else:
            i += 1

    print(f"家教筛选 Web 界面: http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
