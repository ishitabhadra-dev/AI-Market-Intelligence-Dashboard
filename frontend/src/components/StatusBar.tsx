import { useEffect } from "react";
import { Streamlit } from "streamlit-component-lib";

interface Props {
  bedrock?: boolean;
  pending?: number;
  vectorCount?: number;
  articleCount?: number;
}

export function StatusBar({
  bedrock = false,
  pending = 0,
  vectorCount = 0,
  articleCount = 0,
}: Props) {
  useEffect(() => {
    Streamlit.setFrameHeight(56);
  }, [bedrock, pending, vectorCount, articleCount]);

  const pills = [
    {
      label: bedrock ? "Bedrock connected" : "Bedrock not configured",
      kind: bedrock ? "positive" : "negative",
    },
    { label: `${articleCount} articles`, kind: "neutral" },
    {
      label: pending ? `${pending} pending AI` : "All summarized",
      kind: pending ? "pending" : "positive",
    },
    { label: `${vectorCount} in vector DB`, kind: "neutral" },
  ];

  return (
    <div className="mi-root mi-status-row">
      {pills.map((p) => (
        <span key={p.label} className={`mi-badge ${p.kind}`}>
          {p.label}
        </span>
      ))}
    </div>
  );
}
