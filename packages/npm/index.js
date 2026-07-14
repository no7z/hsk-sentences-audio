export const DATASET_VERSION = "1.0.0";
export const DATASET_LICENSE = "CC-BY-SA-4.0";
export const DEFAULT_AUDIO_BASE_URL =
  "https://raw.githubusercontent.com/no7z/hsk-sentences-audio/main/dist/";

// Keep the path non-literal so browser bundlers do not duplicate the 6.1 MB
// packaged JSON when callers explicitly provide their own hosted URL.
const packagedDataUrl = () => new URL("./data/" + "sentences.json", import.meta.url);

function dataUrl(value) {
  if (value instanceof URL) return value;
  if (typeof value === "string" && value) {
    if (typeof window !== "undefined") return new URL(value, window.location.href);
    return new URL(value);
  }
  return packagedDataUrl();
}

/** Load all sentence records. Node reads the packaged JSON; browsers may pass a hosted URL. */
export async function loadSentences(options = {}) {
  const url = dataUrl(options.url);
  if (url.protocol === "file:" && typeof process !== "undefined" && process.versions?.node) {
    const fsModule = "node:fs/promises";
    const { readFile } = await import(/* @vite-ignore */ fsModule);
    return JSON.parse(await readFile(url, "utf8"));
  }
  const response = await fetch(url, { signal: options.signal });
  if (!response.ok) throw new Error(`Unable to load HSK sentences (${response.status} ${response.statusText})`);
  return response.json();
}

/** Resolve a record's normal or slow audio path against a configurable asset base. */
export function audioUrl(sentence, options = {}) {
  const speed = options.speed ?? "normal";
  if (speed !== "normal" && speed !== "slow") throw new Error(`Unknown audio speed: ${speed}`);
  const relative = sentence?.audio?.[speed];
  if (!relative) throw new Error(`Sentence ${sentence?.id ?? "(unknown)"} has no ${speed} audio path`);
  const base = options.baseUrl ?? DEFAULT_AUDIO_BASE_URL;
  const baseUrl = base instanceof URL
    ? base
    : typeof window !== "undefined"
      ? new URL(base, window.location.href)
      : new URL(base);
  return new URL(relative, baseUrl.href.endsWith("/") ? baseUrl : `${baseUrl.href}/`).href;
}

/** Filter in memory without mutating the canonical records. */
export function filterSentences(sentences, filters = {}) {
  const query = (filters.search ?? "").trim().toLowerCase();
  const filtered = sentences.filter((sentence) => {
    if (filters.level != null && sentence.hsk_level !== Number(filters.level)) return false;
    if (filters.topic && sentence.topic !== filters.topic) return false;
    if (filters.sentenceType && sentence.sentence_type !== filters.sentenceType) return false;
    if (query) {
      const haystack = `${sentence.chinese} ${sentence.traditional} ${sentence.pinyin} ${sentence.translation?.en ?? ""}`.toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    return true;
  });
  return filters.limit == null ? filtered : filtered.slice(0, Math.max(0, Number(filters.limit)));
}
