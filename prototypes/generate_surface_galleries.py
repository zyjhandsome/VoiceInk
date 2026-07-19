# -*- coding: utf-8 -*-
"""Generate 10-variant prototype galleries for Model / Polish / About / History."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSS = (ROOT / "_gallery-common.css").read_text(encoding="utf-8")

# Extra layout helpers used across the new galleries
EXTRA_CSS = """
    .model-card {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius-lg); padding: 14px 16px; margin-bottom: 10px;
    }
    .model-card.on { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
    .model-card .name { font-size: 15px; font-weight: 650; }
    .model-card .meta { font-size: 12px; color: var(--text-dim); margin-top: 4px; }
    .model-card .desc { font-size: 13px; color: var(--text-sec); margin-top: 6px; line-height: 1.4; }
    .model-card .actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
    .badge-pill {
      display: inline-block; font-size: 11px; font-weight: 600;
      background: var(--surface-muted); color: var(--text-sec);
      border-radius: 999px; padding: 3px 10px;
    }
    .badge-pill.accent { background: var(--accent-soft); color: var(--accent); }
    .kv { display: grid; grid-template-columns: 120px 1fr; gap: 8px 12px; padding: 12px 16px; }
    .kv .k { font-size: 12px; color: var(--text-dim); }
    .kv .v { font-size: 13px; color: var(--text); }
    .preview-box {
      margin: 12px 16px; padding: 12px; border-radius: var(--radius-md);
      background: var(--surface-muted); border: 1px solid var(--border);
      font-size: 13px; line-height: 1.5; color: var(--text-sec);
    }
    .preview-box .lbl { font-size: 11px; font-weight: 650; color: var(--text-dim); margin-bottom: 6px; }
    .hist-shell { display: grid; grid-template-columns: 320px 1fr; min-height: 560px; }
    .hist-left { background: var(--surface); border-right: 1px solid var(--border); padding: 16px; }
    .hist-right { background: var(--bg); padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
    .session-item {
      padding: 10px 12px; border-radius: var(--radius-sm); margin: 2px 0; cursor: pointer;
      font-size: 13px;
    }
    .session-item.on { background: var(--accent-soft); border-left: 3px solid var(--accent); font-weight: 600; }
    .session-item:hover:not(.on) { background: var(--surface-muted); }
    .session-meta { font-size: 11px; color: var(--text-dim); margin-top: 3px; }
    .detail-body {
      flex: 1; background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius-lg); padding: 16px; font-size: 14px; line-height: 1.55;
      color: var(--text); min-height: 280px;
    }
    .toolbar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    .center-brand { text-align: center; padding: 40px 24px; }
    .center-brand .mark {
      width: 64px; height: 64px; border-radius: 16px; margin: 0 auto 16px;
      background: linear-gradient(145deg, #2563EB, #1D4ED8);
      display: grid; place-items: center; color: #fff; font-size: 22px; font-weight: 700;
    }
    .timeline { border-left: 2px solid var(--border); margin: 8px 0 8px 8px; padding-left: 16px; }
    .timeline .item { margin-bottom: 16px; position: relative; }
    .timeline .item::before {
      content: ""; position: absolute; left: -21px; top: 6px;
      width: 10px; height: 10px; border-radius: 50%; background: var(--accent);
    }
    .table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .table th, .table td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); }
    .table th { color: var(--text-dim); font-weight: 600; font-size: 12px; }
    .chip-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    .stat {
      background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);
      padding: 14px 16px; min-width: 120px;
    }
    .stat .n { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
    .stat .l { font-size: 12px; color: var(--text-dim); margin-top: 4px; }
    .acc { border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; background: var(--surface); }
    .acc + .acc { margin-top: 8px; }
    .acc-head {
      width: 100%; text-align: left; appearance: none; border: none; background: var(--surface);
      padding: 12px 16px; font: inherit; font-size: 13px; font-weight: 600; color: var(--text); cursor: pointer;
    }
    .acc-body { display: none; padding: 0 16px 14px; border-top: 1px solid var(--border); }
    .acc.open .acc-body { display: block; }
    .rail {
      display: grid; grid-template-columns: 140px 1fr; gap: 16px;
    }
    .rail nav { display: flex; flex-direction: column; gap: 4px; position: sticky; top: 12px; }
    .rail nav a {
      font-size: 12px; color: var(--text-dim); text-decoration: none; padding: 6px 10px;
      border-left: 2px solid transparent;
    }
    .rail nav a.on { color: var(--accent); border-left-color: var(--accent); font-weight: 600; }
    .dense .row { min-height: 44px; padding: 8px 14px; }
    .wf { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .wf-card {
      background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);
      padding: 14px;
    }
    .wf-card .step { font-size: 11px; font-weight: 650; color: var(--accent); margin-bottom: 6px; }
    .app.hist-only { grid-template-columns: 1fr; }
    .app.hist-only .sidebar { display: none; }
"""

SIDEBAR = """
        <aside class="sidebar">
          <div class="brand"><div class="brand-mark">V</div><div class="brand-name">VoiceInk</div></div>
          <nav class="nav">
            <div class="nav-item{g}"><span class="nav-ico"></span>通用</div>
            <div class="nav-item{m}"><span class="nav-ico"></span>语音识别</div>
            <div class="nav-item{p}"><span class="nav-ico"></span>文本润色</div>
            <div class="nav-item{a}"><span class="nav-ico"></span>关于</div>
          </nav>
          <div class="status-chip">状态 · <b>就绪</b></div>
        </aside>
"""


def sidebar(active: str) -> str:
    flags = {k: "" for k in "gmpa"}
    flags[active] = " active"
    return SIDEBAR.format(**flags)


def shell(active_nav: str, body: str, *, hist: bool = False) -> str:
    cls = "app hist-only" if hist else "app"
    side = "" if hist else sidebar(active_nav)
    return f"""
      <div class="{cls}" data-shell>
{side}
        <div class="main"><div class="main-body">
{body}
        </div></div>
      </div>"""


SCRIPT = """
  <script>
    function wireInteractive(root = document) {
      root.querySelectorAll(".toggle").forEach((el) => {
        if (el.dataset.wired) return;
        el.dataset.wired = "1";
        el.addEventListener("click", () => el.classList.toggle("on"));
      });
      root.querySelectorAll(".picker").forEach((group) => {
        group.querySelectorAll(".pick").forEach((btn) => {
          if (btn.dataset.wired) return;
          btn.dataset.wired = "1";
          btn.addEventListener("click", () => {
            group.querySelectorAll(".pick").forEach((b) => b.classList.remove("on"));
            btn.classList.add("on");
          });
        });
      });
      root.querySelectorAll(".seg").forEach((group) => {
        group.querySelectorAll("button").forEach((btn) => {
          if (btn.dataset.wired) return;
          btn.dataset.wired = "1";
          btn.addEventListener("click", () => {
            group.querySelectorAll("button").forEach((b) => b.classList.remove("on"));
            btn.classList.add("on");
          });
        });
      });
      root.querySelectorAll(".acc-head").forEach((btn) => {
        if (btn.dataset.wired) return;
        btn.dataset.wired = "1";
        btn.addEventListener("click", () => btn.parentElement.classList.toggle("open"));
      });
      root.querySelectorAll(".subtabs").forEach((bar) => {
        if (bar.dataset.wired) return;
        bar.dataset.wired = "1";
        const panes = bar.parentElement.querySelectorAll(":scope > .pane");
        bar.querySelectorAll(".subtab").forEach((btn) => {
          btn.addEventListener("click", () => {
            bar.querySelectorAll(".subtab").forEach((b) => b.classList.remove("on"));
            btn.classList.add("on");
            const id = btn.dataset.pane;
            panes.forEach((p) => p.classList.toggle("on", p.id === id));
          });
        });
      });
    }
    wireInteractive();
    document.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
        document.querySelectorAll(".variant").forEach((v) => v.classList.remove("active"));
        tab.classList.add("active");
        document.getElementById("v-" + tab.dataset.v).classList.add("active");
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    });
    const themeToggle = document.getElementById("themeToggle");
    themeToggle.addEventListener("click", () => {
      const active = document.querySelector(".variant.active .app");
      const next = !active.classList.contains("dark");
      document.querySelectorAll("[data-shell]").forEach((s) => s.classList.toggle("dark", next));
      themeToggle.textContent = next ? "预览浅色" : "预览暗色";
    });
  </script>
