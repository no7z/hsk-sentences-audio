import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const records = JSON.parse(fs.readFileSync(new URL("../dist/sentences.json", import.meta.url), "utf8"));
const html = fs.readFileSync(new URL("../dist/index.html", import.meta.url), "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1]
  .split("// —— 静态文案与语言切换 ——")[0];
const payload = { window: {} };
vm.runInNewContext(fs.readFileSync(new URL("../dist/data.js", import.meta.url), "utf8"), payload);
function setup(language = "en") {
  const query = { value: "" };
  const context = vm.createContext({ window: payload.window,
    localStorage: { getItem: () => language }, document: { documentElement: {}, getElementById: () => query } });
  vm.runInContext(script, context);
  return context;
}

test("browser offers both independent classifications and the combined high band", () => {
  const context = setup();
  assert.equal(vm.runInContext("ALL.filter(r=>matches(r,null)).length", context), records.length);
  assert.equal(vm.runInContext("state.exam='7'; ALL.filter(r=>matches(r,null)).length", context),
    records.filter(r => r.exam_vocab_level_2025 === 7).length);
  assert.equal(vm.runInContext("examLabel('7')", context), "HSK 7–9");
  assert.equal(vm.runInContext("examLabel(examKey({hsk_level:1}))", context), "Not estimated");
  const high = setup();
  assert.equal(vm.runInContext("state.lvl='7'; ALL.filter(r=>matches(r,null)).length", high), records.filter(r=>r.hsk_level===7).length);
  assert.equal(vm.runInContext("levelLabel('7')", high), "HSK 7–9");
});

test("every grammar point in the dataset has an English UI label without changing IDs", () => {
  const grammar = payload.window.GRAMMAR;
  const categories = payload.window.GRAMMAR_CATEGORIES_EN;
  const used = new Set(records.flatMap(r => r.grammar_tags));
  const source = JSON.parse(fs.readFileSync(new URL("../data/grammar_points.json", import.meta.url), "utf8"));
  const translations = JSON.parse(fs.readFileSync(new URL("../data/grammar_i18n_en.json", import.meta.url), "utf8"));
  for (const id of used) {
    assert.ok(grammar[id].label_en && grammar[id].full_en, id);
    assert.ok(categories[grammar[id].cat], id);
    assert.match(grammar[id].label_en, /[A-Za-z]/);
  }
  for (const entry of source) {
    assert.equal(grammar[entry.id].label, entry.label);
    assert.equal(grammar[entry.id].full, entry.label_full);
    assert.equal(grammar[entry.id].cat, entry.cat);
    assert.equal(grammar[entry.id].label_en, translations.points[entry.id]?.label ?? null);
    assert.equal(grammar[entry.id].full_en, translations.points[entry.id]?.full ?? null);
  }
  for (const [category, english] of Object.entries(translations.categories)) assert.equal(categories[category], english);
});

test("English and Chinese grammar searches, IDs and empty states work in either locale", () => {
  for (const language of ["en", "zh"]) {
    const context = setup(language);
    assert.equal(vm.runInContext("grammarMatches('1-09','ADVERB')", context), true);
    assert.equal(vm.runInContext("grammarMatches('1-09','副词')", context), true);
    assert.equal(vm.runInContext("grammarMatches('1-09','1-09')", context), true);
    assert.equal(vm.runInContext("grammarMatches('1-09','not-a-grammar-point')", context), false);
    assert.equal(vm.runInContext("document.documentElement.lang", context), language === "en" ? "en" : "zh-Hans");
  }
  const context = setup();
  const result = vm.runInContext("gramQuery='adverb'; grammarFacet(counts(r=>r.grammar_tags||[],'gram'))", context);
  assert.match(result, /Degree adverbs/);
  assert.match(result, /Parts of speech/);
  assert.match(result, /lang="zh-Hans"/);
  const empty = vm.runInContext("gramQuery='not-a-grammar-point'; grammarFacet(counts(r=>r.grammar_tags||[],'gram'))", context);
  assert.match(empty, /No matching grammar points/);
  const escaped = vm.runInContext("gramQuery='\"<test>'; grammarFacet(counts(r=>r.grammar_tags||[],'gram'))", context);
  assert.match(escaped, /&quot;&lt;test&gt;/);
  assert.match(vm.runInContext("gtitle('1-09')", context), /Degree adverbs[\s\S]*Chinese source: 程度副词/);
  assert.match(vm.runInContext("glabel('1-45')", context), /Questions with 吗/);
});

test("original-level and vocabulary-level filters intersect without relabelling records", () => {
  const context = setup();
  const expected = records.filter(r => r.hsk_level === 1 && r.exam_vocab_level_2025 === 3);
  assert.ok(expected.length > 0);
  const actual = vm.runInContext("state.lvl='1'; state.exam='3'; ALL.filter(r=>matches(r,null)).map(r=>r.id)", context);
  assert.deepEqual(Array.from(actual), expected.map(r => r.id));
  const ownFacet = vm.runInContext("counts(examKey,'exam').m", context);
  assert.equal(Object.values(ownFacet).reduce((a,b)=>a+b,0), 281);
  const originalFacet = vm.runInContext("counts(r=>String(r.hsk_level),'lvl').m", context);
  assert.equal(Object.values(originalFacet).reduce((a,b)=>a+b,0), records.filter(r => r.exam_vocab_level_2025 === 3).length);
  assert.equal(vm.runInContext("state.exam=null; ALL.filter(r=>matches(r,null)).length", context), 281);
});
