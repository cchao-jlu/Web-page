#!/usr/bin/env python3
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request

from web_collect_agent import run_agent

app = Flask(__name__)

MODEL_OPTIONS = [
    {"label": "Auto (let provider decide)", "value": ""},
    {"label": "Custom (manual entry below)", "value": "__custom__"},
]

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Web Info Collector</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f2ea;
      --card: #fffdf9;
      --ink: #1c1a16;
      --muted: #6a5f52;
      --accent: #c06b2c;
      --accent-2: #1a7a74;
      --border: #e3d8c7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Merriweather", "Georgia", serif;
      color: var(--ink);
      background: radial-gradient(circle at 10% 10%, #fff6e9 0%, var(--bg) 40%, #efe6d8 100%);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      padding: 32px 16px 56px;
    }
    .wrap {
      width: min(980px, 100%);
      display: grid;
      gap: 24px;
    }
    header {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    h1 {
      font-size: clamp(1.8rem, 3vw, 2.6rem);
      margin: 0;
      letter-spacing: -0.02em;
    }
    p.lead {
      margin: 0;
      color: var(--muted);
      font-size: 1rem;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 12px 30px rgba(60, 45, 20, 0.08);
    }
    form {
      display: grid;
      gap: 14px;
    }
    label {
      font-weight: 600;
      font-size: 0.95rem;
    }
    input, select, textarea {
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--border);
      padding: 10px 12px;
      font-size: 0.95rem;
      font-family: "Source Sans 3", "Segoe UI", sans-serif;
      background: #fff;
      color: var(--ink);
    }
    textarea {
      min-height: 140px;
      resize: vertical;
    }
    .grid-2 {
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    }
    button {
      border: 0;
      padding: 12px 18px;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--accent), #e49d54);
      color: #fff;
      font-weight: 700;
      font-size: 1rem;
      cursor: pointer;
      box-shadow: 0 12px 18px rgba(192, 107, 44, 0.2);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    button:hover { transform: translateY(-1px); box-shadow: 0 16px 24px rgba(192, 107, 44, 0.3); }
    .status {
      color: var(--accent-2);
      font-weight: 600;
    }
    .error {
      color: #a02820;
      font-weight: 600;
    }
    .output pre {
      white-space: pre-wrap;
      margin: 0;
      font-family: "JetBrains Mono", "Courier New", monospace;
      font-size: 0.9rem;
      background: #f4eee4;
      padding: 16px;
      border-radius: 12px;
      border: 1px dashed var(--border);
    }
    footer {
      color: var(--muted);
      font-size: 0.85rem;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>Web Info Collector</h1>
      <p class="lead">输入一个主题，自动搜索网页并生成一页总结。</p>
    </header>

    <section class="card">
      <form method="post" action="/run">
        <div>
          <label for="topic">主题</label>
          <input id="topic" name="topic" required placeholder="例如：2025年AI监管趋势" value="{{ topic or '' }}" />
        </div>

        <div class="grid-2">
          <div>
            <label for="lang">输出语言</label>
            <select id="lang" name="lang">
              <option value="zh" {% if lang == 'zh' %}selected{% endif %}>中文</option>
              <option value="en" {% if lang == 'en' %}selected{% endif %}>English</option>
            </select>
          </div>
          <div>
            <label for="min_sources">最少来源数</label>
            <input id="min_sources" name="min_sources" type="number" min="1" value="{{ min_sources or 3 }}" />
          </div>
          <div>
            <label for="max_results">搜索结果数量</label>
            <input id="max_results" name="max_results" type="number" min="3" value="{{ max_results or 8 }}" />
          </div>
          <div>
            <label for="model_select">模型选择</label>
            <select id="model_select" name="model_select">
              {% for opt in model_options %}
                <option value="{{ opt.value }}" {% if model_select == opt.value %}selected{% endif %}>{{ opt.label }}</option>
              {% endfor %}
            </select>
          </div>
        </div>

        <div class="grid-2">
          <div>
            <label for="provider">Provider (可选)</label>
            <input id="provider" name="provider" placeholder="例如：hf-inference" value="{{ provider or '' }}" />
          </div>
          <div>
            <label for="token">HF Token (可选)</label>
            <input id="token" name="token" type="password" placeholder="仅本次使用" />
          </div>
        </div>
        <div>
          <label for="model_id">模型 ID (当选择 Custom 时生效)</label>
          <input id="model_id" name="model_id" placeholder="例如：Qwen/Qwen2.5-7B-Instruct" value="{{ model_id or '' }}" />
        </div>

        <button type="submit">开始搜集</button>
      </form>
    </section>

    {% if status %}
    <section class="card">
      <div class="status">{{ status }}</div>
      {% if output_path %}
        <div>已保存到: <strong>{{ output_path }}</strong></div>
      {% endif %}
    </section>
    {% endif %}

    {% if error %}
    <section class="card">
      <div class="error">{{ error }}</div>
    </section>
    {% endif %}

    {% if summary %}
    <section class="card output">
      <h3>总结预览</h3>
      <pre>{{ summary }}</pre>
    </section>
    {% endif %}

    <footer>Generated at {{ timestamp }}</footer>
  </div>
</body>
</html>
"""


def to_int(value: str | None, fallback: int) -> int:
    try:
        return int(value) if value else fallback
    except ValueError:
        return fallback


@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        HTML,
        topic="",
        lang="zh",
        min_sources=3,
        max_results=8,
        model_id="",
        model_select="",
        model_options=MODEL_OPTIONS,
        provider="",
        summary=None,
        output_path=None,
        status=None,
        error=None,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


@app.route("/run", methods=["POST"])
def run():
    topic = (request.form.get("topic") or "").strip()
    if not topic:
        return render_template_string(
            HTML,
            topic="",
            lang="zh",
            min_sources=3,
            max_results=8,
            model_id="",
            model_select="",
            model_options=MODEL_OPTIONS,
            provider="",
            summary=None,
            output_path=None,
            status=None,
            error="请提供主题。",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    lang = (request.form.get("lang") or "zh").strip()
    min_sources = to_int(request.form.get("min_sources"), 3)
    max_results = to_int(request.form.get("max_results"), 8)
    model_select = (request.form.get("model_select") or "").strip()
    manual_model = (request.form.get("model_id") or "").strip()
    if model_select == "__custom__":
        model_id = manual_model or None
    else:
        model_id = model_select or None
    provider = (request.form.get("provider") or "").strip() or None
    token = (request.form.get("token") or "").strip()

    if token:
        os.environ["HF_TOKEN"] = token

    try:
        summary, output_path = run_agent(
            topic,
            model_id=model_id,
            provider=provider,
            max_results=max_results,
            min_sources=min_sources,
            lang=lang,
            output=None,
        )
        status = "生成完成。"
        error = None
    except Exception as exc:  # noqa: BLE001
        summary = None
        output_path = None
        status = None
        error = f"运行失败：{exc}"

    return render_template_string(
        HTML,
        topic=topic,
        lang=lang,
        min_sources=min_sources,
        max_results=max_results,
        model_id=model_id or "",
        model_select=model_select,
        model_options=MODEL_OPTIONS,
        provider=provider or "",
        summary=summary,
        output_path=output_path,
        status=status,
        error=error,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