"""

TAB_NAMES = [
    "1 纵向分组",
    "2 双栏分区",
    "3 子页签",
    "4 紧凑列表",
    "5 工作流",
    "6 手风琴",
    "7 主从面板",
    "8 扁平分区",
    "9 锚点目录",
    "10 摘要卡片",
]


def page(title: str, meta: str, variants: list[tuple[str, str, str]]) -> str:
    tabs = "\n".join(
        f'      <button class="tab{" active" if i == 0 else ""}" data-v="{i+1}">{n}</button>'
        for i, n in enumerate(TAB_NAMES)
    )
    sections = []
    for i, (badge, caption, body) in enumerate(variants, 1):
        active = " active" if i == 1 else ""
        sections.append(
            f"""
    <section class="variant{active}" id="v-{i}">
      <div class="caption"><span class="badge">{badge}</span>
        <p>{caption}</p></div>
{body}
    </section>"""
        )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
{CSS}
{EXTRA_CSS}
  </style>
</head>
<body>
  <header class="gallery-bar">
    <h1>{title}</h1>
    <div class="tabs" role="tablist">
{tabs}
    </div>
    <button class="theme-toggle" id="themeToggle" type="button">预览暗色</button>
    <p class="meta">{meta}</p>
  </header>
  <div class="stage">
{''.join(sections)}
  </div>
{SCRIPT}
</body>
</html>
"""


# ── Shared mock content bits ──────────────────────────────────────

MODEL_ACTIVE = """
            <div class="model-card on">
              <div style="display:flex;gap:8px;align-items:center;">
                <span class="name">SenseVoice 小</span>
                <span class="badge-pill accent">当前引擎</span>
                <span style="margin-left:auto;font-size:12px;color:var(--text-dim)">~220 MB</span>
              </div>
              <div class="desc">中英日韩粤等多语种，速度与体积较均衡，适合日常口述。</div>
              <div class="meta">多语种 · 准确 ★★★☆ · 速度 ★★★★</div>
            </div>"""

MODEL_LIST = """
            <div class="model-card">
              <div class="name">Paraformer 中</div>
              <div class="desc">中文识别更稳，体积更大。</div>
              <div class="meta">中文优先 · ~640 MB</div>
              <div class="actions"><button class="btn btn-primary">启用</button><button class="btn">删除</button></div>
            </div>
            <div class="model-card">
              <div class="name">Whisper tiny</div>
              <div class="desc">体积小，适合试听与弱网。</div>
              <div class="meta">多语种 · ~75 MB</div>
              <div class="actions"><button class="btn btn-primary">下载</button></div>
            </div>
            <div class="model-card">
              <div class="name">Whisper small</div>
              <div class="desc">准确度更高，下载与载入更久。</div>
              <div class="meta">多语种 · ~460 MB</div>
              <div class="actions"><button class="btn btn-primary">下载</button></div>
            </div>"""

STORAGE_ROW = """
            <div class="row">
              <div class="row-text">
                <div class="row-title">模型存储</div>
                <div class="row-desc">已下载 2 个 · 约 860 MB · C:\\Users\\…\\.voiceink\\models</div>
              </div>
              <button class="btn">更改存储…</button>
            </div>"""


