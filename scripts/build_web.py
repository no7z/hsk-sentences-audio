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
from hashlib import sha256
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
    word_level, per_level = hv.load_levels("new", maxlvl=6)
    legacy_word_level = dict(word_level)
    # Keep advanced spelling coverage on the pinned 2021 transcription rather
    # than silently using the smaller community new_7.json denominator.
    advanced_path = ROOT / "data/standards/gf0025-2021-7-9.txt"
    if advanced_path.exists():
        per_level[7] = set(advanced_path.read_text(encoding="utf-8").splitlines())
        for word in per_level[7]:
            word_level.setdefault(word, 7)
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
            table = word_level if lvl == 7 else legacy_word_level
            maxlen = max(map(len, table)) if lvl == 7 else 6
            for w in hv.hsk_segment(r["chinese"], table, lvl, maxlen=maxlen):
                if w in target:
                    used.add(w)
        stats[lvl] = (len(used), len(target))
    return levels, stats


def main():
    records = json.loads((DIST / "sentences.json").read_text(encoding="utf-8"))
    levels, stats = coverage_stats(records)

    # 语法点注册表（官方 GF0025-2021 编号/分类/等级）→ 前端标签与分组
    grammar = {}
    translations = json.loads((ROOT / "data/grammar_i18n_en.json").read_text(encoding="utf-8"))
    used_ids = {tag for record in records for tag in record.get("grammar_tags", [])}
    missing = used_ids - translations["points"].keys()
    if missing:
        raise ValueError(f"Missing English grammar labels: {sorted(missing)}")
    reg_path = ROOT / "data/grammar_points.json"
    if reg_path.exists():
        for e in json.loads(reg_path.read_text(encoding="utf-8")):
            grammar[e["id"]] = {"label": e["label"], "full": e["label_full"],
                                "level": e["level"], "cat": e["cat"],
                                "label_en": translations["points"].get(e["id"], {}).get("label"),
                                "full_en": translations["points"].get(e["id"], {}).get("full")}
    missing_categories = {grammar[tag]["cat"] for tag in used_ids} - translations["categories"].keys()
    if missing_categories:
        raise ValueError(f"Missing English grammar categories: {sorted(missing_categories)}")

    # data.js
    (DIST / "data.js").write_text(
        "window.SENTENCES = " + json.dumps(records, ensure_ascii=False) + ";\n"
        "window.META = " + json.dumps({
            "count": len(records),
            "levels": levels,
            "coverage": {str(k): v for k, v in stats.items()},
        }, ensure_ascii=False) + ";\n"
        "window.GRAMMAR = " + json.dumps(grammar, ensure_ascii=False) + ";\n"
        "window.GRAMMAR_CATEGORIES_EN = " + json.dumps(translations["categories"], ensure_ascii=False) + ";\n",
        encoding="utf-8", newline="\n")

    # Change the script URL when its content changes so cached Chinese-only
    # grammar metadata cannot hide a newly deployed English interface.
    data_version = sha256((DIST / "data.js").read_bytes()).hexdigest()[:12]
    for name, template in (("index.html", INDEX_HTML), ("setup.html", SETUP_HTML)):
        (DIST / name).write_text(template.replace('src="data.js"',
                                f'src="data.js?v={data_version}"'), encoding="utf-8", newline="\n")
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
           user-select:none; color:#333; white-space:normal; max-width:100%; }
  .fitem:hover { border-color:#d8cfc8; background:#f7f4f1; }
  .fitem.on { background:var(--accent); border-color:var(--accent); color:#fff; }
  .fitem .n { font-size:11px; color:var(--sub); flex-shrink:0; white-space:nowrap; } .fitem.on .n { color:#f3d0ca; }
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
  .more { display:block; margin:14px auto 4px; padding:8px 18px; border:1px solid var(--line); background:var(--card);
          color:var(--sub); border-radius:999px; font-size:13px; cursor:pointer; }
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
  <h1>hsk-sentences-audio
    <button id="langBtn" style="float:right;border:1px solid var(--line);background:#fff;color:#555;
      padding:4px 12px;border-radius:999px;font-size:12.5px;cursor:pointer;"></button></h1>
  <div class="sub" id="sub"></div>
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
// —— i18n：右上角切换，localStorage 记忆 ——
const LANG = localStorage.getItem("hsa_lang") || "zh";
const T = (zh, en) => LANG === "zh" ? zh : en;
document.documentElement.lang = T("zh-Hans", "en");
const TOPIC_L = {greetings:["问候礼貌","Greetings"], identity:["人称身份","People & Identity"],
  family:["家庭","Family"], numbers:["数字数量","Numbers"], time:["时间日期","Time & Dates"],
  daily_actions:["日常动作","Daily Actions"], school_work:["学校工作","School & Work"],
  location:["地点方位","Places"], transport:["出行交通","Transport"], shopping:["购物金钱","Shopping & Money"],
  food:["饮食","Food & Drink"], weather_state:["天气状态","Weather"], questions:["提问判断","Questions"],
  objects_misc:["物品其他","Objects & Misc"], health_body:["健康身体","Health & Body"],
  sports_leisure:["运动文娱","Sports & Leisure"], feelings:["情感观点","Feelings & Opinions"],
  nature:["自然动物","Nature & Animals"], misc:["其他","Misc"]};
Object.assign(TOPIC_L, {society:["社会公共事务","Society & Public Affairs"],
  economy:["经济产业","Economy & Industry"], science:["科技信息","Science & Technology"],
  culture:["文化艺术","Culture & Arts"]});
const TYPE_L = {question:["疑问句","Question"], imperative:["祈使句","Imperative"], statement:["陈述句","Statement"]};
const tlabel = v => (TOPIC_L[v] ? TOPIC_L[v][LANG==="zh"?0:1] : v);
const slabel = v => (TYPE_L[v] ? TYPE_L[v][LANG==="zh"?0:1] : v);
const GRAMMAR = window.GRAMMAR || {}; // Chinese source terminology is retained alongside English teaching labels.
const GRAMMAR_CATEGORIES_EN = window.GRAMMAR_CATEGORIES_EN || {};
const glabel = id => GRAMMAR[id] ? T(GRAMMAR[id].label, GRAMMAR[id].label_en || GRAMMAR[id].label) : id;
const gcatlabel = cat => T(cat, GRAMMAR_CATEGORIES_EN[cat] || cat);
const gtitle = id => {
  const g = GRAMMAR[id];
  if (!g) return id;
  return `${id} · HSK ${g.level}\n` + T(g.full, `${g.full_en || g.full}\nChinese source: ${g.full}`);
};
const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const hanMarkup = value => escapeHtml(value).replace(/[\u3400-\u9fff\uf900-\ufaff]+/g, s => `<span lang="zh-Hans">${s}</span>`);
function grammarMatches(id, query) {
  const g = GRAMMAR[id] || {};
  return [id, g.label, g.full, g.label_en, g.full_en, g.cat, GRAMMAR_CATEGORIES_EN[g.cat]]
    .filter(Boolean).join(" ").toLowerCase().includes(query.trim().toLowerCase());
}

// 当前筛选状态：每组单选，null = 全部
const state = { lvl:null, exam:null, topic:null, stype:null, gram:null };
const examKey = r => r.exam_vocab_level_2025 == null ? "ungraded" : String(r.exam_vocab_level_2025);
const levelLabel = v => v === "7" ? "HSK 7–9" : "HSK " + v;
const examLabel = v => v === "ungraded" ? T("未估算", "Not estimated") : levelLabel(v);

function renderStats() {
  const el = document.getElementById("stats");
  const parts = [`<div class="stat"><b>${META.count||ALL.length}</b><span>${T("句子","sentences")}</span></div>`];
  const cov = META.coverage || {};
  for (const lvl of Object.keys(cov)) {
    const [c,t] = cov[lvl];
    parts.push(`<div class="stat"><b>${Math.floor(c/t*100)}%</b><span>${T(`原 HSK${lvl} 词表覆盖`,`Authored HSK${lvl} wordlist coverage`)} (${c}/${t})</span></div>`);
  }
  parts.push(`<div class="stat"><b>×2</b><span>${T("常速 + 慢速音频","normal + slow audio")}</span></div>`);
  el.innerHTML = parts.join("");
}

// 搜索文本每句只拼一次（近万句时每次按键重拼会明显卡顿）
const HAY = new Map();
function searchHay(r) {
  let h = HAY.get(r);
  if (h === undefined) {
    h = (r.chinese + r.pinyin + ((r.translation&&r.translation.en)||"") +
         r.tokens.map(t => t.word+t.pinyin+t.gloss_en).join("")).toLowerCase();
    HAY.set(r, h);
  }
  return h;
}
function currentQuery() {
  const qEl = document.getElementById("q");
  return qEl ? qEl.value.trim().toLowerCase() : "";
}

// except=某组时忽略该组自身的筛选(标准 faceted-search 联动口径)；q 省略时读搜索框
function matches(r, except, q) {
  if (except!=="lvl"   && state.lvl   && String(r.hsk_level)!==state.lvl) return false;
  if (except!=="exam"  && state.exam  && examKey(r)!==state.exam) return false;
  if (except!=="topic" && state.topic && r.topic!==state.topic) return false;
  if (except!=="stype" && state.stype && r.sentence_type!==state.stype) return false;
  if (except!=="gram"  && state.gram  && !(r.grammar_tags||[]).includes(state.gram)) return false;
  if (q === undefined) q = currentQuery();
  if (q && !searchHay(r).includes(q)) return false;
  return true;
}

// 联动计数：其他组的筛选 + 搜索都生效后再统计本组各项
function counts(fn, except) {
  const m = {}; let total = 0;
  const q = currentQuery();
  for (const r of ALL) {
    if (!matches(r, except, q)) continue;
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
  html += `<div class="fitem ${state[key]===null?"on":""}" role="button" tabindex="0" aria-pressed="${state[key]===null}" data-k="${key}" data-v="">${T("全部","All")}<span class="n">${c.total}</span></div>`;
  for (const v of keys) {
    html += `<div class="fitem ${state[key]===v?"on":""}" role="button" tabindex="0" aria-pressed="${state[key]===v}" data-k="${key}" data-v="${v}">${labelOf(v)}<span class="n">${cm[v]||0}</span></div>`;
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
  if (gramQuery) ids = ids.filter(g => grammarMatches(g, gramQuery));
  ids.sort((a,b) => (cm[b]||0)-(cm[a]||0));
  const groups = {};
  for (const g of ids) {
    const cat = (GRAMMAR[g] && GRAMMAR[g].cat) || "其他";
    (groups[cat] = groups[cat] || []).push(g);
  }
  let html = `<div class="fgroup"><h3>${T("语法点","Grammar points")} <span style="font-weight:400">(${T("官方","official")} GF0025-2021)</span></h3>
    <p class="sub">${T("英文为辅助译名；悬浮查看原始术语与编号。", "English labels are teaching aids; hover for Chinese source terms and IDs.")}</p>
    <input id="gq" aria-label="${T("搜索语法点", "Search grammar points")}" placeholder="${T("搜语法点、英文或编号…","Search grammar in English, Chinese or by ID…")}" value="${escapeHtml(gramQuery)}"
      style="width:100%;margin:0 0 6px;padding:5px 9px;border:1px solid var(--line);border-radius:8px;font-size:12.5px;">
    <div class="fitems"><div class="fitem ${state.gram===null?"on":""}" role="button" tabindex="0" aria-pressed="${state.gram===null}" data-k="gram" data-v="">${T("全部","All")}<span class="n">${c.total}</span></div></div>`;
  const cats = Object.keys(groups).sort((a,b) =>
    groups[b].reduce((s,g)=>s+(cm[g]||0),0) - groups[a].reduce((s,g)=>s+(cm[g]||0),0));
  if (!cats.length) html += `<p class="sub" role="status">${T("没有匹配的语法点", "No matching grammar points")}</p>`;
  for (const cat of cats) {
    // 搜索时全部展开；选中项所在分类保持展开；其余按手风琴状态
    const open = !!gramQuery || gramOpen[cat] || groups[cat].includes(state.gram);
    const sum = groups[cat].reduce((s,g)=>s+(cm[g]||0),0);
    html += `<div class="gcat" role="button" tabindex="0" aria-expanded="${open}" data-cat="${escapeHtml(cat)}"><span>${open?"▾":"▸"} ${escapeHtml(gcatlabel(cat))}</span><span class="n" title="${T("语法点数量 · 匹配次数", "Grammar points · matches")}">${T(`${groups[cat].length}项 · ${sum}次`,`${groups[cat].length} ${groups[cat].length===1?"pt":"pts"} · ${sum} ${sum===1?"match":"matches"}`)}</span></div>`;
    if (open) {
      html += `<div class="fitems" style="margin:2px 0 4px 8px;">`;
      for (const g of groups[cat]) {
        html += `<div class="fitem ${state.gram===g?"on":""}" role="button" tabindex="0" aria-pressed="${state.gram===g}" data-k="gram" data-v="${g}" title="${escapeHtml(gtitle(g))}"><span>${hanMarkup(glabel(g))}</span><span class="n">${cm[g]||0}</span></div>`;
      }
      html += `</div>`;
    }
  }
  return html + `</div>`;
}

function renderFacets() {
  const el = document.getElementById("facets");
  el.innerHTML =
    facetGroup(T("原编排 · 2021 标准","Authored · 2021 standard"), "lvl", counts(r=>String(r.hsk_level), "lvl"), levelLabel, false) +
    facetGroup(T("考试词汇估算 · 2025 大纲","Exam vocabulary · 2025 syllabus"), "exam", counts(examKey, "exam"), examLabel, false) +
    `<p class="sub">${T("词汇估算不等于官方句子等级；不判断语法或词义。两组等级可交叉筛选。7–9 为合并档。", "Vocabulary estimates are not official sentence grades; grammar and word senses are not assessed. Combine both level filters to compare. 7–9 is one band.")}</p>` +
    facetGroup(T("主题","Topic"), "topic", counts(r=>r.topic, "topic"), tlabel) +
    facetGroup(T("句型","Sentence type"), "stype", counts(r=>r.sentence_type, "stype"), slabel) +
    grammarFacet(counts(r=>r.grammar_tags||[], "gram")) +
    `<button class="clear ${Object.values(state).some(v=>v)?"show":""}" id="clearBtn">${T("✕ 清除全部筛选","✕ Clear all filters")}</button>`;
  el.querySelectorAll(".fitem[data-k]").forEach(it => it.onclick = () => {
    const k = it.dataset.k, v = it.dataset.v || null;
    state[k] = (state[k] === v) ? null : v;   // 点已选中的再点一次 = 取消
    renderFacets(); applyFilter();
  });
  el.querySelectorAll('.fitem[role="button"]').forEach(it => it.onkeydown = e => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); it.click(); }
  });
  el.querySelectorAll(".gcat").forEach(it => it.onclick = () => {
    gramOpen[it.dataset.cat] = !gramOpen[it.dataset.cat];
    renderFacets();
  });
  el.querySelectorAll('.gcat[role="button"]').forEach(it => it.onkeydown = e => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); it.click(); }
  });
  const gq = document.getElementById("gq");
  if (gq) {
    gq.oninput = () => { gramQuery = gq.value.trim(); renderFacets();
      const el2 = document.getElementById("gq"); el2.focus(); el2.setSelectionRange(el2.value.length, el2.value.length); };
  }
  const cb = document.getElementById("clearBtn");
  if (cb) cb.onclick = () => { for (const k in state) state[k]=null; gramQuery=""; renderFacets(); applyFilter(); };
}

