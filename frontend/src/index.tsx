import React from "react";
import ReactDOM from "react-dom/client";
import {
  ComponentProps,
  Streamlit,
  withStreamlitConnection,
} from "streamlit-component-lib";
import { ArticleFeed } from "./components/ArticleFeed";
import { DashboardPanel } from "./components/DashboardPanel";
import { MarketAgent } from "./components/MarketAgent";
import { MetricsGrid } from "./components/MetricsGrid";
import { RagResults } from "./components/RagResults";
import { StatusBar } from "./components/StatusBar";
import type { ComponentArgs } from "./types";
import "./theme.css";

Streamlit.setFrameHeight(0);

class Root extends React.PureComponent<ComponentProps> {
  render(): React.ReactNode {
    const args = (this.props.args ?? {}) as ComponentArgs;
    const view = args.view ?? "";

    switch (view) {
      case "status_bar":
        return (
          <StatusBar
            bedrock={args.bedrock}
            pending={args.pending}
            vectorCount={args.vectorCount}
            articleCount={args.articleCount}
          />
        );
      case "metrics":
        return <MetricsGrid metrics={args.metricItems ?? args.metrics} />;
      case "dashboard":
        return <DashboardPanel sentiment={args.sentiment} topics={args.topics} />;
      case "article_feed":
        return <ArticleFeed articles={args.articles} embedded={Boolean(args.embedded)} />;
      case "rag_results":
        return <RagResults articles={args.articles} title={args.placeholder} />;
      case "market_agent":
        return (
          <MarketAgent
            messages={args.messages}
            examples={args.examples}
            placeholder={args.placeholder}
            answer={args.answer}
            sources={args.sources}
            evidence={args.evidence}
          />
        );
      default:
        return (
          <div className="mi-root" style={{ color: "#ef4444" }}>
            Unknown view: {view}
          </div>
        );
    }
  }
}

const Connected = withStreamlitConnection(Root);
const rootEl = document.getElementById("root");
if (rootEl) {
  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      <Connected />
    </React.StrictMode>
  );
}
