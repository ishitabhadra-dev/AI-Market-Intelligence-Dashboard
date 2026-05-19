# Deployment Guide

Production deployment options for the **AI Market Intelligence Dashboard**.

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **AWS account** | Bedrock enabled in your region |
| **IAM** | `bedrock:InvokeModel` on Titan + your chat model |
| **Models** | `amazon.titan-embed-text-v2:0` + inference profile (e.g. `us.anthropic.claude-sonnet-4-6`) |
| **News APIs** | Optional — Yahoo RSS works without keys |

---

## Production checklist

- [ ] Copy `.env.example` → `.env` and set Bedrock model IDs for your region
- [ ] AWS credentials via IAM role (preferred) or `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- [ ] Build React UI: `./scripts/build_frontend.sh` (or use Docker, which builds automatically)
- [ ] Persistent volume for `/app/data` (SQLite + ChromaDB)
- [ ] Do **not** commit `.env` or `.streamlit/secrets.toml`
- [ ] Rotate any keys that were ever committed

---

## Option 1: Docker (recommended)

Builds the React frontend inside the image — no local Node required on the server.

```bash
cp .env.example .env
# Edit .env: AWS_REGION, BEDROCK_*_MODEL_ID, optional AWS keys

docker compose up --build -d
```

Open **http://localhost:8501**

### Commands

```bash
docker compose logs -f          # logs
docker compose down           # stop
docker compose down -v          # stop + delete data volume
```

### Data persistence

`docker-compose.yml` mounts a named volume `market-data` at `/app/data` (SQLite + ChromaDB).

### AWS credentials in Docker

**Option A — Environment variables** (`.env`):

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

**Option B — IAM task role** (ECS/Fargate): attach a role with `bedrock:InvokeModel`; omit access keys.

---

## Option 2: Docker without Compose

```bash
docker build -t ai-market-intelligence .
docker run -d \
  --name market-dashboard \
  -p 8501:8501 \
  --env-file .env \
  -v market-data:/app/data \
  --restart unless-stopped \
  ai-market-intelligence
```

Health check: `curl http://localhost:8501/_stcore/health`

---

## Option 3: Local production script

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/build_frontend.sh
cp .env.example .env   # configure
./scripts/start.sh
```

Listens on `0.0.0.0:8501` (set `PORT` to change).

---

## Option 4: Streamlit Community Cloud

1. Push the repo to GitHub (include `frontend/build/` **or** rely on CI to build it).
2. [share.streamlit.io](https://share.streamlit.io) → **New app** → select repo, `app.py`.
3. **Secrets** → paste TOML from `.streamlit/secrets.toml.example` and add AWS keys if needed.
4. Deploy.

**Note:** ChromaDB + SQLite persist only for the lifetime of the container on free tier. For durable data, use Docker/AWS with a volume.

### Secrets example (Streamlit UI)

```toml
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "AKIA..."
AWS_SECRET_ACCESS_KEY = "..."
BEDROCK_CHAT_MODEL_ID = "us.anthropic.claude-sonnet-4-6"
BEDROCK_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
VECTOR_DB_PATH = "data/vector_db"
```

---

## Option 5: AWS ECS / EC2 (outline)

1. Push image to **ECR**: `docker build -t ... && docker push ...`
2. **ECS Fargate** service with:
   - Task role: `bedrock:InvokeModel`
   - EFS or EBS volume mounted at `/app/data`
   - ALB → target group port **8501**
3. Set env vars from **Secrets Manager** / task definition.

For **EC2**: install Docker, run the same `docker run` command, use an IAM instance profile instead of static keys.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_REGION` | Yes | e.g. `us-east-1` |
| `BEDROCK_CHAT_MODEL_ID` | Yes | Inference profile id |
| `BEDROCK_EMBEDDING_MODEL_ID` | Yes | `amazon.titan-embed-text-v2:0` |
| `AWS_ACCESS_KEY_ID` | If no IAM role | For Bedrock API |
| `AWS_SECRET_ACCESS_KEY` | If no IAM role | For Bedrock API |
| `VECTOR_DB_PATH` | No | Default `data/vector_db` |
| `FINNHUB_API_KEY` | No | More news sources |
| `NEWSAPI_KEY` | No | More news sources |
| `PORT` | No | Default `8501` |
| `DEPLOY_ENV` | No | Set `production` to hide dev hints |

---

## CI/CD

GitHub Actions workflow `.github/workflows/ci.yml` runs on push/PR:

- Builds React frontend
- Installs Python deps
- Compiles `app.py` + `src/`

Use the same steps before releasing a Docker image tag.

---

## Troubleshooting (production)

| Issue | Fix |
|-------|-----|
| Blank / fallback UI | Rebuild frontend or use Docker image (includes build) |
| Bedrock `AccessDenied` | IAM policy + model access in console |
| Data lost after restart | Mount a volume at `data/` |
| Health check failing | Wait 60s on first start; check logs |
| `npm not found` on server | Use Docker — Node is only in build stage |

---

## Security

- Never commit `.env` or AWS keys.
- Prefer **IAM roles** over long-lived access keys on AWS.
- Restrict security groups / firewall to trusted IPs for internal demos.
- Rotate credentials if exposed.
