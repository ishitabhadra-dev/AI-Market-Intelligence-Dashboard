import { useEffect } from "react";
import { Streamlit } from "streamlit-component-lib";
import type { MetricItem } from "../types";

interface Props {
  metrics?: MetricItem[];
}

export function MetricsGrid({ metrics = [] }: Props) {
  useEffect(() => {
    Streamlit.setFrameHeight(Math.max(100, 90 * Math.ceil(metrics.length / 3)));
  }, [metrics]);

  return (
    <div className="mi-root mi-metrics-grid">
      {metrics.map((m) => (
        <div key={m.label} className="mi-metric-card">
          <div className="mi-metric-value">{m.value}</div>
          <div className="mi-metric-label">{m.label}</div>
        </div>
      ))}
      <style>{`
        .mi-metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 0.75rem;
        }
        .mi-metric-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 0.85rem 1rem;
        }
        .mi-metric-value {
          font-size: 1.6rem;
          font-weight: 700;
          color: var(--text);
        }
        .mi-metric-label {
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--muted);
          margin-top: 0.25rem;
        }
      `}</style>
    </div>
  );
}
