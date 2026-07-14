import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const exampleDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = path.resolve(exampleDir, "..", "..", "dist", "sentences.json");
const destination = path.join(exampleDir, "public", "sentences.json");
fs.mkdirSync(path.dirname(destination), { recursive: true });
fs.copyFileSync(source, destination);
console.log(`copied browser dataset → ${destination}`);
