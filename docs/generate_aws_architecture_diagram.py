#!/usr/env python3
"""Fallback diagram (matplotlib boxes). Prefer docs/generate_aws_stencil_diagram.py for AWS icons."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent / "aws-architecture-diagram.png"

# AWS-inspired palette
AWS_ORANGE = "#FF9900"
AWS_DARK = "#232F3E"
AWS_LIGHT = "#F2F3F3"
BEDROCK = "#7B3FF2"
COMPUTE = "#ED7100"
DATABASE = "#3B48CC"
SECURITY = "#DD344C"
EXTERNAL = "#545B64"
STREAMLIT = "#FF4B4B"
LOCAL = "#1D8102"
TEXT = "#16191F"
MUTED = "#5F6B7A"
ARROW = "#879596"


def box(ax, x, y, w, h, title, lines, face, edge=AWS_DARK, title_size=9, line_size=7.5):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.4,
        edgecolor=edge,
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h - 0.35, title, ha="center", va="top", fontsize=title_size, fontweight="bold", color=TEXT, zorder=3)
    body = "\n".join(lines)
    ax.text(x + 0.15, y + h - 0.75, body, ha="left", va="top", fontsize=line_size, color=TEXT, linespacing=1.35, zorder=3)
    return patch


def arrow(ax, x1, y1, x2, y2, label="", style="-|>", color=ARROW):
    arr = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle=style,
        mutation_scale=12,
        linewidth=1.2,
        color=color,
        connectionstyle="arc3,rad=0.08",
        zorder=1,
    )
    ax.add_patch(arr)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my + 0.12, label, ha="center", va="bottom", fontsize=6.5, color=MUTED, style="italic", zorder=4)


def main() -> None:
    fig, ax = plt.subplots(figsize=(20, 14), dpi=150)
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 14)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        10,
        13.55,
        "AI Market Intelligence Dashboard — AWS Architecture",
        ha="center",
        fontsize=18,
        fontweight="bold",
        color=AWS_DARK,
    )
    ax.text(
        10,
        13.05,
        "Phase 1 + 2 (current) · Streamlit + Bedrock + local SQLite/ChromaDB · Phase 3 planned",
        ha="center",
        fontsize=10,
        color=MUTED,
    )

    # --- User ---
    box(
        ax, 0.4, 11.2, 2.6, 1.5,
        "End User",
        ["Web browser", "Dashboard · Feed · RAG · Agent"],
        "#E8F4FD",
        edge="#0073BB",
    )

    # --- Streamlit hosting ---
    st_patch = FancyBboxPatch(
        (3.3, 9.8), 4.2, 3.2,
        boxstyle="round,pad=0.03,rounding_size=0.1",
        linewidth=2,
        edgecolor=STREAMLIT,
        facecolor="#FFF5F5",
        linestyle="--",
        zorder=1,
    )
    ax.add_patch(st_patch)
    ax.text(5.4, 12.75, "Streamlit Host (deploy)", ha="center", fontsize=10, fontweight="bold", color=STREAMLIT)

    box(
        ax, 3.5, 11.0, 3.8, 1.55,
        "Streamlit App  app.py",
        ["Python 3.11 · boto3", "Sidebar: ingest · summarize · sync", "Tabs: Dashboard · Feed · RAG"],
        "#FFFFFF",
        edge=STREAMLIT,
    )
    box(
        ax, 3.5, 10.05, 3.8, 0.85,
        "React UI (Vite)",
        ["Custom components: StatusBar, ArticleFeed,", "MarketAgent, RagResults → frontend/build"],
        "#FFECEC",
        edge=STREAMLIT,
        title_size=8,
        line_size=6.5,
    )

    # --- Local data (inside app host) ---
    local_patch = FancyBboxPatch(
        (3.3, 7.55), 4.2, 2.05,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.5,
        edgecolor=LOCAL,
        facecolor="#E9F7EF",
        zorder=1,
    )
    ax.add_patch(local_patch)
    ax.text(5.4, 9.35, "App-local persistence (ephemeral on Streamlit Cloud)", ha="center", fontsize=8, fontweight="bold", color=LOCAL)

    box(ax, 3.5, 7.75, 1.85, 1.35, "SQLite", ["data/market_news.db", "Articles · summaries", "sentiment · topics"], "#D5F5E3", edge=LOCAL, title_size=8, line_size=6.5)
    box(ax, 5.55, 7.75, 1.85, 1.35, "ChromaDB", ["data/vector_db/", "Titan embeddings", "semantic search"], "#D5F5E3", edge=LOCAL, title_size=8, line_size=6.5)

    # --- AWS Cloud boundary ---
    cloud = FancyBboxPatch(
        (8.0, 1.0), 11.5, 12.0,
        boxstyle="round,pad=0.04,rounding_size=0.15",
        linewidth=2.5,
        edgecolor=AWS_ORANGE,
        facecolor="#FFF8F0",
        zorder=0,
    )
    ax.add_patch(cloud)
    ax.text(13.75, 12.75, "AWS Cloud", ha="center", fontsize=14, fontweight="bold", color=AWS_ORANGE)
    ax.text(13.75, 12.35, "Region: AWS_REGION (e.g. us-east-1)", ha="center", fontsize=9, color=MUTED)

    # IAM
    box(
        ax, 8.3, 10.8, 3.2, 1.45,
        "IAM",
        ["User / role credentials", "bedrock:InvokeModel", "AWS_ACCESS_KEY_ID (Secrets)"],
        "#FCE8E8",
        edge=SECURITY,
        title_size=9,
    )

    # Bedrock section
    bedrock_region = FancyBboxPatch(
        (8.2, 4.5), 10.9, 6.0,
        boxstyle="round,pad=0.02,rounding_size=0.1",
        linewidth=1.8,
        edgecolor=BEDROCK,
        facecolor="#F5F0FF",
        zorder=1,
    )
    ax.add_patch(bedrock_region)
    ax.text(13.65, 10.25, "Amazon Bedrock", ha="center", fontsize=12, fontweight="bold", color=BEDROCK)

    box(
        ax, 8.5, 8.7, 3.3, 1.35,
        "Bedrock Runtime API",
        ["boto3 bedrock-runtime", "invoke_model", "src/bedrock_client.py"],
        "#EDE7FF",
        edge=BEDROCK,
        title_size=9,
    )

    box(
        ax, 12.1, 8.7, 3.4, 1.35,
        "Inference profiles",
        ["us.anthropic.claude-* (chat)", "Cross-region routing", "BEDROCK_CHAT_MODEL_ID"],
        "#EDE7FF",
        edge=BEDROCK,
        title_size=9,
    )

    box(
        ax, 8.5, 6.9, 3.3, 1.55,
        "Foundation model\n(Phase 1 + 2 Chat)",
        ["Claude 3.5 Haiku / Sonnet", "Amazon Nova Lite", "Summaries · RAG Q&A · briefs"],
        "#FFFFFF",
        edge=BEDROCK,
        title_size=8.5,
    )

    box(
        ax, 12.1, 6.9, 3.4, 1.55,
        "Amazon Titan\nText Embeddings V2",
        ["amazon.titan-embed-text-v2:0", "1024-d vectors", "src/embeddings.py"],
        "#FFFFFF",
        edge=BEDROCK,
        title_size=8.5,
    )

    box(
        ax, 8.5, 4.85, 7.0, 1.75,
        "Model access & governance",
        ["Console → Model access (enable models)", "CloudWatch logs (optional)", "Service quotas · responsible AI"],
        "#F8F8F8",
        edge=BEDROCK,
        title_size=8.5,
        line_size=7,
    )

    # Phase 3
    box(
        ax, 8.3, 1.35, 5.2, 2.55,
        "Phase 3 (planned)",
        ["Amazon OpenSearch Serverless", "Vector engine replaces ChromaDB", "S3 · RDS/DynamoDB · Lambda optional"],
        AWS_LIGHT,
        edge=DATABASE,
        title_size=9,
    )

    # External APIs
    ext_patch = FancyBboxPatch(
        (14.0, 7.5), 5.2, 5.5,
        boxstyle="round,pad=0.02,rounding_size=0.1",
        linewidth=1.5,
        edgecolor=EXTERNAL,
        facecolor="#F7F8F8",
        linestyle=":",
        zorder=1,
    )
    ax.add_patch(ext_patch)
    ax.text(16.6, 12.75, "External (non-AWS)", ha="center", fontsize=10, fontweight="bold", color=EXTERNAL)

    box(ax, 14.2, 10.9, 4.8, 1.35, "Finnhub API", ["FINNHUB_API_KEY", "Market headlines"], "#FFFFFF", edge=EXTERNAL, title_size=8.5)
    box(ax, 14.2, 9.35, 4.8, 1.35, "NewsAPI", ["NEWSAPI_KEY", "Financial news"], "#FFFFFF", edge=EXTERNAL, title_size=8.5)
    box(ax, 14.2, 7.8, 4.8, 1.35, "Yahoo Finance RSS", ["Public RSS fallback", "Demo mode if no keys"], "#FFFFFF", edge=EXTERNAL, title_size=8.5)

    # GitHub / Streamlit Cloud
    box(ax, 0.4, 7.5, 2.6, 1.8, "GitHub", ["Source repo", "app.py · src/ · frontend/build", "CI optional"], "#F0F0F0", edge=EXTERNAL, title_size=8.5)
    box(ax, 0.4, 5.4, 2.6, 1.7, "Streamlit Cloud", ["share.streamlit.io", "Secrets → AWS keys", "Python 3.11 · environment.yml"], "#FFE8E8", edge=STREAMLIT, title_size=8.5)

    # --- Arrows / flows ---
    arrow(ax, 3.0, 12.0, 3.5, 12.0, "① HTTPS")
    arrow(ax, 5.4, 11.0, 5.4, 9.1, "② UI bridge")
    arrow(ax, 4.4, 7.75, 4.4, 7.55)
    arrow(ax, 6.4, 7.75, 6.4, 7.55)

    arrow(ax, 7.3, 8.4, 8.3, 9.2, "③ ingest")
    arrow(ax, 16.6, 10.9, 7.3, 8.8, "", style="-|>", color=EXTERNAL)
    arrow(ax, 7.3, 8.2, 8.5, 9.3, "④ summarize")

    arrow(ax, 7.35, 8.0, 9.9, 7.5, "⑤ invoke_model")
    arrow(ax, 10.0, 7.5, 10.0, 8.7)
    arrow(ax, 11.8, 7.6, 13.5, 7.6)
    arrow(ax, 7.35, 7.9, 13.3, 7.2, "⑥ embed")

    arrow(ax, 7.35, 7.5, 6.9, 7.75, "⑦ upsert")
    arrow(ax, 9.7, 11.5, 7.35, 8.5, "⑧ RAG query", color=BEDROCK)

    arrow(ax, 3.0, 6.3, 3.5, 10.5, "deploy", color=STREAMLIT)
    arrow(ax, 3.0, 8.4, 3.3, 8.4, "", color=EXTERNAL)

    # Flow legend
    legend_box = FancyBboxPatch(
        (0.35, 0.35), 7.5, 4.5,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.2,
        edgecolor=AWS_DARK,
        facecolor="white",
        zorder=2,
    )
    ax.add_patch(legend_box)
    ax.text(4.1, 4.6, "Data flows (numbered)", ha="center", fontsize=10, fontweight="bold", color=AWS_DARK)
    flows = [
        "① User opens Streamlit dashboard (browser)",
        "② React components render charts, feed, RAG UI",
        "③ Refresh news → Finnhub / NewsAPI / RSS → SQLite",
        "④ Summarize pending → Bedrock Claude/Nova → SQLite cache",
        "⑤⑥ Titan embeddings + ChromaDB sync (vector search)",
        "⑦ RAG: query embed → Chroma top-k → Bedrock answer + citations",
        "⑧ Secrets: AWS keys + model IDs via Streamlit Secrets / .env",
    ]
    for i, line in enumerate(flows):
        ax.text(0.55, 4.15 - i * 0.48, line, ha="left", va="top", fontsize=7.5, color=TEXT)

    # Component legend
    patches = [
        mpatches.Patch(facecolor="#FFF8F0", edgecolor=AWS_ORANGE, label="AWS Cloud boundary"),
        mpatches.Patch(facecolor="#F5F0FF", edgecolor=BEDROCK, label="Amazon Bedrock"),
        mpatches.Patch(facecolor="#E9F7EF", edgecolor=LOCAL, label="Local / ephemeral store"),
        mpatches.Patch(facecolor="#FFF5F5", edgecolor=STREAMLIT, label="Streamlit host"),
        mpatches.Patch(facecolor="#F7F8F8", edgecolor=EXTERNAL, label="External APIs"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=8, frameon=True, title="Legend", title_fontsize=9)

    ax.text(
        10,
        0.15,
        "src/: bedrock_client · summarizer · embeddings · vector_store · rag_pipeline · database · news_ingestion",
        ha="center",
        fontsize=7.5,
        color=MUTED,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
