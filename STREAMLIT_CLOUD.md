# Deploy to Streamlit Community Cloud

Production hosting with **no Docker** — Streamlit runs the app and serves a public URL.

---

## Before you deploy

1. **GitHub repo** with your project pushed.
2. **`frontend/build/` committed** — Streamlit Cloud does not run `npm build`.  
   Locally run once, then commit:
   ```bash
   ./scripts/build_frontend.sh
   git add frontend/build
   git commit -m "Add React build for Streamlit Cloud"
   ```
3. **AWS Bedrock** credentials and model access in your region.

---

## Step 1: Push to GitHub

```bash
cd "/Users/ishitabhadra/Desktop/AI Market Intelligence Dashboard"
git init   # if needed
git add app.py src/ requirements.txt .streamlit/ frontend/build/
git add STREAMLIT_CLOUD.md README.md
git commit -m "Streamlit Cloud deploy"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

Do **not** commit `.env` (secrets stay in Streamlit UI).

---

## Step 2: Create the app on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **Create app**.
3. Choose your repository, branch `main`, main file **`app.py`**.
4. Python **3.11** is set via `.python-version` in the repo (required for ChromaDB).

---

## Step 3: Add secrets

In the app → **Settings** → **Secrets**, paste (edit values):

```toml
DEPLOY_ENV = "production"
DEPLOY_TARGET = "streamlit-cloud"

AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "AKIAxxxxxxxx"
AWS_SECRET_ACCESS_KEY = "your-secret-key"

BEDROCK_CHAT_MODEL_ID = "us.anthropic.claude-sonnet-4-6"
BEDROCK_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
BEDROCK_MAX_TOKENS = 1024
TITAN_EMBED_DIMENSIONS = 1024
VECTOR_DB_PATH = "data/vector_db"

# Optional — more news sources
# FINNHUB_API_KEY = ""
# NEWSAPI_KEY = ""
```

Save → the app **reboots** automatically.

Use IAM keys with **`bedrock:InvokeModel`** only (least privilege).

---

## Step 4: Deploy & open

Click **Deploy** (or wait for auto-deploy). Your app will be at:

`https://YOUR_APP_NAME.streamlit.app`

---

## Demo flow on Cloud

1. **Refresh market news** (sidebar)
2. **Summarize ALL pending**
3. **RAG Intelligence** → **Sync Articles to Vector DB**
4. Try semantic search or **Ask the Market Agent**

---

## Important: data on Streamlit Cloud

| Storage | Behavior |
|---------|----------|
| SQLite + ChromaDB | Live under `data/` on the container |
| **Persistence** | **Not guaranteed** across redeploys or sleep (free tier) |
| Best for | Demos, portfolios, class presentations |

For durable data long-term, use AWS (RDS, OpenSearch) in a later phase.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Unable to locate package` in logs | Remove `packages.txt` or leave it **empty** (no `#` comments) |
| `Descriptors cannot be created` / protobuf | Use `.python-version` = `3.11` and pinned `requirements.txt` (push latest) |
| App crashes on start | Check **Logs** in Streamlit Cloud; verify `requirements.txt` |
| React UI missing / fallback widgets | Commit `frontend/build/` to GitHub |
| Bedrock `AccessDenied` | IAM policy + correct model IDs in Secrets |
| `inference profile` error | Use `us.anthropic...` profile id from Bedrock console |
| Slow cold start | Normal — ChromaDB + dependencies on first load |
| Secrets not picked up | Keys must be flat TOML strings (see example above) |

---

## Local dev vs Cloud

| | Local | Streamlit Cloud |
|---|--------|-----------------|
| Secrets | `.env` file | App **Secrets** UI |
| React build | `./scripts/build_frontend.sh` | Commit `frontend/build/` |
| URL | `localhost:8501` | `*.streamlit.app` |

Copy template from `.streamlit/secrets.toml.example`.
