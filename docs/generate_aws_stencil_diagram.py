#!/usr/bin/env python3
"""
Generate AWS architecture diagram using official AWS Architecture Icons (diagrams package).

Output: docs/aws-architecture-diagram.png

Requires: pip install diagrams  &&  brew install graphviz
"""

from __future__ import annotations

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.analytics import AmazonOpensearchService
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.ml import Bedrock
from diagrams.aws.security import IdentityAndAccessManagementIam
from diagrams.aws.storage import S3
from diagrams.aws.management import Cloudwatch
from diagrams.generic.database import SQL
from diagrams.generic.storage import Storage
from diagrams.onprem.client import User, Users
from diagrams.onprem.network import Internet
from diagrams.programming.language import Python

OUT = Path(__file__).resolve().parent / "aws-architecture-diagram.png"
ICON_PATH = Path(__file__).resolve().parent / "icons"

# diagrams uses Graphviz; left-right layout fits architecture flows
graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.4",
    "nodesep": "0.55",
    "ranksep": "0.85",
    "splines": "ortho",
}

node_attr = {"fontsize": "11"}


def build() -> None:
    with Diagram(
        "AI Market Intelligence Dashboard\nPhase 1+2 · Streamlit + Amazon Bedrock + local SQLite/ChromaDB",
        filename=str(OUT.with_suffix("")),  # diagrams appends .png
        show=False,
        direction="LR",
        graph_attr=graph_attr,
        node_attr=node_attr,
        outformat="png",
    ):
        user = User("Trader / Analyst\n(Web browser)")

        with Cluster("Deploy & source"):
            github_note = Python("GitHub repo\napp.py · src/\nfrontend/build")
            streamlit_host = Python("Streamlit Cloud\nor local/Docker\nPython 3.11")

        with Cluster("Streamlit application (app.py + src/)"):
            streamlit_app = Python(
                "Streamlit + React UI\n"
                "summarizer · rag_pipeline\n"
                "embeddings · vector_store"
            )

            with Cluster("Ephemeral local stores\n(lost on Streamlit Cloud redeploy)"):
                sqlite_db = SQL(
                    "SQLite — database.py\n"
                    "market_news.db\n"
                    "summaries · sentiment · topics"
                )
                chroma_db = Storage(
                    "ChromaDB — vector_store.py\n"
                    "data/vector_db/\n"
                    "semantic search · RAG top-k"
                )

        with Cluster("AWS Cloud · AWS_REGION"):
            iam = IdentityAndAccessManagementIam(
                "IAM credentials\nbedrock:InvokeModel\nSecrets / .env"
            )

            with Cluster("Amazon Bedrock (bedrock_client.py)"):
                bedrock = Bedrock(
                    "Bedrock Runtime API\n"
                    "invoke_model · us-east-1"
                )
                chat_model = Bedrock(
                    "Inference profile — chat\n"
                    "us.anthropic.claude-*\n"
                    "amazon.nova-lite-v1:0"
                )
                embed_model = Bedrock(
                    "Titan Text Embeddings V2\n"
                    "amazon.titan-embed-text-v2:0\n"
                    "1024 dimensions"
                )

            cw = Cloudwatch("Model access · CloudWatch\nconsole enablement")

            with Cluster("Phase 3 (planned)"):
                aoss = AmazonOpensearchService("OpenSearch Serverless\nvector search")
                s3 = S3("S3\narticle archive")
                ddb = Dynamodb("DynamoDB / metadata")
                fn = Lambda("Lambda\nscheduled ingest")

        with Cluster("External news APIs (optional)"):
            internet = Internet("Finnhub · NewsAPI\nYahoo Finance RSS")

        # --- Data flows ---
        user >> Edge(label="① HTTPS") >> streamlit_host >> streamlit_app

        internet >> Edge(label="③ ingest headlines") >> streamlit_app
        streamlit_app >> Edge(label="persist") >> sqlite_db

        iam >> Edge(label="credentials") >> bedrock
        streamlit_app >> Edge(label="④ summarize\n⑤ RAG chat") >> bedrock
        bedrock >> chat_model
        bedrock >> Edge(label="⑥ embed") >> embed_model

        chat_model >> Edge(label="JSON summaries") >> streamlit_app
        streamlit_app >> Edge(label="cache") >> sqlite_db

        embed_model >> Edge(label="vectors") >> streamlit_app
        streamlit_app >> Edge(label="⑦ sync") >> chroma_db

        streamlit_app >> Edge(label="⑧ RAG retrieve") >> chroma_db
        chroma_db >> Edge(label="top-k context") >> streamlit_app

        bedrock >> cw

        # Phase 3 dashed future path
        streamlit_app >> Edge(label="future", style="dashed") >> aoss
        sqlite_db >> Edge(style="dashed") >> s3
        streamlit_app >> Edge(style="dashed") >> fn
        fn >> Edge(style="dashed") >> ddb

        github_note >> Edge(style="dotted", label="CI/CD deploy") >> streamlit_host


if __name__ == "__main__":
    build()
    print(f"Wrote {OUT}")
