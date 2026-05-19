import { useEffect, useMemo, useState } from "react";
import { Streamlit } from "streamlit-component-lib";
import type { Article } from "../types";

interface Props {
  articles?: Article[];
  /** Hide search toolbar when nested inside RAG results */
  embedded?: boolean;
  bedrockConfigured?: boolean;
  summarizeFailed?: boolean;
}

function sentimentKind(sentiment: string, summary: string): string {
  if (!summary || summary.includes("Pending")) return "pending";
  const s = sentiment.toLowerCase();
  if (s === "positive" || s === "negative" || s === "neutral") return s;
  return "neutral";
}

function ArticleCard({
  article,
  bedrockConfigured = false,
  summarizeFailed = false,
}: {
  article: Article;
  bedrockConfigured?: boolean;
  summarizeFailed?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const pending =
    !article.summary || article.summary === "_Pending summary…_";
  const kind = sentimentKind(article.sentiment, article.summary);

  return (
    <article className={`mi-article ${open ? "open" : ""}`}>
      <button
        type="button"
        className="mi-article-head"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <div className="mi-article-title-row">
          {article.rank != null && (
            <span className="mi-rank">#{article.rank}</span>
          )}
          <h3>{article.title}</h3>
          <span className="mi-chevron">{open ? "−" : "+"}</span>
        </div>
        <div className="mi-article-meta">
          <span className={`mi-badge ${kind}`}>{article.sentiment}</span>
          <span className="mi-badge neutral">{article.ticker}</span>
          <span className="mi-meta-text">
            {article.source} · {article.publishedAt || "—"}
          </span>
        </div>
      </button>
      {open && (
        <div className="mi-article-body">
          {article.url && (
            <a href={article.url} target="_blank" rel="noreferrer" className="mi-link">
              Read source →
            </a>
          )}
          <p className="mi-label">AI Summary</p>
          {pending ? (
            <p className="mi-pending">
              {summarizeFailed ? (
                <>
                  Still pending — Bedrock did not save summaries. Use{" "}
                  <strong>Test Bedrock connection</strong> in the sidebar (Secrets,
                  IAM, model access).
                </>
              ) : bedrockConfigured ? (
                <>
                  Not summarized yet — click <strong>Summarize ALL pending</strong>{" "}
                  in the sidebar.
                </>
              ) : (
                <>
                  Pending — configure Bedrock in Secrets, then{" "}
                  <strong>Summarize ALL pending</strong>.
                </>
              )}
            </p>
          ) : (
            <div className="mi-summary">{article.summary}</div>
          )}
          {article.whyMatters && (
            <p className="mi-why">
              <strong>Why it matters:</strong> {article.whyMatters}
            </p>
          )}
          {article.topics?.length > 0 && (
            <div className="mi-chips">
              {article.topics.map((t) => (
                <span key={t} className="mi-chip">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

const SCROLL_AREA_PX = 480;
const FRAME_HEIGHT_PX = 560;

export function ArticleFeed({
  articles = [],
  embedded = false,
  bedrockConfigured = false,
  summarizeFailed = false,
}: Props) {
  const [query, setQuery] = useState("");
  const [sentimentFilter, setSentimentFilter] = useState("all");

  const sentiments = useMemo(() => {
    const set = new Set(articles.map((a) => a.sentiment?.toLowerCase() || "n/a"));
    return ["all", ...Array.from(set)];
  }, [articles]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return articles.filter((a) => {
      if (sentimentFilter !== "all" && a.sentiment?.toLowerCase() !== sentimentFilter) {
        return false;
      }
      if (!q) return true;
      const hay = `${a.title} ${a.summary} ${a.ticker} ${a.source}`.toLowerCase();
      return hay.includes(q);
    });
  }, [articles, query, sentimentFilter]);

  useEffect(() => {
    Streamlit.setFrameHeight(
      embedded ? Math.min(520, 120 + filtered.length * 72) : FRAME_HEIGHT_PX
    );
  }, [filtered.length, query, embedded]);

  return (
    <div className="mi-root mi-feed">
      {!embedded && (
        <div className="mi-feed-toolbar">
          <input
            className="mi-input"
            placeholder="Filter cards instantly…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="mi-filter-chips">
            {sentiments.map((s) => (
              <button
                key={s}
                type="button"
                className={`mi-chip-btn ${sentimentFilter === s ? "active" : ""}`}
                onClick={() => setSentimentFilter(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
      <p className="mi-feed-count">
        Showing {filtered.length} of {articles.length} articles
      </p>
      <div
        className="mi-feed-scroll"
        style={{ maxHeight: embedded ? 400 : SCROLL_AREA_PX }}
      >
        {filtered.length === 0 ? (
          <p className="mi-empty">No articles match your filters.</p>
        ) : (
          filtered.map((a, i) => (
            <ArticleCard
              key={a.id ?? `${a.title}-${i}`}
              article={a}
              bedrockConfigured={bedrockConfigured}
              summarizeFailed={summarizeFailed}
            />
          ))
        )}
      </div>
      <style>{`
        .mi-feed-scroll {
          overflow-y: auto;
          overflow-x: hidden;
          -webkit-overflow-scrolling: touch;
          padding-right: 6px;
        }
        .mi-feed-scroll::-webkit-scrollbar {
          width: 8px;
        }
        .mi-feed-scroll::-webkit-scrollbar-thumb {
          background: rgba(79, 140, 255, 0.35);
          border-radius: 4px;
        }
        .mi-feed-toolbar { margin-bottom: 0.75rem; }
        .mi-filter-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
          margin-top: 0.5rem;
        }
        .mi-chip-btn {
          background: rgba(79,140,255,0.1);
          border: 1px solid var(--border);
          color: var(--muted);
          border-radius: 999px;
          padding: 0.25rem 0.65rem;
          font-size: 0.75rem;
          cursor: pointer;
          text-transform: capitalize;
        }
        .mi-chip-btn.active {
          background: rgba(79,140,255,0.25);
          color: var(--text);
          border-color: var(--accent);
        }
        .mi-feed-count { font-size: 0.8rem; color: var(--muted); margin: 0 0 0.75rem; }
        .mi-article {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 14px;
          margin-bottom: 0.65rem;
          overflow: hidden;
          transition: border-color 0.2s;
        }
        .mi-article.open { border-color: rgba(79,140,255,0.35); }
        .mi-article-head {
          width: 100%;
          text-align: left;
          background: none;
          border: none;
          padding: 1rem 1.1rem;
          cursor: pointer;
          color: inherit;
        }
        .mi-article-title-row {
          display: flex;
          align-items: flex-start;
          gap: 0.5rem;
        }
        .mi-article-title-row h3 {
          margin: 0;
          flex: 1;
          font-size: 0.98rem;
          line-height: 1.35;
          color: #f1f5f9;
        }
        .mi-rank {
          color: var(--accent);
          font-weight: 700;
          font-size: 0.85rem;
        }
        .mi-chevron {
          color: var(--accent);
          font-size: 1.2rem;
          line-height: 1;
        }
        .mi-article-meta { margin-top: 0.5rem; }
        .mi-meta-text { color: var(--muted); font-size: 0.78rem; }
        .mi-article-body {
          padding: 0 1.1rem 1rem;
          border-top: 1px solid rgba(79,140,255,0.1);
        }
        .mi-link { color: var(--accent); font-size: 0.85rem; }
        .mi-label {
          font-size: 0.68rem;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--muted);
          margin: 0.75rem 0 0.35rem;
        }
        .mi-summary {
          white-space: pre-wrap;
          font-size: 0.9rem;
          line-height: 1.55;
          color: #e2e8f0;
        }
        .mi-pending { color: var(--pending); font-size: 0.88rem; }
        .mi-why { font-size: 0.85rem; color: var(--muted); margin-top: 0.65rem; }
        .mi-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.5rem; }
        .mi-chip {
          background: rgba(79,140,255,0.12);
          color: #93c5fd;
          padding: 0.15rem 0.5rem;
          border-radius: 6px;
          font-size: 0.75rem;
        }
      `}</style>
    </div>
  );
}
