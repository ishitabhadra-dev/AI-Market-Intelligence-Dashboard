# Docker deployment

Run the full app (React UI + Streamlit + Bedrock + ChromaDB) in one container. **No local Node or Python required** after Docker is installed.

---

## Step 1: Install Docker Desktop (Mac)

1. Download: [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)  
   (Apple Silicon → **Mac with Apple chip**; Intel Mac → **Mac with Intel chip**)

   Or Homebrew:
   ```bash
   brew install --cask docker
   ```

2. Open **Docker** from Applications.

3. Wait until the menu bar whale icon says **Docker Desktop is running**.

4. Verify in Terminal:
   ```bash
   docker --version
   docker compose version
   ```

If you see `command not found`, **quit and reopen Terminal** after installing Docker.

---

## Step 2: Configure environment

```bash
cd "/Users/ishitabhadra/Desktop/AI Market Intelligence Dashboard"
cp .env.example .env
```

Edit `.env` — minimum for Bedrock:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
BEDROCK_CHAT_MODEL_ID=us.anthropic.claude-sonnet-4-6
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
```

Remove or comment out `AWS_PROFILE=` (empty profile breaks the container).

---

## Step 3: Start

```bash
./scripts/docker_start.sh
```

Or manually:

```bash
docker compose up --build -d
```

Open **http://localhost:8501**

First build downloads Node + Python images and compiles the React UI (**3–5 minutes**).

---

## Daily commands

| Task | Command |
|------|---------|
| Start | `./scripts/docker_start.sh` or `docker compose up -d` |
| Logs | `docker compose logs -f` |
| Stop | `docker compose down` |
| Restart | `docker compose restart` |
| Rebuild after code changes | `docker compose up --build -d` |
| Health | `curl http://localhost:8501/_stcore/health` |

---

## Data persistence

SQLite and ChromaDB live in the Docker volume **`market-data`** (mounted at `/app/data`).

```bash
# List volumes
docker volume ls

# Delete all app data (fresh start)
docker compose down -v
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker: command not found` | Install Docker Desktop; reopen Terminal |
| `Cannot connect to Docker daemon` | Open Docker.app; wait until running |
| `env_file .env not found` | `cp .env.example .env` |
| Bedrock `AccessDenied` | Check IAM + model IDs in `.env` |
| Port 8501 in use | `PORT=8502 docker compose up -d` and open `:8502` |
| Build fails on `npm` | Check internet; retry `docker compose build --no-cache` |

---

## What the image includes

- **Stage 1:** Builds React → `frontend/build/`
- **Stage 2:** Python 3.11, Streamlit, ChromaDB, your `src/` code
- Health check on `/_stcore/health`
- Runs as non-root user `appuser`
- `restart: unless-stopped` in Compose

See also [DEPLOY.md](DEPLOY.md) for ECS/cloud options using the same image.
