export type AudioSpeed = "normal" | "slow";

export interface SentenceToken {
  word: string;
  pinyin: string;
  gloss_en: string;
}

export interface SentenceRecord {
  id: string;
  hsk_level: number;
  topic: string;
  sentence_type: "statement" | "question" | "imperative";
  chinese: string;
  traditional: string;
  pinyin: string;
  pinyin_numbered: string;
  translation: { en: string };
  tokens: SentenceToken[];
  grammar_points: string[];
  grammar_tags: string[];
  audio: Record<AudioSpeed, string>;
  audio_meta: {
    engine: string;
    voice: string;
    license: string;
    sample_rate: number;
  };
}

export interface LoadOptions {
  url?: string | URL;
  signal?: AbortSignal;
}

export interface FilterOptions {
  level?: number;
  topic?: string;
  sentenceType?: SentenceRecord["sentence_type"];
  search?: string;
  limit?: number;
}

export const DATASET_VERSION: string;
export const DATASET_LICENSE: "CC-BY-SA-4.0";
export const DEFAULT_AUDIO_BASE_URL: string;
export function loadSentences(options?: LoadOptions): Promise<SentenceRecord[]>;
export function audioUrl(sentence: SentenceRecord, options?: { speed?: AudioSpeed; baseUrl?: string | URL }): string;
export function filterSentences(sentences: SentenceRecord[], filters?: FilterOptions): SentenceRecord[];
