import { useEffect } from "react";
import { Streamlit } from "streamlit-component-lib";

interface Props {
  bedrock?: boolean;
  bedrockLabel?: string;
  bedrockKind?: string;
  pending?: number;
  vectorCount?: number;
  articleCount?: number;
}

export function StatusBar({
  bedrock = false,
  bedrockLabel,
  bedrockKind,
  pending = 0,
  vectorCount = 0,
  articleCount = 0,
}: Props) {
  useEffect(() => {
    Streamlit.setFrameHeight(56);
  }, [bedrock, bedrockLabel, pending, vectorCount, articleCount]);

  const pills = [
    {
      label: bedrockLabel ?? (bedrock ? "Bedrock ready" : "Bedrock not configured"),
      kind: bedrockKind ?? (bedrock ? "positive" : "negative"),
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