// 结果分批渲染：一次只生成 PAGE 张卡片，滚到底部再追加（近万张卡片一次性排版要好几秒）
const PAGE = 60;
let shown = [], shownCount = 0, moreObserver = null;
function render(items) {
  const list = document.getElementById("list");
  list.innerHTML = "";
  document.getElementById("count").textContent = items.length + T(" 句", " sentences");
  shown = items; shownCount = 0;
  renderMore();
}
function renderMore() {
  const list = document.getElementById("list");
  const old = document.getElementById("more");
  if (old) old.remove();
  const end = Math.min(shown.length, shownCount + PAGE);
  const frag = document.createDocumentFragment();
  for (const r of shown.slice(shownCount, end)) {
    const card = document.createElement("div");
    card.className = "card";
    const toks = r.tokens.map(t => `<span class="tok"><b lang="zh-Hans">${t.word}</b> ${t.pinyin}${t.gloss_en ? " · " + t.gloss_en : ""}</span>`).join("");
    const tags = (r.grammar_tags||[]).map(g => `<span class="tag" title="${escapeHtml(gtitle(g))}">${hanMarkup(glabel(g))}</span>`).join("");
    card.innerHTML = `
      <div class="zh" lang="zh-Hans">${r.chinese}</div>
      <div class="py">${r.pinyin}</div>
      <div class="en"><span lang="en">${(r.translation&&r.translation.en)||""}</span>　·　${T("繁：","Trad: ")}<span lang="zh-Hant">${r.traditional}</span></div>
      <div class="toks">${toks}</div>${tags}
      <div class="row">
        <button data-a="${AUDIO + r.id}.mp3">${T("▶ 常速","▶ Normal")}</button>
        <button class="ghost" data-a="${AUDIO + r.id}_slow.mp3">${T("▶ 慢速","▶ Slow")}</button>
        <span class="count">${T("原编排", "Authored")} ${levelLabel(String(r.hsk_level))}</span>
        <span class="count">${T("2025 词汇估算", "2025 vocabulary estimate")} ${examLabel(examKey(r))}</span>
        <span class="count">${tlabel(r.topic)} · ${slabel(r.sentence_type)}</span>
        <span class="count">${r.id}</span>
      </div>`;
    frag.appendChild(card);
  }
  shownCount = end;
  if (shownCount < shown.length) {
    const more = document.createElement("button");
    more.id = "more"; more.className = "more";
    more.textContent = T(`显示更多（还有 ${shown.length - shownCount} 句）`, `Show more (${shown.length - shownCount} left)`);
    more.onclick = renderMore;
    frag.appendChild(more);
  }
  list.appendChild(frag);
  const more = document.getElementById("more");
  if (more && typeof IntersectionObserver !== "undefined") {
    if (!moreObserver) moreObserver = new IntersectionObserver(es => {
      if (es.some(e => e.isIntersecting)) renderMore();
    }, {rootMargin: "800px"});
    moreObserver.disconnect();
    moreObserver.observe(more);
  }
}
// 音频按钮用事件委托，不必给每张卡片单独绑定
document.getElementById("list").onclick = e => {
  const b = e.target.closest && e.target.closest(".row button[data-a]");
  if (b) new Audio(b.dataset.a).play();
};