def model_variants() -> list[tuple[str, str, str]]:
    nav = "m"
    v = []

    v.append((
        "01",
        "<strong>纵向分组</strong>：接近现状。Hero + 当前引擎 + 存储 + 模型列表。",
        shell(nav, f"""
          <div class="hero"><h2>语音识别</h2><p>SenseVoice 小 · 220 MB · 多语种</p></div>
          <div class="section"><div class="section-label">当前引擎</div><div class="card" style="padding:8px;">{MODEL_ACTIVE}</div></div>
          <div class="section"><div class="section-label">存储</div><div class="card">{STORAGE_ROW}</div></div>
          <div class="section"><div class="section-label">其他已下载</div>
            <div class="model-card">
              <div class="name">Paraformer 中</div>
              <div class="desc">中文识别更稳，体积更大。</div>
              <div class="actions"><button class="btn btn-primary">启用</button><button class="btn">删除</button></div>
            </div>
          </div>
          <div class="section"><div class="section-label">可下载</div>
            <div class="model-card"><div class="name">Whisper tiny</div><div class="meta">~75 MB</div>
              <div class="actions"><button class="btn btn-primary">下载</button></div></div>
          </div>
        """),
    ))

    v.append((
        "02",
        "<strong>双栏分区</strong>：左栏固定当前引擎与存储，右栏浏览目录。",
        shell(nav, f"""
          <div class="hero"><h2>语音识别</h2><p>选择并管理本地识别引擎</p></div>
          <div class="split">
            <div class="col">
              <div class="section-label">正在使用</div>
              <div class="card" style="padding:8px;">{MODEL_ACTIVE}
                <div style="padding:0 8px 12px">{STORAGE_ROW.replace('class="row"', 'class="row" style="padding:8px 0;border:none"')}</div>
              </div>
            </div>
            <div class="col">
              <div class="section-label">模型目录</div>
              {MODEL_LIST}
            </div>
          </div>
        """),
    ))

    v.append((
        "03 · 推荐对照",
        "<strong>子页签</strong>：当前 / 已下载 / 可下载，降低长列表压迫感。",
        shell(nav, f"""
          <div class="hero"><h2>语音识别</h2><p>按状态浏览模型</p></div>
          <div class="subtabs">
            <button class="subtab on" data-pane="m-cur">当前</button>
            <button class="subtab" data-pane="m-dl">已下载</button>
            <button class="subtab" data-pane="m-av">可下载</button>
          </div>
          <div class="pane on" id="m-cur">
            <div class="card" style="padding:8px;">{MODEL_ACTIVE}</div>
            <div class="card" style="margin-top:12px">{STORAGE_ROW}</div>
          </div>
          <div class="pane" id="m-dl"><div class="model-card"><div class="name">Paraformer 中</div>
            <div class="actions"><button class="btn btn-primary">启用</button><button class="btn">删除</button></div></div></div>
          <div class="pane" id="m-av">
            <div class="model-card"><div class="name">Whisper tiny</div><div class="actions"><button class="btn btn-primary">下载</button></div></div>
            <div class="model-card"><div class="name">Whisper small</div><div class="actions"><button class="btn btn-primary">下载</button></div></div>
          </div>
        """),
    ))

    v.append((
        "04",
        "<strong>紧凑列表</strong>：一行一模型，密度接近系统设置。",
        shell(nav, """
          <div class="compact-hero" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <h2 style="font-size:17px;font-weight:650">语音识别</h2>
            <button class="btn">更改存储…</button>
          </div>
          <div class="card dense">
            <div class="row"><div class="row-text"><div class="row-title">SenseVoice 小</div><div class="row-desc">当前 · 220 MB · 多语种</div></div><span class="badge-pill accent">使用中</span></div>
            <div class="row"><div class="row-text"><div class="row-title">Paraformer 中</div><div class="row-desc">已下载 · 640 MB</div></div><button class="btn">启用</button></div>
            <div class="row"><div class="row-text"><div class="row-title">Whisper tiny</div><div class="row-desc">未下载 · 75 MB</div></div><button class="btn btn-primary">下载</button></div>
            <div class="row"><div class="row-text"><div class="row-title">Whisper small</div><div class="row-desc">未下载 · 460 MB</div></div><button class="btn btn-primary">下载</button></div>
          </div>
        """),
    ))

    v.append((
        "05",
        "<strong>工作流</strong>：选引擎 → 下载/启用 → 存储，三步卡片。",
        shell(nav, f"""
          <div class="hero"><h2>语音识别</h2><p>先选好引擎，再管理本机文件</p></div>
          <div class="wf">
            <div class="wf-card"><div class="step">1 · 当前</div><h3 style="font-size:14px;margin-bottom:8px">用哪个引擎</h3>{MODEL_ACTIVE}</div>
            <div class="wf-card"><div class="step">2 · 获取</div><h3 style="font-size:14px;margin-bottom:8px">下载更多</h3>
              <button class="pick on" style="width:100%;margin-bottom:6px"><span class="t">Whisper tiny</span></button>
              <button class="btn btn-primary" style="width:100%">下载选中</button>
            </div>
            <div class="wf-card"><div class="step">3 · 存储</div><h3 style="font-size:14px;margin-bottom:8px">放在哪里</h3>
              <p class="row-desc" style="margin-bottom:10px">已下载 2 个 · 约 860 MB</p>
              <button class="btn" style="width:100%">更改存储…</button>
            </div>
          </div>
        """),
    ))

    v.append((
        "06",
        "<strong>手风琴</strong>：当前 / 已下载 / 可下载 / 存储折叠展开。",
        shell(nav, f"""
          <div class="hero"><h2>语音识别</h2><p>按需展开区块</p></div>
          <div class="acc open"><button class="acc-head" type="button">当前引擎 ▾</button>
            <div class="acc-body">{MODEL_ACTIVE}</div></div>
          <div class="acc"><button class="acc-head" type="button">其他已下载 ▸</button>
            <div class="acc-body"><div class="model-card"><div class="name">Paraformer 中</div>
              <div class="actions"><button class="btn btn-primary">启用</button></div></div></div></div>
          <div class="acc"><button class="acc-head" type="button">可下载 ▸</button>
            <div class="acc-body"><div class="model-card"><div class="name">Whisper tiny</div>
              <div class="actions"><button class="btn btn-primary">下载</button></div></div></div></div>
          <div class="acc"><button class="acc-head" type="button">存储 ▸</button>
            <div class="acc-body"><div class="card">{STORAGE_ROW}</div></div></div>
        """),
    ))

    v.append((
        "07",
        "<strong>主从面板</strong>：左列表选模型，右详情报价与操作。",
        shell(nav, """
          <div class="hero sm"><h2>语音识别</h2></div>
          <div class="split">
            <div class="col card" style="padding:8px;">
              <div class="session-item on">SenseVoice 小<span class="session-meta">当前 · 220 MB</span></div>
              <div class="session-item">Paraformer 中<span class="session-meta">已下载 · 640 MB</span></div>
              <div class="session-item">Whisper tiny<span class="session-meta">可下载 · 75 MB</span></div>
              <div class="session-item">Whisper small<span class="session-meta">可下载 · 460 MB</span></div>
            </div>
            <div class="col">
              <div class="card" style="padding:16px;">
                <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
                  <span style="font-size:18px;font-weight:650">SenseVoice 小</span>
                  <span class="badge-pill accent">当前引擎</span>
                </div>
                <p style="font-size:13px;color:var(--text-sec);line-height:1.45;margin-bottom:10px;">
                  中英日韩粤等多语种，速度与体积较均衡，适合日常口述。
                </p>
                <div class="meta" style="font-size:12px;color:var(--text-dim);margin-bottom:14px;">多语种 · 准确 ★★★☆ · 速度 ★★★★</div>
                <div class="toolbar">
                  <button class="btn btn-primary">保持启用</button>
                  <button class="btn">删除</button>
                  <button class="btn">更改存储…</button>
                </div>
              </div>
            </div>
          </div>
        """),
    ))

    v.append((
        "08",
        "<strong>扁平分区</strong>：弱化卡片嵌套，分区标题 + 列表。",
        shell(nav, f"""
          <div class="hero"><h2>语音识别</h2><p>本机模型与存储路径</p></div>
          <div class="section-label">当前</div>
          {MODEL_ACTIVE}
          <div class="section-label">存储</div>
          <div class="row" style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);">
            <div class="row-text"><div class="row-title">已下载 2 个 · 约 860 MB</div>
              <div class="row-desc">C:\\Users\\…\\.voiceink\\models</div></div>
            <button class="btn-link">更改存储…</button>
          </div>
          <div class="section-label" style="margin-top:16px">目录</div>
          {MODEL_LIST}
        """),
    ))

    v.append((
        "09",
        "<strong>锚点目录</strong>：左侧跳转当前 / 已下载 / 可下载 / 存储。",
        shell(nav, f"""
          <div class="hero"><h2>语音识别</h2></div>
          <div class="rail">
            <nav>
              <a class="on" href="#mc">当前</a>
              <a href="#md">已下载</a>
              <a href="#ma">可下载</a>
              <a href="#ms">存储</a>
            </nav>
            <div>
              <div id="mc" class="section"><div class="section-label">当前</div><div class="card" style="padding:8px">{MODEL_ACTIVE}</div></div>
              <div id="md" class="section"><div class="section-label">已下载</div><div class="model-card"><div class="name">Paraformer 中</div></div></div>
              <div id="ma" class="section"><div class="section-label">可下载</div><div class="model-card"><div class="name">Whisper tiny</div></div></div>
              <div id="ms" class="section"><div class="section-label">存储</div><div class="card">{STORAGE_ROW}</div></div>
            </div>
          </div>
        """),
    ))

    v.append((
        "10",
        "<strong>摘要卡片</strong>：顶栏统计 + 推荐引擎 + 其余网格。",
        shell(nav, f"""
          <div class="hero"><h2>语音识别</h2><p>一眼看懂容量与当前选择</p></div>
          <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px;">
            <div class="stat"><div class="n">2</div><div class="l">已下载</div></div>
            <div class="stat"><div class="n">860</div><div class="l">占用 MB</div></div>
            <div class="stat"><div class="n">2</div><div class="l">可下载</div></div>
          </div>
          <div class="section-label">推荐使用</div>
          <div class="card" style="padding:8px">{MODEL_ACTIVE}</div>
          <div class="section-label" style="margin-top:16px">更多模型</div>
          <div class="split3">{MODEL_LIST}</div>
          <div class="card" style="margin-top:12px">{STORAGE_ROW}</div>
        """),
    ))
    return v


