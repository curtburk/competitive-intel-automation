# Competitive Intelligence Monitor - Deployment Guide

## Overview

This system monitors competitor product pages (Dell, ASUS, NVIDIA) and alerts you to changes via email. It consists of:

1. **Backend API** (HuggingFace Spaces) - Handles scraping, change detection, email alerts
2. **Frontend Dashboard** (Lovable) - Visual interface for viewing intel and changes

---

## Step 1: Set Up Resend for Email Alerts

1. Go to https://resend.com and create a free account
2. Generate an API key from the dashboard
3. Note: Free tier allows 100 emails/day (more than enough)

**Save your API key** - you'll need it for Step 2.

---

## Step 2: Deploy Backend to HuggingFace Spaces

### 2.1 Create a New Space

1. Go to https://huggingface.co/new-space
2. Settings:
   - **Space name**: `competitive-intel-monitor` (or similar)
   - **License**: Choose any
   - **SDK**: Select "Docker"
   - **Hardware**: CPU basic (free tier is fine)
   - **Visibility**: Private (recommended for competitive intel)

### 2.2 Upload Files

Upload these files to your Space:
- `app.py`
- `requirements.txt`
- `Dockerfile`
- `README.md`

### 2.3 Configure Environment Variables

In your Space settings, add these secrets:

| Variable | Value |
|----------|-------|
| `RESEND_API_KEY` | Your Resend API key from Step 1 |
| `ALERT_EMAIL` | Your HP Outlook email address |

### 2.4 Verify Deployment

Once the Space builds (2-3 minutes), test:

```bash
# Health check
curl https://YOUR-USERNAME-competitive-intel-monitor.hf.space/

# List competitors
curl https://YOUR-USERNAME-competitive-intel-monitor.hf.space/api/competitors

# Trigger initial scan
curl -X POST https://YOUR-USERNAME-competitive-intel-monitor.hf.space/api/scan
```

---

## Step 3: Build Frontend in Lovable

### 3.1 Create New Project

1. Open Lovable
2. Describe what you want:

```
Build a competitive intelligence dashboard with:

1. Header with "HP ZGX Competitive Intelligence" title and HP Blue (#024AD8) accent

2. Three competitor cards in a row:
   - Dell Pro Max GB300
   - ASUS ExpertCenter Pro ET900N G3  
   - NVIDIA DGX Station
   Each card shows: last scanned time, last change detected, and a "View Details" button

3. A "Changes Feed" section below showing recent changes:
   - Each change shows: competitor name, change type, timestamp, summary
   - Changes sorted newest first
   - Visual indicator for change severity (green=minor, yellow=moderate, red=major)

4. A "Scan Now" button that triggers /api/scan on the backend

5. A "Battle Cards" tab that shows competitive positioning content

Backend API is at: [YOUR_HUGGINGFACE_SPACE_URL]
Use the endpoints:
- GET /api/competitors - list competitors
- GET /api/changes - get recent changes
- POST /api/scan - trigger scan
- GET /api/battlecards - get battle card content
```

### 3.2 Connect to Backend

In Lovable, set your backend URL as an environment variable or constant:

```javascript
const API_BASE = "https://YOUR-USERNAME-competitive-intel-monitor.hf.space";
```

---

## Step 4: Set Up Scheduled Scanning

HuggingFace Spaces don't have built-in cron, so use one of these options:

### Option A: GitHub Actions (Recommended)

Create `.github/workflows/scan.yml` in a GitHub repo:

```yaml
name: Daily Competitive Scan

on:
  schedule:
    - cron: '0 14 * * *'  # 2 PM UTC = 7 AM PT
  workflow_dispatch:  # Allow manual trigger

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger scan
        run: |
          curl -X POST https://YOUR-USERNAME-competitive-intel-monitor.hf.space/api/scan
```

### Option B: cron-job.org (Free)

1. Go to https://cron-job.org
2. Create account
3. Add job:
   - URL: `https://YOUR-USERNAME-competitive-intel-monitor.hf.space/api/scan`
   - Method: POST
   - Schedule: Daily at 7 AM PT

### Option C: Manual

Just click "Scan Now" in your dashboard when you want to check.

---

## Usage

### Daily Workflow

1. Receive email alert when competitor page changes
2. Open dashboard to see details
3. Review change diff to understand what changed
4. Update battle cards if needed

### Before Sales Calls

1. Open dashboard
2. Click "Scan Now" to get fresh data
3. Review any recent changes
4. Check battle cards for talk track

### Interview Talking Point

"I built a competitive intelligence system that monitors Dell, ASUS, and NVIDIA product pages daily. When something changes - pricing, specs, availability - I get an email alert. Instead of manually checking competitor sites every week, I get notified automatically. It's competitive intelligence as a service, not a static PDF."

---

## API Reference

### GET /api/competitors
Returns list of tracked competitors with scan status.

### GET /api/changes?limit=20
Returns recent changes across all competitors.

### GET /api/changes/{competitor_id}
Returns changes for specific competitor (dell, asus, nvidia).

### POST /api/scan
Triggers immediate scan. Body (optional):
```json
{"competitor_id": "dell"}  // Scan specific competitor
{}  // Scan all
```

### GET /api/battlecards
Returns competitive positioning content.

### GET /api/snapshots/{competitor_id}
Returns snapshot history for a competitor.

---

## Troubleshooting

**Scan returns errors**
- Some sites block automated access; the system handles this gracefully
- Check Space logs for details

**Email not arriving**
- Verify RESEND_API_KEY is set correctly in Space secrets
- Check Resend dashboard for delivery status
- Check spam folder

**Space not building**
- Check logs in HuggingFace Space
- Ensure Dockerfile and requirements.txt are present

---

## Files Included

| File | Purpose |
|------|---------|
| `app.py` | FastAPI backend application |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container configuration |
| `README.md` | HuggingFace Space documentation |

---

## Cost

- **HuggingFace Spaces**: Free (CPU basic)
- **Resend**: Free (100 emails/day)
- **Lovable**: Your existing subscription
- **GitHub Actions**: Free (2000 minutes/month)

Total: $0/month

---

Built for HP ZGX competitive positioning by Curtis Burkhalter.
