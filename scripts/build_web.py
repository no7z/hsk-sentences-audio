# -*- coding: utf-8 -*-
"""生成自包含的网页产物到 dist/：
  - data.js       : window.SENTENCES = [...]（供两页用 <script src> 加载，file:// 免 CORS）
  - index.html    : 数据集浏览器（搜索/筛选/播放音频/统计）
  - setup.html    : 开发者落地页（SQL/CSV/Anki 导出、Swift/TS/Kotlin 模型、LLM 提示词生成）

双击 dist/index.html 即可离线使用（音频按相对路径 audio/<id>.mp3 加载）。

用法： python scripts/build_web.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
WL = ROOT / "data/hsk_wordlist"

sys.path.insert(0, str(Path(__file__).resolve().parent))


def coverage_stats(records):
    """覆盖率与校验器口径一致（等级感知分词，而非 jieba token）。"""
    try:
        import hsk_validate as hv
    except Exception:
        return sorted({r["hsk_level"] for r in records}), {}
    word_level, per_level = hv.load_levels("new")
    levels = sorted({r["hsk_level"] for r in records})
    stats = {}
    for lvl in levels:
        target = per_level.get(lvl, set())
        if not target:
            continue
        used = set()
        for r in records:
            if r["hsk_level"] != lvl:
                continue
            for w in hv.hsk_segment(r["chinese"], word_level, lvl):
                if w in target:
                    used.add(w)
        stats[lvl] = (len(used), len(target))
    return levels, stats


def main():
    records = json.loads((DIST / "sentences.json").read_text(encoding="utf-8"))
    levels, stats = coverage_stats(records)

    # 语法点注册表（官方 GF0025-2021 编号/分类/等级）→ 前端标签与分组
    grammar = {}
    reg_path = ROOT / "data/grammar_points.json"
    if reg_path.exists():
        for e in json.loads(reg_path.read_text(encoding="utf-8")):
            grammar[e["id"]] = {"label": e["label"], "full": e["label_full"],
                                "level": e["level"], "cat": e["cat"]}

    # data.js
    (DIST / "data.js").write_text(
        "window.SENTENCES = " + json.dumps(records, ensure_ascii=False) + ";\n"
        "window.META = " + json.dumps({
            "count": len(records),
            "levels": levels,
            "coverage": {str(k): v for k, v in stats.items()},
        }, ensure_ascii=False) + ";\n"
        "window.GRAMMAR = " + json.dumps(grammar, ensure_ascii=False) + ";\n",
        encoding="utf-8")

    (DIST / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (DIST / "setup.html").write_text(SETUP_HTML, encoding="utf-8")
    n = len(records)
    covtxt = "; ".join(f"HSK{k} {v[0]}/{v[1]}" for k, v in stats.items())
    print(f"生成 dist/data.js, index.html, setup.html （{n} 句；覆盖 {covtxt}）")


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>hsk-sentences-audio · 浏览器</title>
<style>
  :root { --bg:#faf9f7; --card:#fff; --ink:#1a1a1a; --sub:#6b6b6b; --accent:#c0392b; --line:#ececec; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--ink); }
  header { padding:22px 24px 10px; }
  h1 { margin:0; font-size:20px; }
  .sub { color:var(--sub); font-size:13px; margin-top:4px; }
  .sub a { color:var(--accent); text-decoration:none; }
  .stats { display:flex; gap:14px; margin-top:12px; flex-wrap:wrap; }
  .stat { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:7px 13px; }
  .stat b { font-size:17px; } .stat span { color:var(--sub); font-size:11.5px; display:block; }
  .layout { display:grid; grid-template-columns:340px 1fr; gap:0 24px; padding:0 24px 60px; align-items:start; }
  /* —— 左侧筛选面板：胶囊横排自动换行 —— */
  aside { position:sticky; top:12px; max-height:calc(100vh - 24px); overflow:auto; padding-bottom:20px; }
  .fgroup { margin-top:16px; }
  .fgroup h3 { font-size:12px; color:var(--sub); margin:0 0 8px; font-weight:600; letter-spacing:1px; }
  .fitems { display:flex; flex-wrap:wrap; gap:6px; }
  .fitem { display:inline-flex; align-items:center; gap:5px; padding:4px 11px; border-radius:999px;
           border:1px solid var(--line); background:#fff; font-size:13px; cursor:pointer;
           user-select:none; color:#333; white-space:nowrap; }
  .fitem:hover { border-color:#d8cfc8; background:#f7f4f1; }
  .fitem.on { background:var(--accent); border-color:var(--accent); color:#fff; }
  .fitem .n { font-size:11px; color:var(--sub); } .fitem.on .n { color:#f3d0ca; }
  .clear { margin-top:14px; width:100%; border:1px dashed var(--line); background:none; color:var(--sub);
           padding:7px; border-radius:8px; font-size:12.5px; cursor:pointer; display:none; }
  .clear.show { display:block; }
  .gcat { display:flex; justify-content:space-between; align-items:center; font-size:12.5px; color:#444;
          padding:5px 9px; margin-top:4px; border-radius:8px; cursor:pointer; user-select:none; }
  .gcat:hover { background:#f1eeea; }
  .gcat .n { font-size:11px; color:var(--sub); }
  /* —— 右侧内容 —— */
  .main { min-width:0; }
  .bar { position:sticky; top:0; background:var(--bg); padding:12px 0; z-index:5; display:flex; gap:10px; align-items:center; }
  input { flex:1; padding:9px 12px; border:1px solid var(--line); border-radius:8px; font-size:14px; background:#fff; }
  .count { color:var(--sub); font-size:13px; white-space:nowrap; }
  #list { display:grid; gap:12px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }
  .zh { font-size:24px; font-weight:600; letter-spacing:1px; }
  .py { color:var(--accent); font-size:15px; margin-top:6px; }
  .en { color:var(--sub); font-size:14px; margin-top:6px; }
  .toks { margin-top:10px; display:flex; gap:8px; flex-wrap:wrap; }
  .tok { background:#f4f2ef; border-radius:6px; padding:4px 8px; font-size:12px; color:#444; }
  .tok b { color:var(--ink); font-size:14px; font-weight:600; }
  .row { display:flex; gap:10px; align-items:center; margin-top:12px; flex-wrap:wrap; }
  .row button { border:none; background:var(--accent); color:#fff; padding:7px 14px; border-radius:8px; font-size:13px; cursor:pointer; }
  .row button.ghost { background:#efecea; color:#333; }
  .tag { display:inline-block; background:#eef4ff; color:#2c5aa0; font-size:11px; padding:2px 8px; border-radius:10px; margin:8px 6px 0 0; }
  @media (max-width:760px) {
    .layout { grid-template-columns:1fr; }
    aside { position:static; max-height:none; }
    .fgroup { display:inline-block; vertical-align:top; margin-right:18px; }
  }
</style>
</head>
<body>
<header>
  <h1>hsk-sentences-audio</h1>
  <div class="sub">中文分级句子 · 拼音 · 翻译 · 逐词词义 · 原生音频 · 依 HSK 3.0 分级 ·
    <a href="setup.html">开发者接入 →</a></div>
  <div class="stats" id="stats"></div>
</header>
<div class="layout">
  <aside id="facets"></aside>
  <div class="main">
    <div class="bar">
      <input id="q" placeholder="搜索汉字 / 拼音 / 英文…">
      <span class="count" id="count"></span>
    </div>
    <div id="list"></div>
  </div>
</div>
<script src="data.js"></script>
<script>
const AUDIO = "audio/";
const ALL = window.SENTENCES || [];
const META = window.META || {};
const TOPIC_ZH = {greetings:"问候礼貌", identity:"人称身份", family:"家庭", numbers:"数字数量",
  time:"时间日期", daily_actions:"日常动作", school_work:"学校工作", location:"地点方位",
  transport:"出行交通", shopping:"购物金钱", food:"饮食", weather_state:"天气状态",
  questions:"提问判断", objects_misc:"物品其他", health_body:"健康身体",
  sports_leisure:"运动文娱", feelings:"情感观点", nature:"自然动物", misc:"其他"};
const TYPE_ZH = {question:"疑问句", imperative:"祈使句", statement:"陈述句"};
const GRAMMAR = window.GRAMMAR || {};   // 官方语法点注册表 {id:{label,full,level,cat}}
const glabel = id => (GRAMMAR[id] && GRAMMAR[id].label) || id;

// 当前筛选状态：每组单选，null = 全部
const state = { lvl:null, topic:null, stype:null, gram:null };

function renderStats() {
  const el = document.getElementById("stats");
  const parts = [`<div class="stat"><b>${META.count||ALL.length}</b><span>句子</span></div>`];
  const cov = META.coverage || {};
  for (const lvl of Object.keys(cov)) {
    const [c,t] = cov[lvl];
    parts.push(`<div class="stat"><b>${Math.round(c/t*100)}%</b><span>HSK${lvl} 词表覆盖 (${c}/${t})</span></div>`);
  }
  parts.push(`<div class="stat"><b>×2</b><span>常速 + 慢速音频</span></div>`);
  el.innerHTML = parts.join("");
}

function searchHay(r) {
  return (r.chinese + r.pinyin + ((r.translation&&r.translation.en)||"") +
          r.tokens.map(t => t.word+t.pinyin+t.gloss_en).join("")).toLowerCase();
}

// except=某组时忽略该组自身的筛选(标准 faceted-search 联动口径)
function matches(r, except) {
  if (except!=="lvl"   && state.lvl   && String(r.hsk_level)!==state.lvl) return false;
  if (except!=="topic" && state.topic && r.topic!==state.topic) return false;
  if (except!=="stype" && state.stype && r.sentence_type!==state.stype) return false;
  if (except!=="gram"  && state.gram  && !(r.grammar_tags||[]).includes(state.gram)) return false;
  const qEl = document.getElementById("q");
  const q = qEl ? qEl.value.trim().toLowerCase() : "";
  if (q && !searchHay(r).includes(q)) return false;
  return true;
}

// 联动计数：其他组的筛选 + 搜索都生效后再统计本组各项
function counts(fn, except) {
  const m = {}; let total = 0;
  for (const r of ALL) {
    if (!matches(r, except)) continue;
    total++;
    const vs = fn(r);
    (Array.isArray(vs)?vs:[vs]).forEach(v => m[v]=(m[v]||0)+1);
  }
  return {m, total};
}

function facetGroup(title, key, c, labelOf, sortByCount=true) {
  const cm = c.m;
  let keys = Object.keys(cm).filter(v => cm[v] > 0);
  if (state[key] !== null && !keys.includes(state[key])) keys.push(state[key]);
  if (sortByCount) keys.sort((a,b)=>(cm[b]||0)-(cm[a]||0)); else keys.sort();
  let html = `<div class="fgroup"><h3>${title}</h3><div class="fitems">`;
  html += `<div class="fitem ${state[key]===null?"on":""}" data-k="${key}" data-v="">全部<span class="n">${c.total}</span></div>`;
  for (const v of keys) {
    html += `<div class="fitem ${state[key]===v?"on":""}" data-k="${key}" data-v="${v}">${labelOf(v)}<span class="n">${cm[v]||0}</span></div>`;
  }
  return html + `</div></div>`;
}

let gramQuery = "";
const gramOpen = {};   // 分类 -> 是否展开（默认全部收起，手风琴）

function grammarFacet(c) {
  const cm = c.m;
  // 可见集：联动计数>0（或当前选中）；已选等级时只显示该等级及以下引入的语法点
  let ids = Object.keys(cm).filter(g => cm[g] > 0);
  if (state.gram && !ids.includes(state.gram)) ids.push(state.gram);
  if (state.lvl) ids = ids.filter(g => !GRAMMAR[g] || GRAMMAR[g].level <= Number(state.lvl));
  if (gramQuery) ids = ids.filter(g => (glabel(g) + (GRAMMAR[g]?GRAMMAR[g].full:"")).includes(gramQuery));
  ids.sort((a,b) => (cm[b]||0)-(cm[a]||0));
  const groups = {};
  for (const g of ids) {
    const cat = (GRAMMAR[g] && GRAMMAR[g].cat) || "其他";
    (groups[cat] = groups[cat] || []).push(g);
  }
  let html = `<div class="fgroup"><h3>语法点 <span style="font-weight:400">(官方 GF0025-2021)</span></h3>
    <input id="gq" placeholder="搜语法点…" value="${gramQuery}"
      style="width:100%;margin:0 0 6px;padding:5px 9px;border:1px solid var(--line);border-radius:8px;font-size:12.5px;">
    <div class="fitems"><div class="fitem ${state.gram===null?"on":""}" data-k="gram" data-v="">全部<span class="n">${c.total}</span></div></div>`;
  const cats = Object.keys(groups).sort((a,b) =>
    groups[b].reduce((s,g)=>s+(cm[g]||0),0) - groups[a].reduce((s,g)=>s+(cm[g]||0),0));
  for (const cat of cats) {
    // 搜索时全部展开；选中项所在分类保持展开；其余按手风琴状态
    const open = !!gramQuery || gramOpen[cat] || groups[cat].includes(state.gram);
    const sum = groups[cat].reduce((s,g)=>s+(cm[g]||0),0);
    html += `<div class="gcat" data-cat="${cat}"><span>${open?"▾":"▸"} ${cat}</span><span class="n">${groups[cat].length}项 · ${sum}</span></div>`;
    if (open) {
      html += `<div class="fitems" style="margin:2px 0 4px 8px;">`;
      for (const g of groups[cat]) {
        const lv = GRAMMAR[g] ? `HSK${GRAMMAR[g].level}·` : "";
        html += `<div class="fitem ${state.gram===g?"on":""}" data-k="gram" data-v="${g}" title="${lv}${GRAMMAR[g]?GRAMMAR[g].full:g}">${glabel(g)}<span class="n">${cm[g]||0}</span></div>`;
      }
      html += `</div>`;
    }
  }
  return html + `</div>`;
}

function renderFacets() {
  const el = document.getElementById("facets");
  el.innerHTML =
    facetGroup("等级", "lvl", counts(r=>String(r.hsk_level), "lvl"), v=>"HSK "+v, false) +
    facetGroup("主题", "topic", counts(r=>r.topic, "topic"), v=>TOPIC_ZH[v]||v) +
    facetGroup("句型", "stype", counts(r=>r.sentence_type, "stype"), v=>TYPE_ZH[v]||v) +
    grammarFacet(counts(r=>r.grammar_tags||[], "gram")) +
    `<button class="clear ${Object.values(state).some(v=>v)?"show":""}" id="clearBtn">✕ 清除全部筛选</button>`;
  el.querySelectorAll(".fitem[data-k]").forEach(it => it.onclick = () => {
    const k = it.dataset.k, v = it.dataset.v || null;
    state[k] = (state[k] === v) ? null : v;   // 点已选中的再点一次 = 取消
    renderFacets(); applyFilter();
  });
  el.querySelectorAll(".gcat").forEach(it => it.onclick = () => {
    gramOpen[it.dataset.cat] = !gramOpen[it.dataset.cat];
    renderFacets();
  });
  const gq = document.getElementById("gq");
  if (gq) {
    gq.oninput = () => { gramQuery = gq.value.trim(); renderFacets();
      const el2 = document.getElementById("gq"); el2.focus(); el2.setSelectionRange(el2.value.length, el2.value.length); };
  }
  const cb = document.getElementById("clearBtn");
  if (cb) cb.onclick = () => { for (const k in state) state[k]=null; gramQuery=""; renderFacets(); applyFilter(); };
}

function render(items) {
  const list = document.getElementById("list");
  list.innerHTML = "";
  document.getElementById("count").textContent = items.length + " 句";
  const frag = document.createDocumentFragment();
  for (const r of items) {
    const card = document.createElement("div");
    card.className = "card";
    const toks = r.tokens.map(t => `<span class="tok"><b>${t.word}</b> ${t.pinyin}${t.gloss_en ? " · " + t.gloss_en : ""}</span>`).join("");
    const tags = (r.grammar_tags||[]).map(g => `<span class="tag" title="${GRAMMAR[g]?GRAMMAR[g].full:g}">${glabel(g)}</span>`).join("");
    card.innerHTML = `
      <div class="zh">${r.chinese}</div>
      <div class="py">${r.pinyin}</div>
      <div class="en">${(r.translation&&r.translation.en)||""}　·　繁：${r.traditional}</div>
      <div class="toks">${toks}</div>${tags}
      <div class="row">
        <button data-a="${AUDIO + r.id}.mp3">▶ 常速</button>
        <button class="ghost" data-a="${AUDIO + r.id}_slow.mp3">▶ 慢速</button>
        <span class="count">HSK ${r.hsk_level} · ${TOPIC_ZH[r.topic]||r.topic} · ${TYPE_ZH[r.sentence_type]||""} · ${r.id}</span>
      </div>`;
    frag.appendChild(card);
  }
  list.appendChild(frag);
  list.querySelectorAll(".row button").forEach(b => b.onclick = () => new Audio(b.dataset.a).play());
}

function applyFilter() {
  render(ALL.filter(r => matches(r, null)));
}

renderStats();
renderFacets();
// 搜索也参与联动：结果与所有 facet 计数同时刷新
document.getElementById("q").oninput = () => { applyFilter(); renderFacets(); };
render(ALL);
</script>
</body>
</html>
"""

