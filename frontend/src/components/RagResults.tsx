import { useEffect } from "react";
import { Streamlit } from "streamlit-component-lib";
import { ArticleFeed } from "./ArticleFeed";
import type { Article } from "../types";

interface Props {
  articles?: Article[];
  title?: string;
}

/** Read-only search hit list (expandable cards). */
export function RagResults({ articles = [], title = "Results" }: Props) {
  useEffect(() => {
    Streamlit.setFrameHeight(Math.min(600, 100 + articles.length * 70));
  }, [articles.length]);

  if (articles.length === 0) {
    return (
      <div className="mi-root">
        <p className="mi-empty" style={{ color: "#8b9cb8", margin: 0 }}>
          No results to display.
        </p>
      </div>
    );
  }

  return (
    <div className="mi-root">
      <p style={{ margin: "0 0 0.5rem", fontWeight: 600, color: "#f1f5f9" }}>{title}</p>
      <ArticleFeed articles={articles} embedded />
    </div>
  );
}
