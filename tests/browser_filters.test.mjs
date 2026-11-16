import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const records = JSON.parse(fs.readFileSync(new URL("../dist/sentences.json", import.meta.url), "utf8"));
const html = fs.readFileSync(new URL("../dist/index.html", import.meta.url), "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1]
  .split("// —— 静态文案与语言切换 ——")[0];
function setup() {
  const query = { value: "" };
  const context = vm.createContext({ window: { SENTENCES: records },
    localStorage: { getItem: () => "en" }, document: { getElementById: () => query } });
  vm.runInContext(script, context);
  return context;
}

test("browser offers both independent classifications and the combined high band", () => {
  const context = setup();
  assert.equal(vm.runInContext("ALL.filter(r=>matches(r,null)).length", context), 4354);
  assert.equal(vm.runInContext("state.exam='7'; ALL.filter(r=>matches(r,null)).length", context), 422);
  assert.equal(vm.runInContext("examLabel('7')", context), "HSK 7–9");
  assert.equal(vm.runInContext("examLabel(examKey({hsk_level:1}))", context), "Not estimated");
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
  assert.equal(Object.values(originalFacet).reduce((a,b)=>a+b,0), 399);
  assert.equal(vm.runInContext("state.exam=null; ALL.filter(r=>matches(r,null)).length", context), 281);
});