function applyFilter() {
  const q = currentQuery();
  render(ALL.filter(r => matches(r, null, q)));
}

// —— 静态文案与语言切换 ——
document.getElementById("sub").innerHTML = T(
  '两套分级独立查看：2021 标准原编排 + 2025 考试大纲词汇估算 · 合成音频 · <a href="setup.html">开发者接入 →</a>',
  'Compare authored 2021 levels and 2025 exam vocabulary estimates · synthetic audio · <a href="setup.html">Developer setup →</a>');
document.getElementById("q").placeholder = T("搜索汉字 / 拼音 / 英文…","Search hanzi / pinyin / English…");
const lb = document.getElementById("langBtn");
lb.textContent = T("EN","中文");
lb.lang = T("en", "zh-Hans");
lb.onclick = () => { localStorage.setItem("hsa_lang", LANG === "zh" ? "en" : "zh"); location.reload(); };
document.title = T("hsk-sentences-audio · 浏览器","hsk-sentences-audio · Browser");

renderStats();
renderFacets();
// 搜索也参与联动：结果与所有 facet 计数同时刷新
let searchTimer = null;
document.getElementById("q").oninput = () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { applyFilter(); renderFacets(); }, 150);
};
render(ALL);
// 空闲时预先算好搜索文本，第一次搜索就不用等
(window.requestIdleCallback || (f => setTimeout(f, 500)))(() => ALL.forEach(searchHay));
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
  <h1 id="h1t">开发者接入指南
    <button id="langBtn" style="float:right;border:1px solid var(--line);background:#fff;color:#555;
      padding:4px 12px;border-radius:999px;font-size:12.5px;cursor:pointer;"></button></h1>
  <div class="sub" id="subT"></div>

  <h2 id="s1"></h2>
  <div class="sub" id="d1"></div>
  <div class="btns">
    <button class="p" id="bJson" onclick="dl('sentences.json', JSON.stringify(SENTENCES,null,2))"></button>
    <button id="bCsv" onclick="dl('sentences.csv', toCSV())"></button>
    <button id="bAnki" onclick="dl('anki.txt', toAnki())"></button>
  </div>
  <div class="note" id="noteAnki"></div>

  <h2 id="s2"></h2>
  <div class="field">
    <label id="lDb"></label>
    <select id="db" onchange="renderSQL()">
      <option value="sqlite">SQLite</option>
      <option value="postgres">PostgreSQL</option>
      <option value="mysql">MySQL</option>
    </select>
    <button id="bSql" onclick="dl('schema_'+db()+'.sql', sqlText)"></button>
  </div>
  <pre id="sql"><button class="copy" onclick="cp('sql')"></button><code></code></pre>

  <h2 id="s3"></h2>
  <div class="field">
    <label id="lLang"></label>
    <select id="lang" onchange="renderModel()">
      <option value="swift">Swift (Codable)</option>
      <option value="ts">TypeScript</option>
      <option value="kotlin">Kotlin</option>
    </select>
  </div>
  <pre id="model"><button class="copy" onclick="cp('model')"></button><code></code></pre>

  <h2 id="s4"></h2>
  <div class="sub" id="d4"></div>
  <div class="field">
    <label id="lGoal"></label>
    <select id="goal" onchange="renderPrompt()">
      <option value="ios"></option>
      <option value="api"></option>
      <option value="web"></option>
    </select>
  </div>
  <pre id="prompt"><button class="copy" onclick="cp('prompt')"></button><code></code></pre>
