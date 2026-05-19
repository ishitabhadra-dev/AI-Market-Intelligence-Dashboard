# Production deployment (no Docker)

Use this guide if **Docker is not installed**. These steps match a real production setup: background service, logs, persistent data, and optional cloud hosting.

---

## Quick start (your Mac)

```bash
cd "/Users/ishitabhadra/Desktop/AI Market Intelligence Dashboard"

./scripts/production_install.sh    # once: venv, deps, frontend build
# Edit .env — AWS_REGION, BEDROCK_CHAT_MODEL_ID, AWS keys if needed

./scripts/production.sh start      # runs in background on port 8501
./scripts/production.sh status
./scripts/production.sh logs       # tail logs
./scripts/production.sh stop
```

Open **http://localhost:8501**

Data is stored in `data/` (SQLite + ChromaDB). Logs go to `logs/dashboard.log`.

---

## What “production” means here

| Feature | How |
|---------|-----|
| Background process | `production.sh` + `nohup` |
| Headless server | `0.0.0.0:8501`, no browser auto-open |
| `DEPLOY_ENV=production` | Hides dev-only UI hints |
| Persistent DB | `data/market_news.db`, `data/vector_db/` |
| React UI | Built into `frontend/build/` |
| Health | `curl http://localhost:8501/_stcore/health` |

---

## Auto-start on Mac (optional)

1. Edit `deploy/macos/com.marketintel.dashboard.plist` — replace `REPLACE_WITH_PROJECT_ROOT` with your full project path (3 places).
2. Install:

```bash
PROJECT="/Users/ishitabhadra/Desktop/AI Market Intelligence Dashboard"
sed "s|REPLACE_WITH_PROJECT_ROOT|$PROJECT|g" \
  deploy/macos/com.marketintel.dashboard.plist \
  > ~/Library/LaunchAgents/com.marketintel.dashboard.plist
launchctl load ~/Library/LaunchAgents/com.marketintel.dashboard.plist
```

Unload: `launchctl unload ~/Library/LaunchAgents/com.marketintel.dashboard.plist`

---

## Linux VPS (Ubuntu)

On a server (e.g. EC2):

```bash
sudo apt update && sudo apt install -y python3.11-venv git curl
sudo mkdir -p /opt/ai-market-intelligence
sudo chown $USER:$USER /opt/ai-market-intelligence
# clone or scp your project into /opt/ai-market-intelligence

cd /opt/ai-market-intelligence
./scripts/production_install.sh
nano .env   # AWS + Bedrock settings

./scripts/production.sh start
```

**systemd** (survives reboot):

```bash
sudo cp deploy/linux/market-intelligence.service /etc/systemd/system/
# Edit User= and paths if not using /opt/ai-market-intelligence
sudo systemctl daemon-reload
sudo systemctl enable market-intelligence
sudo systemctl start market-intelligence
sudo systemctl status market-intelligence
```

Use a security group / firewall: allow **8501** only from trusted IPs, or put **nginx** in front with HTTPS.

---

## Cloud hosting (no Docker on your laptop)

### Streamlit Community Cloud (easiest)

1. Push project to **GitHub** (include `frontend/build/` or let CI build it).
2. [share.streamlit.io](https://share.streamlit.io) → New app → `app.py`.
3. **Secrets** → paste from `.streamlit/secrets.toml.example` + AWS keys.
4. Deploy → share the public URL.

Note: free tier storage is ephemeral; fine for demos.

### Render.com

1. Push to GitHub.
2. [render.com](https://render.com) → New **Blueprint** → connect repo (`render.yaml` included).
3. Set environment variables in the dashboard (`AWS_*`, `BEDROCK_*`).
4. Deploy.

---

## AWS credentials

**On your Mac / VPS**, either:

- `aws configure` and leave `AWS_ACCESS_KEY_ID` empty in `.env`, or  
- Set in `.env`:

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

**On AWS EC2**, prefer an **IAM instance role** with `bedrock:InvokeModel` (no keys in `.env`).

---

## Production checklist

- [ ] `./scripts/production_install.sh`
- [ ] `.env` configured (Bedrock model IDs for your region)
- [ ] `./scripts/production.sh start` and health check passes
- [ ] Ingest news → summarize → sync vector DB (demo flow)
- [ ] `.env` not committed to git
- [ ] Firewall / HTTPS if exposed to the internet

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Failed to start` | `cat logs/dashboard.log` |
| Port in use | `PORT=8502 ./scripts/production.sh start` |
| No React UI | `./scripts/build_frontend.sh` |
| Bedrock errors | Check `.env` model IDs and IAM |

Docker-based deploy is optional — see [DEPLOY.md](DEPLOY.md).
