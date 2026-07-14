import { useEffect, useMemo, useState } from "react";
import {
  audioUrl,
  filterSentences,
  loadSentences,
  type AudioSpeed,
  type SentenceRecord,
} from "hsk-sentences-audio";

export default function App() {
  const [sentences, setSentences] = useState<SentenceRecord[]>([]);
  const [level, setLevel] = useState(1);
  const [search, setSearch] = useState("");
  const [speed, setSpeed] = useState<AudioSpeed>("normal");
  const [error, setError] = useState("");

  useEffect(() => {
    loadSentences({ url: "/sentences.json" }).then(setSentences).catch((reason) => setError(String(reason)));
  }, []);

  const visible = useMemo(
    () => filterSentences(sentences, { level, search, limit: 24 }),
    [level, search, sentences],
  );

  return (
    <main>
      <header>
        <p className="eyebrow">hsk-sentences-audio · React</p>
        <h1>Listen by level</h1>
        <p>Structured HSK 3.0 sentences, loaded with the npm package.</p>
      </header>

      <section className="controls" aria-label="Sentence filters">
        <label>
          HSK level
          <select value={level} onChange={(event) => setLevel(Number(event.target.value))}>
            {[1, 2, 3, 4, 5, 6].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>
          Search
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="中文, pinyin, or English" />
        </label>
        <fieldset>
          <legend>Audio</legend>
          {(["normal", "slow"] as const).map((value) => (
            <label key={value}><input type="radio" checked={speed === value} onChange={() => setSpeed(value)} /> {value}</label>
          ))}
        </fieldset>
      </section>

      {error && <p role="alert">{error}</p>}
      {!error && sentences.length === 0 && <p>Loading 4,354 records…</p>}
      <section className="grid" aria-live="polite">
        {visible.map((sentence) => (
          <article key={sentence.id}>
            <span className="meta">HSK {sentence.hsk_level} · {sentence.topic}</span>
            <h2>{sentence.chinese}</h2>
            <p className="pinyin">{sentence.pinyin}</p>
            <p>{sentence.translation.en}</p>
            <audio key={`${sentence.id}-${speed}`} controls preload="none" src={audioUrl(sentence, { speed })} />
          </article>
        ))}
      </section>
    </main>
  );
}