SETUP_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>hsk-sentences-audio · 开发者接入</title>
<style>
  :root { --bg:#faf9f7; --card:#fff; --ink:#1a1a1a; --sub:#6b6b6b; --accent:#c0392b; --line:#ececec; --code:#1e1e1e; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--ink); }
  .wrap { max-width:860px; margin:0 auto; padding:24px 20px 80px; }
  h1 { font-size:22px; margin:0 0 4px; }
  h2 { font-size:17px; margin:34px 0 10px; padding-top:10px; border-top:1px solid var(--line); }
  .sub { color:var(--sub); font-size:13px; }
  a { color:var(--accent); }
  .btns { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0; }
  button, select { border:1px solid var(--line); background:#fff; color:var(--ink); padding:8px 14px; border-radius:8px; font-size:13px; cursor:pointer; }
  button.p { background:var(--accent); color:#fff; border:none; }
  pre { background:var(--code); color:#eaeaea; padding:14px; border-radius:10px; overflow:auto; font-size:12.5px; line-height:1.5; position:relative; }
  pre .copy { position:absolute; top:8px; right:8px; background:#333; color:#ccc; border:none; padding:4px 10px; font-size:11px; border-radius:6px; }
  .field { margin:8px 0; } label { font-size:13px; color:var(--sub); margin-right:8px; }
  .note { background:#fff8f0; border:1px solid #f0d9c0; border-radius:8px; padding:10px 12px; font-size:13px; color:#7a5a30; }
</style>
</head>
<body>
<div class="wrap">
  <h1>开发者接入指南</h1>
  <div class="sub">把这个数据集接进你的应用：<b id="cnt"></b> 句 · 每句含拼音/翻译/逐词词义/常速+慢速音频 · <a href="index.html">← 返回浏览器</a></div>

  <h2>1 · 拿数据</h2>
  <div class="sub">整个数据集是 <code>dist/sentences.json</code> + <code>dist/audio/&lt;id&gt;.mp3</code>。也可在本页一键导出到你熟悉的格式：</div>
  <div class="btns">
    <button class="p" onclick="dl('sentences.json', JSON.stringify(SENTENCES,null,2))">下载 sentences.json</button>
    <button onclick="dl('sentences.csv', toCSV())">下载 CSV（句级）</button>
    <button onclick="dl('anki.txt', toAnki())">下载 Anki 导入文件</button>
  </div>
  <div class="note">Anki：新建牌组 → 导入 → 选“Fields separated by: Tab”，字段顺序为 正面(汉字) / 拼音 / 英文 / 音频。音频文件需一并放入 Anki media 目录。</div>

  <h2>2 · 导入数据库</h2>
  <div class="field">
    <label>数据库</label>
    <select id="db" onchange="renderSQL()">
      <option value="sqlite">SQLite</option>
      <option value="postgres">PostgreSQL</option>
      <option value="mysql">MySQL</option>
    </select>
    <button onclick="dl('schema_'+db()+'.sql', sqlText)">下载 .sql</button>
  </div>
  <pre id="sql"><button class="copy" onclick="cp('sql')">复制</button><code></code></pre>

  <h2>3 · 数据模型（复制即用）</h2>
  <div class="field">
    <label>语言</label>
    <select id="lang" onchange="renderModel()">
      <option value="swift">Swift (Codable)</option>
      <option value="ts">TypeScript</option>
      <option value="kotlin">Kotlin</option>
    </select>
  </div>
  <pre id="model"><button class="copy" onclick="cp('model')">复制</button><code></code></pre>

  <h2>4 · Ask your LLM（让 AI 帮你搭）</h2>
  <div class="sub">选一个目标，生成一段自带数据结构说明的提示词，直接丢给你的 AI：</div>
  <div class="field">
    <label>我想做</label>
    <select id="goal" onchange="renderPrompt()">
      <option value="ios">iOS 闪卡/SRS App（SwiftUI）</option>
      <option value="api">FastAPI 后端 + 检索接口</option>
      <option value="web">网页版跟读练习（React）</option>
    </select>
  </div>
  <pre id="prompt"><button class="copy" onclick="cp('prompt')">复制提示词</button><code></code></pre>
</div>

<script src="data.js"></script>
<script>
const SENTENCES = window.SENTENCES || [];
document.getElementById("cnt").textContent = SENTENCES.length;
const db = () => document.getElementById("db").value;
let sqlText = "";

function dl(name, text) {
  const b = new Blob([text], {type:"text/plain;charset=utf-8"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = name; a.click();
}
function cp(id){ const t = document.querySelector("#"+id+" code").innerText; navigator.clipboard.writeText(t); }
function esc(s){ return String(s==null?"":s).replace(/'/g,"''"); }
function csvCell(s){ return '"' + String(s==null?"":s).replace(/"/g,'""') + '"'; }

function toCSV(){
  const head = ["id","hsk_level","chinese","traditional","pinyin","pinyin_numbered","english","audio_normal","audio_slow"];
  const rows = [head.join(",")];
  for (const r of SENTENCES) rows.push([r.id,r.hsk_level,r.chinese,r.traditional,r.pinyin,r.pinyin_numbered,(r.translation&&r.translation.en)||"",r.audio.normal,r.audio.slow].map(csvCell).join(","));
  return rows.join("\n");
}
function toAnki(){
  // 正面(汉字) \t 拼音 \t 英文 \t [sound:xxx.mp3]
  return SENTENCES.map(r => [r.chinese, r.pinyin, (r.translation&&r.translation.en)||"", "[sound:"+r.id+".mp3]"].join("\t")).join("\n");
}

function renderSQL(){
  const d = db();
  const TEXT = d==="mysql" ? "TEXT" : "TEXT";
  const AUTO = "";
  let s = "";
  if (d==="postgres" || d==="sqlite") {
    s += "CREATE TABLE sentences (\n  id TEXT PRIMARY KEY,\n  hsk_level INTEGER,\n  chinese TEXT,\n  traditional TEXT,\n  pinyin TEXT,\n  pinyin_numbered TEXT,\n  english TEXT,\n  audio_normal TEXT,\n  audio_slow TEXT\n);\n";
    s += "CREATE TABLE tokens (\n  sentence_id TEXT,\n  position INTEGER,\n  word TEXT,\n  pinyin TEXT,\n  gloss_en TEXT\n);\n\n";
  } else {
    s += "CREATE TABLE sentences (\n  id VARCHAR(32) PRIMARY KEY,\n  hsk_level INT,\n  chinese VARCHAR(255),\n  traditional VARCHAR(255),\n  pinyin VARCHAR(255),\n  pinyin_numbered VARCHAR(255),\n  english VARCHAR(512),\n  audio_normal VARCHAR(128),\n  audio_slow VARCHAR(128)\n) CHARACTER SET utf8mb4;\n";
    s += "CREATE TABLE tokens (\n  sentence_id VARCHAR(32),\n  position INT,\n  word VARCHAR(64),\n  pinyin VARCHAR(64),\n  gloss_en VARCHAR(512)\n) CHARACTER SET utf8mb4;\n\n";
  }
  for (const r of SENTENCES) {
    s += `INSERT INTO sentences VALUES ('${esc(r.id)}',${r.hsk_level},'${esc(r.chinese)}','${esc(r.traditional)}','${esc(r.pinyin)}','${esc(r.pinyin_numbered)}','${esc((r.translation&&r.translation.en)||"")}','${esc(r.audio.normal)}','${esc(r.audio.slow)}');\n`;
    r.tokens.forEach((t,i) => { s += `INSERT INTO tokens VALUES ('${esc(r.id)}',${i},'${esc(t.word)}','${esc(t.pinyin)}','${esc(t.gloss_en)}');\n`; });
  }
  sqlText = s;
  document.querySelector("#sql code").textContent = s.length > 4000 ? s.slice(0,4000) + "\n... （完整内容见下载）" : s;
}

function renderModel(){
  const lang = document.getElementById("lang").value;
  let c = "";
  if (lang==="swift") {
    c = `struct Sentence: Codable, Identifiable {
    let id: String
    let hskLevel: Int
    let chinese: String
    let traditional: String
    let pinyin: String
    let translation: Translation
    let tokens: [Token]
    let audio: Audio

    enum CodingKeys: String, CodingKey {
        case id, chinese, traditional, pinyin, translation, tokens, audio
        case hskLevel = "hsk_level"
    }
}
struct Translation: Codable { let en: String }
struct Token: Codable { let word, pinyin, glossEn: String
    enum CodingKeys: String, CodingKey { case word, pinyin; case glossEn = "gloss_en" } }
struct Audio: Codable { let normal, slow: String }

// 加载：
let url = Bundle.main.url(forResource: "sentences", withExtension: "json")!
let data = try Data(contentsOf: url)
let sentences = try JSONDecoder().decode([Sentence].self, from: data)`;
  } else if (lang==="ts") {
    c = `export interface Token { word: string; pinyin: string; gloss_en: string; }
export interface Sentence {
  id: string;
  hsk_level: number;
  chinese: string;
  traditional: string;
  pinyin: string;
  pinyin_numbered: string;
  translation: { en: string };
  tokens: Token[];
  grammar_points: string[];
  audio: { normal: string; slow: string };
}
import data from "./sentences.json";
export const sentences: Sentence[] = data as Sentence[];`;
  } else {
    c = `@Serializable
data class Sentence(
    val id: String,
    @SerialName("hsk_level") val hskLevel: Int,
    val chinese: String,
    val traditional: String,
    val pinyin: String,
    val translation: Translation,
    val tokens: List<Token>,
    val audio: Audio,
)
@Serializable data class Translation(val en: String)
@Serializable data class Token(val word: String, val pinyin: String, @SerialName("gloss_en") val glossEn: String)
@Serializable data class Audio(val normal: String, val slow: String)`;
  }
  document.querySelector("#model code").textContent = c;
}

function renderPrompt(){
  const goal = document.getElementById("goal").value;
  const schema = `每条记录：{ id, hsk_level, chinese(简体), traditional(繁体), pinyin(带声调,已处理轻声/儿化/多音字), pinyin_numbered, translation:{en}, tokens:[{word,pinyin,gloss_en}], grammar_points:[], audio:{normal,slow} }。音频文件在 audio/<id>.mp3 与 audio/<id>_slow.mp3。`;
  const map = {
    ios: `我有一个中文学习数据集（sentences.json + audio/ 目录）。${schema}\n请用 SwiftUI 写一个离线闪卡/SRS 应用：卡片正面显示汉字，点击播放常速音频、长按播放慢速；背面显示拼音、英文和逐词词义；实现一个简单的 SM-2 间隔重复算法按 hsk_level 由易到难排程。给出完整可编译的 Swift 代码和 JSON 解码模型。`,
    api: `我有一个中文学习数据集 sentences.json。${schema}\n请用 FastAPI 写一个后端：启动时加载 JSON，提供 GET /sentences?level=&q=（按 HSK 等级过滤 + 汉字/拼音/英文模糊搜索，支持分页 page/limit）、GET /sentences/{id}、GET /audio/{id} 返回 mp3。给出完整 main.py 和 Pydantic 模型。`,
    web: `我有一个中文学习数据集 sentences.json + audio/。${schema}\n请用 React 写一个网页跟读练习：列出句子，点击播放常速/慢速音频，显示拼音和逐词词义，可按 HSK 等级筛选和搜索。给出完整组件代码。`,
  };
  document.querySelector("#prompt code").textContent = map[goal];
}

renderSQL(); renderModel(); renderPrompt();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