def polish_variants() -> list[tuple[str, str, str]]:
    nav = "p"
    enable = """
            <div class="row">
              <div class="row-text">
                <div class="row-title">启用后处理</div>
                <div class="row-desc">关闭时直接输出语音转写原文</div>
              </div>
              <button class="toggle on" type="button"></button>
            </div>"""
    preview = """
            <div class="preview-box">
              <div class="lbl">效果预览</div>
              <div><b>原文</b>　嗯那个就是把会议纪要整理一下吧</div>
              <div style="margin-top:6px"><b>润色</b>　请整理会议纪要。</div>
            </div>"""
    fields = """
            <div class="field"><label>接口地址</label><input class="input" value="https://api.deepseek.com/v1" /></div>
            <div class="field" style="border-top:1px solid var(--border)">
              <label>API 密钥</label>
              <div style="display:flex;gap:8px"><input class="input" type="password" value="sk-••••" /><button class="btn">显示</button></div>
            </div>
            <div class="field" style="border-top:1px solid var(--border)"><label>模型名称</label><input class="input" value="deepseek-chat" /></div>
            <div class="row"><button class="btn">测试连接</button></div>"""
    prompt = """
            <div style="padding:12px 16px">
              <div style="display:flex;justify-content:flex-end;margin-bottom:8px"><button class="btn">恢复默认</button></div>
              <textarea class="input" style="min-height:120px;resize:vertical">你是语音转写后的文本润色助手……</textarea>
            </div>"""

    v = []
    v.append(("01", "<strong>纵向分组</strong>：接近现状。开关 + 预览 + 接口 + 提示词。",
        shell(nav, f"""
          <div class="hero"><h2>文字润色</h2><p>已开启 · deepseek-chat</p></div>
          <div class="card">{enable}{preview}</div>
          <div class="section" style="margin-top:16px"><div class="section-label">接口配置</div><div class="card">{fields}</div></div>
          <div class="section"><div class="section-label">提示词</div><div class="card">{prompt}</div></div>
          <p class="footnote">支持 OpenAI、DeepSeek、通义千问、Ollama 等 OpenAI 兼容接口。</p>
        """)))
    v.append(("02", "<strong>双栏分区</strong>：左配置，右实时预览。",
        shell(nav, f"""
          <div class="hero"><h2>文字润色</h2><p>配置接口与提示词，右侧看效果</p></div>
          <div class="split">
            <div class="col">
              <div class="card">{enable}</div>
              <div class="card" style="margin-top:12px">{fields}</div>
              <div class="card" style="margin-top:12px">{prompt}</div>
            </div>
            <div class="col">
              <div class="section-label">预览</div>
              <div class="card">{preview}</div>
              <p class="footnote" style="margin-top:12px">兼容 OpenAI 协议的接口均可。</p>
            </div>
          </div>
        """)))
    v.append(("03 · 推荐对照", "<strong>子页签</strong>：总览 / 接口 / 提示词。",
        shell(nav, f"""
          <div class="hero"><h2>文字润色</h2><p>已开启 · deepseek-chat</p></div>
          <div class="subtabs">
            <button class="subtab on" data-pane="p-ov">总览</button>
            <button class="subtab" data-pane="p-api">接口</button>
            <button class="subtab" data-pane="p-pr">提示词</button>
          </div>
          <div class="pane on" id="p-ov"><div class="card">{enable}{preview}</div></div>
          <div class="pane" id="p-api"><div class="card">{fields}</div></div>
          <div class="pane" id="p-pr"><div class="card">{prompt}</div></div>
        """)))
    v.append(("04", "<strong>紧凑列表</strong>：控件右对齐，密度更高。",
        shell(nav, """
          <div class="compact-hero" style="display:flex;justify-content:space-between;margin-bottom:14px;">
            <h2 style="font-size:17px;font-weight:650">文字润色</h2>
            <button class="toggle on" type="button"></button>
          </div>
          <div class="card dense">
            <div class="row"><div class="row-text"><div class="row-title">接口地址</div></div><input class="input" style="width:240px" value="https://api.deepseek.com/v1" /></div>
            <div class="row"><div class="row-text"><div class="row-title">API 密钥</div></div><input class="input" style="width:240px" type="password" value="sk-••" /></div>
            <div class="row"><div class="row-text"><div class="row-title">模型名称</div></div><input class="input" style="width:240px" value="deepseek-chat" /></div>
            <div class="row"><div class="row-text"><div class="row-title">提示词</div><div class="row-desc">留空则用内置默认</div></div><button class="btn">编辑</button></div>
            <div class="row"><div class="row-text"><div class="row-title">连接</div></div><button class="btn">测试连接</button></div>
          </div>
        """)))
    v.append(("05", "<strong>工作流</strong>：开启 → 填接口 → 测通 → 调提示词。",
        shell(nav, f"""
          <div class="hero"><h2>文字润色</h2><p>按四步配好后处理</p></div>
          <div class="wf" style="grid-template-columns:1fr 1fr">
            <div class="wf-card"><div class="step">1 · 开关</div><h3 style="font-size:14px;margin-bottom:8px">是否润色</h3>{enable}</div>
            <div class="wf-card"><div class="step">2 · 接口</div><h3 style="font-size:14px;margin-bottom:8px">填地址与密钥</h3>
              <input class="input" style="margin-bottom:8px" value="https://api.deepseek.com/v1" />
              <input class="input" type="password" value="sk-••••" /></div>
            <div class="wf-card"><div class="step">3 · 验证</div><h3 style="font-size:14px;margin-bottom:8px">测试连接</h3>
              <button class="btn btn-primary" style="width:100%">测试连接</button></div>
            <div class="wf-card"><div class="step">4 · 提示词</div><h3 style="font-size:14px;margin-bottom:8px">怎么改写</h3>
              <button class="btn" style="width:100%">编辑提示词</button></div>
          </div>
          {preview}
        """)))
    v.append(("06", "<strong>手风琴</strong>：总开关、接口、提示词、说明折叠。",
        shell(nav, f"""
          <div class="hero"><h2>文字润色</h2></div>
          <div class="acc open"><button class="acc-head" type="button">启用与预览 ▾</button>
            <div class="acc-body"><div class="card" style="border:none">{enable}{preview}</div></div></div>
          <div class="acc"><button class="acc-head" type="button">接口配置 ▸</button>
            <div class="acc-body"><div class="card" style="border:none">{fields}</div></div></div>
          <div class="acc"><button class="acc-head" type="button">提示词 ▸</button>
            <div class="acc-body"><div class="card" style="border:none">{prompt}</div></div></div>
          <div class="acc"><button class="acc-head" type="button">兼容说明 ▸</button>
            <div class="acc-body"><p class="footnote">支持 OpenAI、DeepSeek、通义千问、Ollama 等。</p></div></div>
        """)))
    v.append(("07", "<strong>主从面板</strong>：左导航配置项，右编辑区。",
        shell(nav, f"""
          <div class="hero sm"><h2>文字润色</h2></div>
          <div class="split">
            <div class="col card" style="padding:8px;">
              <div class="session-item on">启用后处理</div>
              <div class="session-item">接口地址</div>
              <div class="session-item">API 密钥</div>
              <div class="session-item">模型名称</div>
              <div class="session-item">提示词</div>
              <div class="session-item">测试连接</div>
            </div>
            <div class="col card" style="padding:16px;">
              <div class="row-title" style="margin-bottom:8px">启用后处理</div>
              <div class="row-desc" style="margin-bottom:12px">关闭时直接输出语音转写原文</div>
              <button class="toggle on" type="button"></button>
              {preview}
            </div>
          </div>
        """)))
    v.append(("08", "<strong>扁平分区</strong>：少卡片嵌套，分区更轻。",
        shell(nav, f"""
          <div class="hero"><h2>文字润色</h2><p>已开启 · deepseek-chat</p></div>
          {enable}
          {preview}
          <div class="section-label" style="margin-top:16px">接口</div>
          <div class="card">{fields}</div>
          <div class="section-label" style="margin-top:16px">提示词</div>
          <div class="card">{prompt}</div>
        """)))
    v.append(("09", "<strong>锚点目录</strong>：侧栏跳转到开关 / 接口 / 提示词。",
        shell(nav, f"""
          <div class="hero"><h2>文字润色</h2></div>
          <div class="rail">
            <nav>
              <a class="on" href="#pe">开关</a>
              <a href="#pa">接口</a>
              <a href="#pp">提示词</a>
            </nav>
            <div>
              <div id="pe" class="card" style="margin-bottom:14px">{enable}{preview}</div>
              <div id="pa" class="section"><div class="section-label">接口配置</div><div class="card">{fields}</div></div>
              <div id="pp" class="section"><div class="section-label">提示词</div><div class="card">{prompt}</div></div>
            </div>
          </div>
        """)))
    v.append(("10", "<strong>摘要卡片</strong>：状态条 + 两块配置卡。",
        shell(nav, f"""
          <div class="hero"><h2>文字润色</h2></div>
          <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
            <div class="stat"><div class="n" style="font-size:16px;color:var(--green)">已开启</div><div class="l">后处理</div></div>
            <div class="stat"><div class="n" style="font-size:16px">deepseek-chat</div><div class="l">模型</div></div>
            <div class="stat"><div class="n" style="font-size:16px">未测</div><div class="l">连接</div></div>
          </div>
          <div class="split">
            <div class="card">{enable}{fields}</div>
            <div class="card">{prompt}{preview}</div>
          </div>
        """)))
    return v


