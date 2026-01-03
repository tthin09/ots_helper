## Overview

This automated system crawls Zendesk help center articles and uploads them to Google Vertex AI Data Store to power an intelligent chatbot. The chatbot can answer customer questions by searching through your entire knowledge base, providing accurate responses with source references.

### How It Works

1. **Crawls** Zendesk articles via API
2. **Converts** HTML content to clean markdown format
3. **Uploads** articles to Google Cloud Storage bucket
4. **Syncs** with Vertex AI Data Store for AI-powered search
5. **Enables** chatbot to answer questions using your knowledge base

### Use Case: AI-Powered Support Chatbot

Once your articles are synced to Vertex AI Data Store, you can:
- Build a chatbot that answers customer questions automatically
- Provide accurate responses based on your help center content
- Include source links for users to read full articles
- Reduce support ticket volume with self-service AI

## Demo Results

After running the crawler, your Vertex AI chatbot will be able to answer questions like:

**User Question:** "How do I add content to multiple playlists at once?"

**Chatbot Response:**
```
You can add one or multiple assets to many playlists at the same time using the bulk assignment feature. 

To do this:
1. Select the assets you want to add
2. Click the "Add to Playlists" button
3. Choose the playlists from the list
4. Confirm your selection

Source: https://support.optisigns.com/articles/add-multiple-assets-to-playlists
```

### System Logs & Results

After running the crawler, check these folders:

**`logs/` folder** - Execution logs showing:
```
============================================================
=== Crawl Summary ===
============================================================
New articles: 25
Updated articles: 12
Unchanged articles: 362
Deleted articles: 0
Total articles processed: 399
Crawl time: 2.34 minutes

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

**`output/` folder** - Generated markdown files:
- Each article converted to `.md` format
- Includes article titles, content, and source links
- Ready for human review or further processing

**`data/` folder** - SQLite database:
- Tracks which articles have been processed
- Monitors upload and sync status
- Enables incremental updates (only syncs changes)

## Features

- 📥 **Automated Crawling**: Fetches articles from Zendesk API with change detection
- 📝 **HTML to Markdown**: Converts Zendesk HTML content to clean markdown format
- ☁️ **GCS Upload**: Batch uploads articles to Google Cloud Storage
- 🤖 **Vertex AI Sync**: Automatically imports documents into Vertex AI Data Store
- 🔄 **Daily Scheduling**: Runs automatically every day at midnight via cron
- 💾 **SQLite Database**: Tracks article changes and sync status
- 🐳 **Docker Support**: Fully containerized with Docker Compose

## Prerequisites

Before setting up, ensure you have:

1. **Docker & Docker Compose** installed on your system
2. **Zendesk API** access with articles endpoint URL
3. **Google Cloud Platform** account with:
   - A GCP project created
   - Cloud Storage bucket created
   - Vertex AI Data Store created
   - Service account with appropriate permissions

### GCP Service Account Permissions

Your service account needs these roles:
- `Storage Object Admin` (for GCS bucket access)
- `Discovery Engine Editor` (for Vertex AI Data Store)

## Setup Instructions

### 1. Clone or Download the Project

```bash
cd /path/to/project/ots_helper
```

### 2. Prepare GCP Service Account Key

1. Go to [GCP Console > IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Create a service account (or use existing)
3. Grant required permissions (see above)
4. Create a JSON key
5. Download and save as `keys/service-account-key.json`

```bash
# Create keys directory if it doesn't exist
mkdir -p keys

# Place your downloaded key file
mv ~/Downloads/your-key.json keys/service-account-key.json
```

### 3. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` file with your actual values:

```env
# Zendesk Configuration
ZENDESK_API_URL=https://your-company.zendesk.com/api/v2/help_center/articles.json

# Google Cloud Storage Configuration
GCS_BUCKET_NAME=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/app/keys/service-account-key.json

# Google Cloud Project Configuration
GCP_PROJECT_ID=your-project-id

# Vertex AI Data Store Configuration
VERTEX_AI_DATA_STORE_ID=your-datastore-id
VERTEX_AI_LOCATION=us
```

#### Environment Variable Explanations

| Variable | Description | Example |
|----------|-------------|---------|
| `ZENDESK_API_URL` | Full URL to your Zendesk articles API endpoint | `https://company.zendesk.com/api/v2/help_center/articles.json` |
| `GCS_BUCKET_NAME` | Name of your Google Cloud Storage bucket (not full URI) | `my-articles-bucket` |
| `GOOGLE_APPLICATION_CREDENTIALS` | **Do not change** - Path to service account key inside container | `/app/keys/service-account-key.json` |
| `GCP_PROJECT_ID` | Your Google Cloud project ID | `my-project-123456` |
| `VERTEX_AI_DATA_STORE_ID` | Data Store ID from Vertex AI Search console | `my-datastore-1_1234567890123` |
| `VERTEX_AI_LOCATION` | Location/region of your data store | `us` or `global` |

#### How to Find Your Values

**Zendesk API URL:**
- Go to your Zendesk help center
- Append `/api/v2/help_center/articles.json` to your domain
- Example: `https://yourcompany.zendesk.com/api/v2/help_center/articles.json`

