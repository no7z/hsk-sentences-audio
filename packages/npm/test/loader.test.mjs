import test from "node:test";
import assert from "node:assert/strict";
import { audioUrl, filterSentences, loadSentences } from "../index.js";

test("loads the canonical packaged dataset", async () => {
  const records = await loadSentences();
  assert.equal(records.length, 4354);
  assert.equal(records[0].id, "hsk1-0001");
});

test("filters records and resolves configurable audio URLs", async () => {
  const records = await loadSentences();
  const result = filterSentences(records, { level: 1, search: "老师", limit: 2 });
  assert.ok(result.length > 0 && result.length <= 2);
  assert.match(audioUrl(result[0], { speed: "slow", baseUrl: "https://cdn.example/data/" }), /^https:\/\/cdn\.example\/data\/audio\/.+_slow\.mp3$/);
});