</div>

<script src="data.js"></script>
<script>
const SENTENCES = window.SENTENCES || [];
const db = () => document.getElementById("db").value;
let sqlText = "";

// —— i18n：与 index.html 共用 localStorage 键 ——
const LANG = localStorage.getItem("hsa_lang") || "zh";
const T = (zh, en) => LANG === "zh" ? zh : en;
document.documentElement.lang = T("zh-Hans", "en");
function applyI18n() {
  const S = (id, zh, en) => { const e = document.getElementById(id); if (e) e.innerHTML = T(zh, en); };
  document.title = T("hsk-sentences-audio · 开发者接入", "hsk-sentences-audio · Developer setup");
  S("h1t", `开发者接入指南<button id="langBtn" lang="en" style="float:right;border:1px solid var(--line);background:#fff;color:#555;padding:4px 12px;border-radius:999px;font-size:12.5px;cursor:pointer;">EN</button>`,
          `Developer Integration Guide<button id="langBtn" lang="zh-Hans" style="float:right;border:1px solid var(--line);background:#fff;color:#555;padding:4px 12px;border-radius:999px;font-size:12.5px;cursor:pointer;">中文</button>`);
  S("subT", `把这个数据集接进你的应用：<b>${SENTENCES.length}</b> 句 · 每句含拼音/翻译/逐词词义/常速+慢速音频 · <a href="index.html">← 返回浏览器</a>`,
            `Wire this dataset into your app: <b>${SENTENCES.length}</b> sentences · each with pinyin / translation / per-word glosses / normal+slow audio · <a href="index.html">← Back to browser</a>`);
  S("s1", "1 · 拿数据", "1 · Get the data");
  S("d1", '整个数据集是 <code>dist/sentences.json</code> + <code>dist/audio/&lt;id&gt;.mp3</code>。也可在本页一键导出到你熟悉的格式：',
          'The whole dataset is <code>dist/sentences.json</code> + <code>dist/audio/&lt;id&gt;.mp3</code>. Or export right here to a format you like:');
  S("bJson", "下载 sentences.json", "Download sentences.json");
  S("bCsv", "下载 CSV（句级）", "Download CSV (per sentence)");
  S("bAnki", "下载 Anki 导入文件", "Download Anki import file");
  S("noteAnki", 'Anki：新建牌组 → 导入 → 选“Fields separated by: Tab”，字段顺序为 正面(汉字) / 拼音 / 英文 / 音频。音频文件需一并放入 Anki media 目录。',
                'Anki: create a deck → Import → choose "Fields separated by: Tab"; field order is Front (hanzi) / pinyin / English / audio. Copy the audio files into your Anki media folder.');
  S("s2", "2 · 导入数据库", "2 · Import into a database");
  S("lDb", "数据库", "Database");
  S("bSql", "下载 .sql", "Download .sql");
  S("s3", "3 · 数据模型（复制即用）", "3 · Data models (copy & paste)");
  S("lLang", "语言", "Language");
  S("s4", "4 · Ask your LLM（让 AI 帮你搭）", "4 · Ask your LLM");
  S("d4", "选一个目标，生成一段自带数据结构说明的提示词，直接丢给你的 AI：",
          "Pick a goal to generate a prompt with the full schema baked in — paste it into your AI:");
  S("lGoal", "我想做", "I want to build");
  const opts = {ios: ["iOS 闪卡/SRS App（SwiftUI）","iOS flashcard/SRS app (SwiftUI)"],
                api: ["FastAPI 后端 + 检索接口","FastAPI backend + search API"],
                web: ["网页版跟读练习（React）","Web shadowing practice (React)"]};
  for (const k in opts) {
    const o = document.querySelector(`#goal option[value=${k}]`);
    if (o) o.textContent = T(opts[k][0], opts[k][1]);
  }
  document.querySelectorAll("pre .copy").forEach(b => b.textContent = T("复制","Copy"));
  const pc = document.querySelector("#prompt .copy");
  if (pc) pc.textContent = T("复制提示词","Copy prompt");
  const lb = document.getElementById("langBtn");
  if (lb) lb.onclick = () => { localStorage.setItem("hsa_lang", LANG === "zh" ? "en" : "zh"); location.reload(); };
}