**GCS Bucket Name:**
- Visit [GCP Console > Cloud Storage](https://console.cloud.google.com/storage)
- Your bucket name is listed (e.g., `optisigns-bucket-1`)

**GCP Project ID:**
- Visit [GCP Console](https://console.cloud.google.com)
- Project ID shown in the top bar (e.g., `my-project-123456`)

**Vertex AI Data Store ID:**
- Go to [Vertex AI Search console](https://console.cloud.google.com/gen-app-builder/engines)
- Select your data store
- Data Store ID is shown in the details (format: `name_1234567890123`)

**Vertex AI Location:**
- Check your data store location in Vertex AI console
- Common values: `us`, `global`, `eu`, etc.

### 4. Build and Run with Docker

Build the Docker image:

```bash
docker compose build
```

Start the container:

```bash
docker compose up
```

Or run in detached mode (background):

```bash
docker compose up -d
```

### 5. Verify Setup

Check the logs to ensure everything is working:

```bash
# View live logs
docker compose logs -f

# View specific log files
cat logs/20260103_120000.log  # Replace with actual timestamp
```

Expected output:
```
=== Starting Zendesk Article Crawler ===
Start time: 2026-01-03 00:00:00
Running in Docker: True
Database: /app/data/articles.db
Output: /app/output
✓ GCS client initialized successfully
✓ Vertex AI Data Store client initialized successfully
```

## Docker Container Behavior

### Initial Run
When you start the container with `docker compose up`, it will:
1. ✅ Run the crawler immediately
2. ✅ Process all Zendesk articles
3. ✅ Upload to GCS
4. ✅ Sync with Vertex AI
5. ✅ Start cron scheduler

### Daily Schedule
After the initial run, the crawler will automatically run:
- **Every day at midnight (00:00)** based on container timezone
- Logs are saved to `./logs/` directory
- All output files persist in `./output/` directory
- Database persists in `./data/` directory

## File Structure

```
ots_helper/
├── main.py                 # Main crawler script
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
├── pyproject.toml          # Python dependencies
├── .env                    # Environment variables (create from .env.example)
├── .env.example            # Example environment file
├── README.md               # This file
├── keys/
│   └── service-account-key.json  # GCP credentials (you provide)
├── data/
│   └── articles.db         # SQLite database (auto-created)
├── output/
│   └── *.md                # Generated markdown files
└── logs/
    └── *.log               # Application logs
```

## Managing the Container

### Stop the container
```bash
docker compose down
```

### Restart the container
```bash
docker compose restart
```

### View logs in real-time
```bash
docker compose logs -f
```

### Rebuild after code changes
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Run crawler manually (without waiting for cron)
```bash
docker compose exec article-crawler python /app/main.py
```

## Troubleshooting

### Issue: "GCS client not configured"

**Cause**: Missing or incorrect GCP credentials

**Solution**:
1. Verify `keys/service-account-key.json` exists
2. Check file has valid JSON format
3. Ensure service account has correct permissions

### Issue: "Vertex AI client not configured"

**Cause**: Missing environment variables or invalid Data Store ID

**Solution**:
1. Verify all required env vars in `.env` file
2. Check Data Store exists in Vertex AI console
3. Confirm `VERTEX_AI_LOCATION` matches your data store location

### Issue: Import completed with errors (0 items succeeded)

**Cause**: Data format mismatch or incorrect data schema

**Solution**:
- The code now uses `data_schema="content"` for unstructured text
- Verify files are uploaded to GCS bucket under `articles/` folder
- Check Vertex AI Data Store is configured for unstructured data

### Issue: Container keeps restarting

**Cause**: Error in environment configuration or missing dependencies

**Solution**:
```bash
# Check container logs
docker compose logs

# Run interactively to see errors
docker compose run --rm article-crawler python /app/main.py
```

### Issue: Cron job not running

**Cause**: Cron daemon not started or timezone issues

**Solution**:
```bash
# Check if cron is running
docker compose exec article-crawler pgrep cron

# Check cron logs
docker compose exec article-crawler cat /app/logs/cron.log

# Verify cron job is installed
docker compose exec article-crawler crontab -l
```

## Monitoring

### View Application Logs
```bash
# View latest log file
ls -lt logs/ | head -n 2
cat logs/YYYYMMDD_HHMMSS.log
```

### View Cron Execution Logs
```bash
docker compose exec article-crawler tail -f /app/logs/cron.log
```

### Check Database Status
```bash
# Install sqlite3 if not already installed
# Then view database
sqlite3 data/articles.db "SELECT COUNT(*) FROM articles;"
sqlite3 data/articles.db "SELECT COUNT(*) FROM articles WHERE uploaded = 1;"
```

## Advanced Configuration

### Change Cron Schedule

Edit the cron expression in `Dockerfile`:

```dockerfile
# Current: Daily at midnight
RUN echo "0 0 * * * cd /app && /usr/local/bin/python /app/main.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/crawler-cron

# Every 6 hours
RUN echo "0 */6 * * * cd /app && /usr/local/bin/python /app/main.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/crawler-cron

# Every Monday at 3 AM
RUN echo "0 3 * * 1 cd /app && /usr/local/bin/python /app/main.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/crawler-cron
```

Then rebuild the container:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Change Timezone

Edit `docker-compose.yml`:

```yaml
environment:
  - TZ=America/New_York  # Change to your timezone
```

## Support

For issues or questions:
1. Check the logs in `./logs/` directory
2. Verify all environment variables are set correctly
3. Ensure GCP credentials have proper permissions
4. Check Vertex AI Data Store configuration" 
