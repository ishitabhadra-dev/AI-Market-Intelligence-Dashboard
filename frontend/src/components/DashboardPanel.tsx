import { useEffect } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Streamlit } from "streamlit-component-lib";
import type { TopicItem } from "../types";

interface Props {
  sentiment?: Record<string, number>;
  topics?: TopicItem[];
}

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "#10b981",
  negative: "#ef4444",
  neutral: "#94a3b8",
  "n/a": "#64748b",
};

export function DashboardPanel({ sentiment = {}, topics = [] }: Props) {
  const chartData = Object.entries(sentiment).map(([name, value]) => ({
    name,
    value,
    fill: SENTIMENT_COLORS[name.toLowerCase()] ?? "#4f8cff",
  }));

  useEffect(() => {
    Streamlit.setFrameHeight(340);
  }, [sentiment, topics]);

  return (
    <div className="mi-root mi-dashboard">
      <div className="mi-dash-col chart">
        <h4 className="mi-section-title">Sentiment overview</h4>
        {chartData.length === 0 ? (
          <p className="mi-empty">Summarize articles to see sentiment data.</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(79,140,255,0.12)" />
              <XAxis dataKey="name" tick={{ fill: "#8b9cb8", fontSize: 12 }} />
              <YAxis tick={{ fill: "#8b9cb8", fontSize: 12 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: "#121a2b",
                  border: "1px solid rgba(79,140,255,0.25)",
                  borderRadius: 8,
                }}
              />
              <Bar dataKey="value" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      <div className="mi-dash-col topics">
        <h4 className="mi-section-title">Trending topics</h4>
        {topics.length === 0 ? (
          <p className="mi-empty">Run AI summaries to populate topics.</p>
        ) : (
          <ul className="mi-topic-list">
            {topics.map((t) => (
              <li key={t.topic}>
                <span className="mi-topic-name">{t.topic}</span>
                <span className="mi-topic-count">{t.count}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <style>{`
        .mi-dashboard {
          display: grid;
          grid-template-columns: 1.4fr 1fr;
          gap: 1rem;
        }
        @media (max-width: 768px) {
          .mi-dashboard { grid-template-columns: 1fr; }
        }
        .mi-dash-col {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 1rem 1.1rem;
        }
        .mi-section-title {
          margin: 0 0 0.75rem 0;
          font-size: 0.95rem;
          color: #f1f5f9;
        }
        .mi-empty { color: var(--muted); font-size: 0.88rem; margin: 0; }
        .mi-topic-list {
          list-style: none;
          margin: 0;
          padding: 0;
        }
        .mi-topic-list li {
          display: flex;
          justify-content: space-between;
          padding: 0.45rem 0;
          border-bottom: 1px solid rgba(79,140,255,0.08);
          font-size: 0.88rem;
        }
        .mi-topic-name { color: var(--text); font-weight: 500; }
        .mi-topic-count {
          color: var(--accent);
          font-weight: 600;
          background: rgba(79,140,255,0.12);
          padding: 0.1rem 0.5rem;
          border-radius: 6px;
        }
      `}</style>
    </div>
  );
}