function dl(name, text) {
  const b = new Blob([text], {type:"text/plain;charset=utf-8"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = name; a.click();
}
function cp(id){ const t = document.querySelector("#"+id+" code").innerText; navigator.clipboard.writeText(t); }
function esc(s){ return String(s==null?"":s).replace(/'/g,"''"); }
function csvCell(s){ return '"' + String(s==null?"":s).replace(/"/g,'""') + '"'; }

function toCSV(){
  const head = ["id","hsk_level","chinese","traditional","pinyin","pinyin_numbered","english","audio_normal","audio_slow","exam_vocab_level_2025"];
  const rows = [head.join(",")];
  for (const r of SENTENCES) rows.push([r.id,r.hsk_level,r.chinese,r.traditional,r.pinyin,r.pinyin_numbered,(r.translation&&r.translation.en)||"",r.audio.normal,r.audio.slow,r.exam_vocab_level_2025].map(csvCell).join(","));
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
    s += "CREATE TABLE sentences (\n  id TEXT PRIMARY KEY,\n  hsk_level INTEGER,\n  chinese TEXT,\n  traditional TEXT,\n  pinyin TEXT,\n  pinyin_numbered TEXT,\n  english TEXT,\n  audio_normal TEXT,\n  audio_slow TEXT,\n  exam_vocab_level_2025 INTEGER\n);\n";
    s += "CREATE TABLE tokens (\n  sentence_id TEXT,\n  position INTEGER,\n  word TEXT,\n  pinyin TEXT,\n  gloss_en TEXT\n);\n\n";
  } else {
    s += "CREATE TABLE sentences (\n  id VARCHAR(32) PRIMARY KEY,\n  hsk_level INT,\n  chinese VARCHAR(255),\n  traditional VARCHAR(255),\n  pinyin VARCHAR(255),\n  pinyin_numbered VARCHAR(255),\n  english VARCHAR(512),\n  audio_normal VARCHAR(128),\n  audio_slow VARCHAR(128),\n  exam_vocab_level_2025 INT\n) CHARACTER SET utf8mb4;\n";
    s += "CREATE TABLE tokens (\n  sentence_id VARCHAR(32),\n  position INT,\n  word VARCHAR(64),\n  pinyin VARCHAR(64),\n  gloss_en VARCHAR(512)\n) CHARACTER SET utf8mb4;\n\n";
  }
  for (const r of SENTENCES) {
    s += `INSERT INTO sentences VALUES ('${esc(r.id)}',${r.hsk_level},'${esc(r.chinese)}','${esc(r.traditional)}','${esc(r.pinyin)}','${esc(r.pinyin_numbered)}','${esc((r.translation&&r.translation.en)||"")}','${esc(r.audio.normal)}','${esc(r.audio.slow)}',${r.exam_vocab_level_2025 == null ? 'NULL' : Number(r.exam_vocab_level_2025)});\n`;
    r.tokens.forEach((t,i) => { s += `INSERT INTO tokens VALUES ('${esc(r.id)}',${i},'${esc(t.word)}','${esc(t.pinyin)}','${esc(t.gloss_en)}');\n`; });
  }
  sqlText = s;
  document.querySelector("#sql code").textContent = s.length > 4000 ? s.slice(0,4000) + T("\n... （完整内容见下载）","\n... (full content in the download)") : s;
}

function renderModel(){
  const lang = document.getElementById("lang").value;
  let c = "";
  if (lang==="swift") {
    c = `struct Sentence: Codable, Identifiable {
    let id: String
    let hskLevel: Int
    let examVocabLevel2025: Int?
    let chinese: String
    let traditional: String
    let pinyin: String
    let translation: Translation
    let tokens: [Token]
    let audio: Audio

    enum CodingKeys: String, CodingKey {
        case id, chinese, traditional, pinyin, translation, tokens, audio
        case hskLevel = "hsk_level"
        case examVocabLevel2025 = "exam_vocab_level_2025"
    }
}
struct Translation: Codable { let en: String }
struct Token: Codable { let word, pinyin, glossEn: String
    enum CodingKeys: String, CodingKey { case word, pinyin; case glossEn = "gloss_en" } }
struct Audio: Codable { let normal, slow: String }

// ${T("加载：", "Load the dataset:")}
let url = Bundle.main.url(forResource: "sentences", withExtension: "json")!
let data = try Data(contentsOf: url)
let sentences = try JSONDecoder().decode([Sentence].self, from: data)`;
  } else if (lang==="ts") {
    c = `export interface Token { word: string; pinyin: string; gloss_en: string; }
export interface Sentence {
  id: string;
  hsk_level: number;
  exam_vocab_level_2025?: number | null; // vocabulary estimate; 7 = 7-9 band
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
    @SerialName("exam_vocab_level_2025") val examVocabLevel2025: Int? = null,
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
  const schemaZh = `每条记录：{ id, hsk_level, exam_vocab_level_2025(词汇估算，7=7–9合并档，可为空), chinese(简体), traditional(繁体), pinyin(带声调,已处理轻声/儿化/多音字), pinyin_numbered, translation:{en}, tokens:[{word,pinyin,gloss_en}], grammar_tags:[], audio:{normal,slow} }。音频文件在 audio/<id>.mp3 与 audio/<id>_slow.mp3。`;
  const schemaEn = `Each record: { id, hsk_level, exam_vocab_level_2025 (vocabulary estimate; 7=7–9 band; nullable), chinese (simplified), traditional, pinyin (tone marks; neutral tones/erhua/polyphones handled), pinyin_numbered, translation:{en}, tokens:[{word,pinyin,gloss_en}], grammar_tags:[], audio:{normal,slow} }. Audio files live at audio/<id>.mp3 and audio/<id>_slow.mp3.`;
  const map = {
    ios: T(`我有一个中文学习数据集（sentences.json + audio/ 目录）。${schemaZh}\n请用 SwiftUI 写一个离线闪卡/SRS 应用：卡片正面显示汉字，点击播放常速音频、长按播放慢速；背面显示拼音、英文和逐词词义；实现一个简单的 SM-2 间隔重复算法按 hsk_level 由易到难排程。给出完整可编译的 Swift 代码和 JSON 解码模型。`,
           `I have a Chinese-learning dataset (sentences.json + an audio/ folder). ${schemaEn}\nBuild an offline flashcard/SRS app in SwiftUI: card front shows the hanzi, tap plays normal-speed audio, long-press plays slow; the back shows pinyin, English, and per-word glosses. Implement a simple SM-2 spaced-repetition scheduler ordered easy-to-hard by hsk_level. Give me complete, compilable Swift code including the JSON decoding models.`),
    api: T(`我有一个中文学习数据集 sentences.json。${schemaZh}\n请用 FastAPI 写一个后端：启动时加载 JSON，提供 GET /sentences?level=&q=（按 HSK 等级过滤 + 汉字/拼音/英文模糊搜索，支持分页 page/limit）、GET /sentences/{id}、GET /audio/{id} 返回 mp3。给出完整 main.py 和 Pydantic 模型。`,
           `I have a Chinese-learning dataset sentences.json. ${schemaEn}\nBuild a FastAPI backend: load the JSON at startup and expose GET /sentences?level=&q= (filter by HSK level + fuzzy search over hanzi/pinyin/English, with page/limit pagination), GET /sentences/{id}, and GET /audio/{id} returning the mp3. Give me a complete main.py with Pydantic models.`),
    web: T(`我有一个中文学习数据集 sentences.json + audio/。${schemaZh}\n请用 React 写一个网页跟读练习：列出句子，点击播放常速/慢速音频，显示拼音和逐词词义，可按 HSK 等级筛选和搜索。给出完整组件代码。`,
           `I have a Chinese-learning dataset sentences.json + audio/. ${schemaEn}\nBuild a React shadowing-practice page: list sentences, click to play normal/slow audio, show pinyin and per-word glosses, filter by HSK level and search. Give me complete component code.`),
  };
  document.querySelector("#prompt code").textContent = map[goal];
}

applyI18n(); renderSQL(); renderModel(); renderPrompt();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
