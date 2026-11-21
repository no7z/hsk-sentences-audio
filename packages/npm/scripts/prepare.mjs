import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = path.resolve(packageDir, "..", "..", "dist", "sentences.json");
const destination = path.join(packageDir, "data", "sentences.json");
const records = JSON.parse(fs.readFileSync(source, "utf8"));
if (!Array.isArray(records) || records.filter(r => r.hsk_level <= 6).length !== 4354 ||
    new Set(records.map(r => r.id)).size !== records.length) {
  throw new Error(`Expected 4,354 preserved level 1–6 records and unique IDs in ${source}`);
}
fs.mkdirSync(path.dirname(destination), { recursive: true });
fs.copyFileSync(source, destination);
fs.copyFileSync(path.join(path.dirname(source), "exam_vocab_metadata.json"), path.join(path.dirname(destination), "exam_vocab_metadata.json"));
console.log(`prepared ${records.length.toLocaleString()} records → ${destination}`);
