# Competitive Intelligence Monitor

**What this is:** An automated system that watches competitor product pages (Dell, ASUS, NVIDIA) and emails you when something changes.

**Why it exists:** So you don't have to manually check competitor websites. The system does it daily and alerts you.

**Who built it:** Curtis Burkhalter, March 2026, for HP ZGX competitive positioning.

---

## How It Works (Simple Version)

```
Every weekday at 7 AM PT:
  1. GitHub Actions triggers a scan
  2. HuggingFace backend fetches competitor pages
  3. Backend compares to previous snapshot
  4. If something changed → sends you an email
  5. Stores the new snapshot for next comparison
```

That's it. You get an email when competitors update their pages. You do nothing unless you get an email.

---

## What's In This Repo

```
competitive-intel-automation/
├── .github/workflows/scan.yml    ← Runs daily, triggers the scan
├── huggingface/                  ← Backend code (runs on HuggingFace Spaces)
│   ├── app.py                    ← The actual application
│   ├── requirements.txt          ← Python dependencies
│   ├── Dockerfile                ← Container config
│   └── README.md                 ← HuggingFace Space description
├── docs/
│   ├── DEPLOYMENT_GUIDE.md       ← Step-by-step setup instructions
│   └── LOVABLE_PROMPT.md         ← Prompt to build the dashboard UI
└── README.md                     ← This file
```

---

## The Three Competitors Being Monitored

| Competitor | Product | URL |
|------------|---------|-----|
| Dell | Pro Max GB300 | https://www.dell.com/en-us/shop/desktop-computers/dell-pro-max-with-gb300/spd/dell-pro-max-fct6263-desktop |
| ASUS | ExpertCenter Pro ET900N G3 | https://www.asus.com/displays-desktops/workstations/performance/expertcenter-pro-et900n-g3/ |
| NVIDIA | DGX Station | https://www.nvidia.com/en-us/products/workstations/dgx-station/ |

All three compete with **HP ZGX Fury**.

---

## Where Things Are Running

| Component | Location | URL |
|-----------|----------|-----|
| Backend API | HuggingFace Spaces | https://curtburk-competitive-intel-monitor.hf.space |
| Daily scheduler | GitHub Actions | This repo → Actions tab |
| Email alerts | Resend | Configured via environment variables |
| Frontend (optional) | Lovable | Not yet built — use LOVABLE_PROMPT.md |

---

## How To Check If It's Working

### 1. Check if the backend is alive

```bash
curl https://curtburk-competitive-intel-monitor.hf.space/
```

**Expected response:**
```json
{"service":"Competitive Intelligence Monitor","status":"operational","competitors_tracked":3,"version":"1.0.0"}
```

If you get a 404 or HTML page → the Space is down or sleeping. Go to HuggingFace and restart it.

### 2. Check recent changes

```bash
curl https://curtburk-competitive-intel-monitor.hf.space/api/changes
```

This shows recent detected changes. If empty, no changes have been detected yet.

### 3. Manually trigger a scan

```bash
curl -X POST https://curtburk-competitive-intel-monitor.hf.space/api/scan \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected response:**
```json
{"results":[
  {"competitor_id":"dell","status":"success","change_detected":false,...},
  {"competitor_id":"asus","status":"success","change_detected":false,...},
  {"competitor_id":"nvidia","status":"success","change_detected":false,...}
]}
```

### 4. Check the GitHub Action ran

Go to this repo → Actions tab → "Daily Competitive Scan"

You should see green checkmarks for recent runs. If red, click to see the error.

---

## How To Fix Common Problems

### Problem: "I'm not getting emails"

1. **Check Resend:** Log into https://resend.com and check if emails are being sent
2. **Check HuggingFace secrets:** Go to your Space → Settings → Variables and secrets
   - `RESEND_API_KEY` must be set
   - `ALERT_EMAIL` must be set to your email
3. **Restart the Space** after changing secrets (changes don't apply until restart)
4. **Check spam folder**

### Problem: "The API returns 404"

The Space is either:
- **Sleeping:** HuggingFace free tier Spaces sleep after inactivity. Visit the Space URL in a browser to wake it up.
- **Failed to build:** Go to the Space page and check the logs

### Problem: "GitHub Action is failing"

1. Go to Actions tab → click the failed run → read the error
2. Most likely: the HuggingFace Space is sleeping. The Action will fail if it can't reach the API.
3. Fix: Wake up the Space, then re-run the Action

### Problem: "I need to change which competitors are monitored"

Edit `huggingface/app.py` → find the `COMPETITORS` dictionary near the top → add/remove/change URLs → redeploy to HuggingFace

### Problem: "I need to change the scan schedule"

Edit `.github/workflows/scan.yml` → change the cron line:

```yaml
schedule:
  - cron: '0 14 * * 1-5'  # Currently: 7 AM PT, Monday-Friday