def about_variants() -> list[tuple[str, str, str]]:
    nav = "a"
    brand = """
            <div class="row" style="gap:14px">
              <div class="brand-mark" style="width:48px;height:48px;font-size:18px;border-radius:12px">V</div>
              <div class="row-text">
                <div style="font-size:22px;font-weight:650">VoiceInk</div>
                <div class="chip-row"><span class="badge-pill">版本 0.x.x</span></div>
              </div>
            </div>"""
    tip = """
            <div class="callout" style="margin:12px">持续转写：按住 Ctrl+Win+Space 开始监听，停顿后自动出字；Esc 或浮窗 × 结束</div>"""
    info = """
            <div class="kv">
              <div class="k">识别引擎</div><div class="v">SenseVoice 小</div>
              <div class="k">润色</div><div class="v">已关闭</div>
              <div class="k">触发方式</div><div class="v">连续口述</div>
              <div class="k">快捷键</div><div class="v">Ctrl + Win + Space</div>
              <div class="k">模型目录</div><div class="v">~/.voiceink/models</div>
            </div>"""

    v = []
    v.append(("01", "<strong>纵向分组</strong>：接近现状。品牌卡 + 用法提示 + 运行信息。",
        shell(nav, f"""
          <div class="hero"><h2>关于 VoiceInk</h2></div>
          <div class="card">{brand}</div>
          {tip}
          <div class="section"><div class="section-label">运行信息</div><div class="card">{info}</div></div>
        """)))
    v.append(("02", "<strong>双栏分区</strong>：左品牌与提示，右运行信息。",
        shell(nav, f"""
          <div class="hero"><h2>关于 VoiceInk</h2></div>
          <div class="split">
            <div class="col"><div class="card">{brand}</div>{tip}</div>
            <div class="col"><div class="section-label">运行信息</div><div class="card">{info}</div></div>
          </div>
        """)))
    v.append(("03", "<strong>子页签</strong>：概览 / 运行信息 / 用法。",
        shell(nav, f"""
          <div class="hero"><h2>关于 VoiceInk</h2></div>
          <div class="subtabs">
            <button class="subtab on" data-pane="a-ov">概览</button>
            <button class="subtab" data-pane="a-rt">运行信息</button>
            <button class="subtab" data-pane="a-tip">用法</button>
          </div>
          <div class="pane on" id="a-ov"><div class="card">{brand}</div></div>
          <div class="pane" id="a-rt"><div class="card">{info}</div></div>
          <div class="pane" id="a-tip">{tip}</div>
        """)))
    v.append(("04", "<strong>紧凑列表</strong>：版本与键值同行展示。",
        shell(nav, f"""
          <div class="compact-hero" style="margin-bottom:14px"><h2 style="font-size:17px;font-weight:650">关于</h2></div>
          <div class="card dense">
            <div class="row"><div class="row-text"><div class="row-title">VoiceInk</div></div><span class="badge-pill">版本 0.x.x</span></div>
            <div class="row"><div class="row-text"><div class="row-title">识别引擎</div></div><div class="row-desc">SenseVoice 小</div></div>
            <div class="row"><div class="row-text"><div class="row-title">润色</div></div><div class="row-desc">已关闭</div></div>
            <div class="row"><div class="row-text"><div class="row-title">快捷键</div></div><div class="row-desc">Ctrl + Win + Space</div></div>
          </div>
          {tip}
        """)))
    v.append(("05", "<strong>居中品牌页</strong>：营销感弱、产品名作主视觉。",
        shell(nav, f"""
          <div class="card">
            <div class="center-brand">
              <div class="mark">V</div>
              <div style="font-size:28px;font-weight:700;letter-spacing:-0.02em">VoiceInk</div>
              <div class="chip-row" style="justify-content:center;margin-top:12px"><span class="badge-pill">版本 0.x.x</span></div>
              <p style="margin-top:16px;font-size:13px;color:var(--text-dim);max-width:360px;margin-left:auto;margin-right:auto;line-height:1.5">
                本机语音转写与粘贴。持续转写：按住快捷键开始监听。
              </p>
            </div>
          </div>
          <div class="section" style="margin-top:16px"><div class="section-label">运行信息</div><div class="card">{info}</div></div>
        """)))
    v.append(("06", "<strong>手风琴</strong>：品牌、用法、运行信息折叠。",
        shell(nav, f"""
          <div class="hero"><h2>关于 VoiceInk</h2></div>
          <div class="acc open"><button class="acc-head" type="button">品牌与版本 ▾</button>
            <div class="acc-body"><div class="card" style="border:none">{brand}</div></div></div>
          <div class="acc"><button class="acc-head" type="button">用法提示 ▸</button>
            <div class="acc-body">{tip}</div></div>
          <div class="acc"><button class="acc-head" type="button">运行信息 ▸</button>
            <div class="acc-body"><div class="card" style="border:none">{info}</div></div></div>
        """)))
    v.append(("07", "<strong>主从面板</strong>：左选信息类别，右展示详情。",
        shell(nav, f"""
          <div class="hero sm"><h2>关于 VoiceInk</h2></div>
          <div class="split">
            <div class="col card" style="padding:8px">
              <div class="session-item on">品牌</div>
              <div class="session-item">用法</div>
              <div class="session-item">运行信息</div>
            </div>
            <div class="col card">{brand}{tip}</div>
          </div>
        """)))
    v.append(("08", "<strong>扁平分区</strong>：信息铺开，少容器。",
        shell(nav, f"""
          <div class="hero"><h2>关于 VoiceInk</h2><p>版本 0.x.x</p></div>
          {brand}
          <div class="section-label" style="margin-top:16px">用法</div>
          {tip}
          <div class="section-label">运行信息</div>
          <div class="card">{info}</div>
        """)))
    v.append(("09", "<strong>锚点目录</strong>：跳转品牌 / 用法 / 信息。",
        shell(nav, f"""
          <div class="hero"><h2>关于 VoiceInk</h2></div>
          <div class="rail">
            <nav>
              <a class="on" href="#ab">品牌</a>
              <a href="#at">用法</a>
              <a href="#ai">信息</a>
            </nav>
            <div>
              <div id="ab" class="card" style="margin-bottom:14px">{brand}</div>
              <div id="at">{tip}</div>
              <div id="ai" class="section"><div class="section-label">运行信息</div><div class="card">{info}</div></div>
            </div>
          </div>
        """)))
    v.append(("10", "<strong>摘要卡片</strong>：关键状态四格 + 详情。",
        shell(nav, f"""
          <div class="hero"><h2>关于 VoiceInk</h2></div>
          <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
            <div class="stat"><div class="n" style="font-size:15px">SenseVoice</div><div class="l">引擎</div></div>
            <div class="stat"><div class="n" style="font-size:15px">关闭</div><div class="l">润色</div></div>
            <div class="stat"><div class="n" style="font-size:15px">连续</div><div class="l">触发</div></div>
            <div class="stat"><div class="n" style="font-size:15px">就绪</div><div class="l">状态</div></div>
          </div>
          <div class="card">{brand}</div>
          {tip}
          <div class="card" style="margin-top:12px">{info}</div>
        """)))
    return v


