import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = path.resolve(packageDir, "..", "..", "dist", "sentences.json");
const destination = path.join(packageDir, "data", "sentences.json");
const records = JSON.parse(fs.readFileSync(source, "utf8"));
if (!Array.isArray(records) || records.length !== 4354) {
  throw new Error(`Expected 4,354 canonical records in ${source}; found ${records?.length ?? "invalid JSON"}`);
}
fs.mkdirSync(path.dirname(destination), { recursive: true });
fs.copyFileSync(source, destination);
console.log(`prepared ${records.length.toLocaleString()} records → ${destination}`);