```

Cron format: `minute hour day-of-month month day-of-week`
- `0 14 * * 1-5` = 14:00 UTC (7 AM PT), weekdays only
- `0 14 * * *` = 14:00 UTC, every day
- `0 13,21 * * 1-5` = 6 AM and 2 PM PT, weekdays

---

## How To Redeploy The Backend

If you need to update the backend code:

1. Make changes to files in `huggingface/` folder
2. Go to https://huggingface.co/spaces/curtburk/competitive-intel-monitor
3. Click "Files" tab
4. Upload the updated files (or delete and re-upload)
5. The Space will automatically rebuild and restart

---

## API Reference

### GET /
Health check. Returns service status.

### GET /api/competitors
Lists all tracked competitors with last scan time and change status.

### GET /api/changes
Returns recent detected changes, newest first.

### GET /api/changes/{competitor_id}
Returns changes for a specific competitor. Valid IDs: `dell`, `asus`, `nvidia`

### GET /api/snapshots/{competitor_id}
Returns stored page snapshots for a competitor.

### POST /api/scan
Triggers an immediate scan of all competitors.

**Body (optional):**
```json
{"competitor_id": "dell"}  // Scan only Dell
{}                          // Scan all
```

### GET /api/battlecards
Returns competitive positioning content following HP Legal Training Guide format.

---

## Credentials & Secrets

### HuggingFace Space Secrets

Set these in Space → Settings → Variables and secrets:

| Name | Value | Where to get it |
|------|-------|-----------------|
| `RESEND_API_KEY` | `re_xxxxxxxx` | https://resend.com → API Keys |
| `ALERT_EMAIL` | Your email | Your HP Outlook address |

### GitHub Secrets

None required. The scan workflow just hits a public URL.

---

## Cost

| Service | Cost |
|---------|------|
| HuggingFace Spaces (CPU basic) | Free |
| Resend (100 emails/day) | Free |
| GitHub Actions (2000 min/month) | Free |
| **Total** | **$0/month** |

---

## If You're Starting From Scratch

See `docs/DEPLOYMENT_GUIDE.md` for complete step-by-step setup instructions.

---

## If You Want To Build The Dashboard UI

See `docs/LOVABLE_PROMPT.md` for a detailed prompt to paste into Lovable.

---

## Interview Talking Point

> "I built a competitive intelligence system that monitors Dell, ASUS, and NVIDIA product pages daily. When pricing, specs, or availability changes, I get an email alert automatically. It runs on HuggingFace Spaces with GitHub Actions for scheduling — zero cost, fully automated. Instead of manually checking competitor sites every week, I get notified. That's competitive intelligence as a service, not a static PDF."

---

## Files Quick Reference

| I want to... | Edit this file |
|--------------|----------------|
| Change scan schedule | `.github/workflows/scan.yml` |
| Change which competitors are monitored | `huggingface/app.py` (COMPETITORS dict) |
| Change battle card content | `huggingface/app.py` (get_battlecards function) |
| Change email alert format | `huggingface/app.py` (send_alert_email function) |
| Build the dashboard | Use `docs/LOVABLE_PROMPT.md` |

---

## Contact

**Built by:** Curtis Burkhalter  
**Date:** March 2026  
**Purpose:** HP ZGX Fury competitive positioning  
**Questions:** You're the only one who knows this system exists, so ask yourself.