def history_variants() -> list[tuple[str, str, str]]:
    sessions = """
              <input class="input" placeholder="搜索会话…" style="margin-bottom:12px" />
              <div class="session-item on">今天 14:32 · 把会议纪要整理一下<span class="session-meta">麦克风 · VS Code · 3 段</span></div>
              <div class="session-item">今天 11:05 · 帮我写一封邮件草稿<span class="session-meta">混合 · Outlook · 2 段</span></div>
              <div class="session-item">昨天 21:18 · 周报要点<span class="session-meta">麦克风 · 记事本 · 5 段</span></div>
              <div class="session-item">07-16 09:40 · 产品评审记录<span class="session-meta">电脑声 · 浏览器 · 8 段</span></div>"""
    detail = """
              <div class="toolbar">
                <div style="flex:1;font-size:16px;font-weight:600">会话详情</div>
                <button class="btn">复制原文</button>
                <button class="btn">复制润色</button>
                <button class="btn btn-primary">导出</button>
                <button class="btn" style="color:var(--text);border-color:#FCA5A5;color:#DC2626">删除</button>
              </div>
              <div class="detail-body">
                <p style="color:var(--text-dim);font-size:12px;margin-bottom:12px">2026-07-19 14:32:10 · 麦克风 · VS Code</p>
                <p>请整理会议纪要，重点写清决议与待办。</p>
                <p style="margin-top:12px">下周三前完成原型评审，并同步给设计组。</p>
              </div>
              <div class="toolbar">
                <button class="btn" style="color:#DC2626;border-color:#FCA5A5">清空全部历史</button>
                <span style="flex:1"></span>
                <button class="btn btn-primary">关闭</button>
              </div>"""

    v = []
    # History is its own window — no settings sidebar
    v.append(("01", "<strong>主从列表</strong>：接近现状。左会话列表，右详情与操作。",
        shell("g", f'<div class="hist-shell"><div class="hist-left"><div style="font-size:22px;font-weight:700;margin-bottom:12px">历史</div>{sessions}</div><div class="hist-right">{detail}</div></div>', hist=True)))
    v.append(("02", "<strong>双栏加宽预览</strong>：列表更窄，正文阅读区更大。",
        shell("g", f'''
          <div class="hist-shell" style="grid-template-columns:260px 1fr">
            <div class="hist-left"><div style="font-size:20px;font-weight:700;margin-bottom:12px">历史</div>{sessions}</div>
            <div class="hist-right">{detail}</div>
          </div>''', hist=True)))
    v.append(("03", "<strong>顶栏筛选</strong>：来源 / 日期筛选条 + 主从。",
        shell("g", f'''
          <div class="hero sm" style="display:flex;justify-content:space-between;align-items:center">
            <h2>历史</h2>
            <div class="seg"><button class="on">全部</button><button>今天</button><button>本周</button></div>
          </div>
          <div class="toolbar" style="margin-bottom:12px">
            <div class="seg"><button class="on">全部来源</button><button>麦克风</button><button>混合</button></div>
            <input class="input" placeholder="搜索会话…" style="max-width:240px;margin-left:auto" />
          </div>
          <div class="hist-shell"><div class="hist-left">{sessions.split('<input')[0] if False else sessions.replace('搜索会话…', '在结果中筛选…')}</div><div class="hist-right">{detail}</div></div>
        ''', hist=True)))
    v.append(("04", "<strong>紧凑表格</strong>：会话表 + 底栏详情抽屉感。",
        shell("g", """
          <div class="hero sm"><h2>历史</h2></div>
          <div class="card" style="padding:0;overflow:auto">
            <table class="table">
              <thead><tr><th>时间</th><th>预览</th><th>来源</th><th>段数</th><th></th></tr></thead>
              <tbody>
                <tr style="background:var(--accent-soft)"><td>今天 14:32</td><td>把会议纪要整理一下</td><td>麦克风</td><td>3</td><td><button class="btn-link">打开</button></td></tr>
                <tr><td>今天 11:05</td><td>帮我写一封邮件草稿</td><td>混合</td><td>2</td><td><button class="btn-link">打开</button></td></tr>
                <tr><td>昨天 21:18</td><td>周报要点</td><td>麦克风</td><td>5</td><td><button class="btn-link">打开</button></td></tr>
              </tbody>
            </table>
          </div>
          <div class="card" style="margin-top:12px;padding:16px">
            <div class="toolbar" style="margin-bottom:10px">
              <strong>把会议纪要整理一下</strong>
              <span style="flex:1"></span>
              <button class="btn">复制</button><button class="btn btn-primary">导出</button>
            </div>
            <p style="font-size:14px;line-height:1.55">请整理会议纪要，重点写清决议与待办。</p>
          </div>
        """, hist=True)))
    v.append(("05", "<strong>三栏</strong>：列表 / 元数据 / 正文。",
        shell("g", f'''
          <div style="display:grid;grid-template-columns:260px 200px 1fr;min-height:560px;background:var(--bg);border-radius:12px;overflow:hidden;border:1px solid var(--border)">
            <div class="hist-left"><div style="font-size:18px;font-weight:700;margin-bottom:12px">历史</div>{sessions}</div>
            <div style="background:var(--surface);border-right:1px solid var(--border);padding:16px">
              <div class="section-label">元数据</div>
              <div class="kv" style="padding:0;grid-template-columns:1fr">
                <div class="k">时间</div><div class="v">今天 14:32</div>
                <div class="k">来源</div><div class="v">麦克风</div>
                <div class="k">应用</div><div class="v">VS Code</div>
                <div class="k">模型</div><div class="v">SenseVoice 小</div>
                <div class="k">段数</div><div class="v">3</div>
              </div>
            </div>
            <div class="hist-right">{detail}</div>
          </div>
        ''', hist=True)))
    v.append(("06", "<strong>卡片瀑布</strong>：会话以卡片网格浏览。",
        shell("g", """
          <div class="hero" style="display:flex;justify-content:space-between;align-items:end">
            <div><h2>历史</h2><p>以卡片浏览近期会话</p></div>
            <input class="input" placeholder="搜索会话…" style="max-width:220px" />
          </div>
          <div class="split3">
            <div class="model-card on"><div class="name" style="font-size:14px">把会议纪要整理一下</div>
              <div class="meta">今天 14:32 · 麦克风 · 3 段</div>
              <div class="desc">请整理会议纪要，重点写清决议与待办。</div>
              <div class="actions"><button class="btn">复制</button><button class="btn btn-primary">导出</button></div></div>
            <div class="model-card"><div class="name" style="font-size:14px">帮我写一封邮件草稿</div>
              <div class="meta">今天 11:05 · 混合 · 2 段</div>
              <div class="desc">请起草一封跟进邮件……</div></div>
            <div class="model-card"><div class="name" style="font-size:14px">周报要点</div>
              <div class="meta">昨天 21:18 · 麦克风 · 5 段</div>
              <div class="desc">本周完成三项……</div></div>
          </div>
        """, hist=True)))
    v.append(("07", "<strong>时间线</strong>：按日分组的时间轴。",
        shell("g", """
          <div class="hero"><h2>历史</h2><p>按时间回顾口述内容</p></div>
          <div class="section-label">今天</div>
          <div class="timeline">
            <div class="item">
              <div class="row-title">14:32 · 把会议纪要整理一下</div>
              <div class="row-desc">麦克风 · VS Code · 3 段</div>
              <div class="card" style="margin-top:8px;padding:12px;font-size:13px">请整理会议纪要，重点写清决议与待办。</div>
            </div>
            <div class="item">
              <div class="row-title">11:05 · 帮我写一封邮件草稿</div>
              <div class="row-desc">混合 · Outlook · 2 段</div>
            </div>
          </div>
          <div class="section-label">昨天</div>
          <div class="timeline">
            <div class="item">
              <div class="row-title">21:18 · 周报要点</div>
              <div class="row-desc">麦克风 · 记事本 · 5 段</div>
            </div>
          </div>
        """, hist=True)))
    v.append(("08", "<strong>扁平分区</strong>：工具条 + 列表 + 详情上下堆叠（窄窗友好）。",
        shell("g", f"""
          <div class="hero sm" style="display:flex;gap:12px;align-items:center">
            <h2>历史</h2>
            <input class="input" placeholder="搜索会话…" style="max-width:260px;margin-left:auto" />
          </div>
          <div class="card" style="padding:8px;margin-bottom:12px">{sessions}</div>
          <div class="card" style="padding:16px">{detail}</div>
        """, hist=True)))
    v.append(("09", "<strong>日期锚点</strong>：左侧日期目录，右侧当日会话。",
        shell("g", f"""
          <div class="hero sm"><h2>历史</h2></div>
          <div class="rail">
            <nav>
              <a class="on" href="#h-today">今天</a>
              <a href="#h-yday">昨天</a>
              <a href="#h-week">本周更早</a>
            </nav>
            <div>
              <div id="h-today" class="section-label">今天</div>
              <div class="hist-shell" style="min-height:360px;border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden">
                <div class="hist-left">{sessions}</div>
                <div class="hist-right">{detail}</div>
              </div>
            </div>
          </div>
        """, hist=True)))
    v.append(("10", "<strong>摘要仪表</strong>：统计 + 最近会话 + 快捷操作。",
        shell("g", f"""
          <div class="hero"><h2>历史</h2><p>本机文本记录，不含音频</p></div>
          <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
            <div class="stat"><div class="n">128</div><div class="l">会话</div></div>
            <div class="stat"><div class="n">4</div><div class="l">今天</div></div>
            <div class="stat"><div class="n">30</div><div class="l">保留天</div></div>
          </div>
          <div class="toolbar" style="margin-bottom:12px">
            <button class="btn btn-primary">导出全部</button>
            <button class="btn">清空全部历史</button>
            <input class="input" placeholder="搜索会话…" style="max-width:220px;margin-left:auto" />
          </div>
          <div class="hist-shell" style="min-height:400px;border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden">
            <div class="hist-left">{sessions}</div>
            <div class="hist-right">{detail}</div>
          </div>
        """, hist=True)))
    return v


