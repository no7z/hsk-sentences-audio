import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { execFileSync } from "node:child_process";

const records = JSON.parse(fs.readFileSync(new URL("../dist/sentences.json", import.meta.url), "utf8"));
const html = fs.readFileSync(new URL("../dist/setup.html", import.meta.url), "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1]
  .replace("applyI18n(); renderSQL(); renderModel(); renderPrompt();", "");

function setup(db = "sqlite", data = records) {
  const display = { textContent: "" };
  const context = vm.createContext({
    window: { SENTENCES: data }, localStorage: { getItem: () => "en" },
    document: { getElementById: () => ({ value: db }), querySelector: () => display },
  });
  vm.runInContext(script, context);
  return context;
}

test("CSV exports every original row with the additional vocabulary estimate", () => {
  const csv = vm.runInContext("toCSV()", setup());
  execFileSync("python3", ["-c", `
import csv,io,json,sys
data=json.load(sys.stdin)
rows=list(csv.DictReader(io.StringIO(data['csv'])))
assert len(rows)==len(data['records'])
for row,record in zip(rows,data['records']):
    assert row['id']==record['id'] and row['chinese']==record['chinese']
    assert int(row['hsk_level'])==record['hsk_level']
    assert int(row['exam_vocab_level_2025'])==record['exam_vocab_level_2025']
`], { input: JSON.stringify({ csv, records }) });
});

test("generated SQL imports into a real SQLite database without changing original grades", () => {
  for (const dialect of ["sqlite", "postgres"]) {
    const context = setup(dialect);
    const sql = vm.runInContext("renderSQL(); sqlText", context);
    execFileSync("python3", ["-c", `
import json,sqlite3,sys
data=json.load(sys.stdin)
db=sqlite3.connect(':memory:');db.executescript(data['sql'])
actual=db.execute('select id,hsk_level,exam_vocab_level_2025 from sentences order by id').fetchall()
expected=sorted((r['id'],r['hsk_level'],r['exam_vocab_level_2025']) for r in data['records'])
assert actual==expected
`], { input: JSON.stringify({ sql, records }) });
  }
});

test("older records produce SQL NULL instead of zero or undefined", () => {
  const legacy = { ...records[0] };
  delete legacy.exam_vocab_level_2025;
  const context = setup("sqlite", [legacy]);
  const sql = vm.runInContext("renderSQL(); sqlText", context);
  const result = execFileSync("python3", ["-c", `
import json,sqlite3,sys
db=sqlite3.connect(':memory:');db.executescript(sys.stdin.read())
print(json.dumps(db.execute('select exam_vocab_level_2025 from sentences').fetchall()))
`], { input: sql, encoding: "utf8" });
  assert.deepEqual(JSON.parse(result), [[null]]);
});
