# Zendesk to Vertex AI Chatbot Crawler

Automated system that crawls Zendesk articles and syncs them to Google Vertex AI Data Store for AI-powered chatbot responses.

## What It Does

Crawls your Zendesk help center → Uploads to Google Cloud Storage → Syncs to Vertex AI → Powers intelligent chatbot

![Chatbot Demo](result/chatbot-demo.png)
*Chatbot answers questions with direct links to source articles*

---

## Quick Setup

### Prerequisites
- Docker & Docker Compose
- GCP Project with Storage & Vertex AI enabled
- Zendesk API access

### 1. Configure GCP Credentials

Place your service account key in folder:
```bash
keys/service-account-key.json
```

### 2. Set Environment Variables

Create `.env` file:
```env
ZENDESK_API_URL=https://your-company.zendesk.com/api/v2/help_center/articles.json
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket-name
VERTEX_AI_DATA_STORE_ID=your-datastore-id
VERTEX_AI_LOCATION=us
GOOGLE_APPLICATION_CREDENTIALS=/app/keys/service-account-key.json
```

### 3. Build & Run

```bash
# Build the Docker image
docker compose build

# Run (will execute immediately, then schedule daily at midnight)
docker compose up -d
```

---

## Run Locally (Without Docker)

### 1. Install Dependencies
```bash
# With uv
uv pip install .
```

### 2. Set Environment Variables
```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Run the Crawler
```bash
python main.py
```

---

## View Results

### Execution Logs
Check the `logs/` directory for detailed execution logs:
```bash
ls -lt logs/
cat logs/20260104_000000.log
```

Sample log output:
```
============================================================
=== Vertex AI Sync Summary ===
============================================================
Successfully synced: 399
  - Added: 350
  - Updated: 49
  - Skipped: 0
Failed to sync: 0
Sync time: 3.45 minutes
============================================================
```

### Playground Results

![Chatbot Demo](result/chatbot-demo.png)

### Daily Job Logs (Docker)
```bash
# View cron job logs
docker compose exec article-crawler tail -f /app/logs/cron.log

# View live container logs
docker compose logs -f
```

### Generated Files
- **`articles/`** - Markdown files for each article
- **`data/articles.db`** - SQLite database tracking sync status
- **`logs/`** - Timestamped execution logs