def main() -> None:
    specs = [
        (
            "settings-model-variants.html",
            "设置 › 语音识别 · 10 版全貌",
            "覆盖当前引擎、存储路径、已下载/可下载列表。侧栏高亮「语音识别」。",
            model_variants(),
        ),
        (
            "settings-polish-variants.html",
            "设置 › 文字润色 · 10 版全貌",
            "覆盖启用开关、效果预览、接口配置、提示词。侧栏高亮「文本润色」。",
            polish_variants(),
        ),
        (
            "settings-about-variants.html",
            "设置 › 关于 · 10 版全貌",
            "覆盖品牌版本、用法提示、运行信息。侧栏高亮「关于」。",
            about_variants(),
        ),
        (
            "history-variants.html",
            "历史窗口 · 10 版全貌",
            "独立窗口（无设置侧栏）。覆盖搜索、会话列表、详情、导出/删除/清空。",
            history_variants(),
        ),
    ]
    for filename, title, meta, variants in specs:
        path = ROOT / filename
        path.write_text(page(title, meta, variants), encoding="utf-8")
        print(f"wrote {path.name} ({path.stat().st_size} bytes)")

    index = ROOT / "index.html"
    index.write_text(
        """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>VoiceInk · 原型画廊索引</title>
  <style>
    body { font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif; background:#0f1218; color:#e5e7eb; padding:40px 24px; }
    h1 { font-size:20px; margin-bottom:8px; }
    p { color:#9ca3af; font-size:13px; margin-bottom:24px; }
    a { display:block; color:#93c5fd; font-size:15px; padding:10px 0; text-decoration:none; }
    a:hover { color:#fff; }
  </style>
</head>
<body>
  <h1>VoiceInk · 原型画廊</h1>
  <p>每页 10 个布局方案，可切换浅/暗色预览。</p>
  <a href="settings-general-variants.html">设置 › 通用</a>
  <a href="settings-model-variants.html">设置 › 语音识别（模型）</a>
  <a href="settings-polish-variants.html">设置 › 文字润色</a>
  <a href="settings-about-variants.html">设置 › 关于</a>
  <a href="history-variants.html">历史窗口</a>
</body>
</html>
""",
        encoding="utf-8",
    )
    print(f"wrote {index.name}")


if __name__ == "__main__":
    main()
