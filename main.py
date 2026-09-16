"""常州美食排行榜 — Flask 服务"""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, request

DATA_PATH = Path(__file__).parent / "data" / "restaurants.json"
TITLE = "常州美食排行榜"

app = Flask(__name__)


def load_restaurants() -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as f:
        items = json.load(f)
    # 按评分降序，同分按打卡次数降序（无次数视为 0）
    items.sort(key=lambda x: (x["score"], x["count"] or 0), reverse=True)
    return items


def render_page(items: list[dict], q: str = "") -> str:
    rows = []
    for i, item in enumerate(items, start=1):
        count = item["count"]
        count_html = f"{count} 次" if count is not None else "—"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, str(i))
        rows.append(
            f"""
            <tr>
              <td class="rank">{medal}</td>
              <td class="name">{item['name']}</td>
              <td class="score">{item['score']:.1f}</td>
              <td class="count">{count_html}</td>
            </tr>
            """
        )

    empty = ""
    if not rows:
        empty = '<tr><td colspan="4" class="empty">没有匹配的饭店</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{TITLE}</title>
  <style>
    :root {{
      --bg: #f7f3eb;
      --card: #fffdf8;
      --ink: #1f1a14;
      --muted: #6b6258;
      --accent: #c45c26;
      --line: #e8dfd2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(ellipse at top, #fff8ee 0%, var(--bg) 55%),
        var(--bg);
      color: var(--ink);
      min-height: 100vh;
    }}
    .wrap {{
      max-width: 720px;
      margin: 0 auto;
      padding: 32px 16px 48px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 1.75rem;
      letter-spacing: 0.04em;
    }}
    .sub {{
      margin: 0 0 24px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    form {{
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
    }}
    input[type="search"] {{
      flex: 1;
      padding: 10px 14px;
      border: 1px solid var(--line);
      border-radius: 10px;
      font-size: 1rem;
      background: #fff;
    }}
    button {{
      padding: 10px 16px;
      border: none;
      border-radius: 10px;
      background: var(--accent);
      color: #fff;
      font-size: 0.95rem;
      cursor: pointer;
    }}
    button:hover {{ filter: brightness(1.05); }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 8px 24px rgba(50, 30, 10, 0.06);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 12px 14px;
      text-align: left;
      border-bottom: 1px solid var(--line);
    }}
    th {{
      font-size: 0.85rem;
      color: var(--muted);
      font-weight: 600;
      background: #faf6ef;
    }}
    tr:last-child td {{ border-bottom: none; }}
    .rank {{ width: 56px; text-align: center; font-weight: 600; }}
    .score {{
      width: 72px;
      font-weight: 700;
      color: var(--accent);
    }}
    .count {{ width: 72px; color: var(--muted); }}
    .empty {{ text-align: center; color: var(--muted); padding: 28px; }}
    .meta {{
      margin-top: 14px;
      font-size: 0.85rem;
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{TITLE}</h1>
    <p class="sub">按评分排序 · 同分优先展示打卡次数更多的店</p>
    <form method="get" action="/">
      <input type="search" name="q" value="{q}" placeholder="搜索饭店名称…" autocomplete="off">
      <button type="submit">搜索</button>
    </form>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th class="rank">排名</th>
            <th>饭店</th>
            <th class="score">评分</th>
            <th class="count">次数</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows) or empty}
        </tbody>
      </table>
    </div>
    <p class="meta">共 {len(items)} 家 · API: <a href="/api/restaurants">/api/restaurants</a></p>
  </div>
</body>
</html>
"""


@app.get("/")
def index():
    q = (request.args.get("q") or "").strip()
    items = load_restaurants()
    if q:
        items = [x for x in items if q.lower() in x["name"].lower()]
    return render_page(items, q=q)


@app.get("/api/restaurants")
def api_restaurants():
    q = (request.args.get("q") or "").strip()
    items = load_restaurants()
    if q:
        items = [x for x in items if q.lower() in x["name"].lower()]
    return jsonify({"title": TITLE, "total": len(items), "items": items})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=False)
