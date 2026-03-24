---
title: Competitive Intelligence Monitor
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Competitive Intelligence Monitor

Backend API for monitoring competitor product pages (Dell Pro Max GB300, ASUS ET900N G3, NVIDIA DGX Station) and detecting changes.

## Features

- **Page Monitoring**: Fetches and parses competitor product pages
- **Change Detection**: Computes diffs between snapshots to detect updates
- **Email Alerts**: Sends notifications via Resend when changes are detected
- **Battle Cards**: Serves competitive positioning content
- **REST API**: Full API for frontend integration

## Environment Variables

Set these in your HuggingFace Space settings:

| Variable | Description |
|----------|-------------|
| `RESEND_API_KEY` | Your Resend API key for email alerts |
| `ALERT_EMAIL` | Email address to receive alerts |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/competitors` | GET | List all tracked competitors |
| `/api/changes` | GET | Get recent changes |
| `/api/changes/{id}` | GET | Get changes for specific competitor |
| `/api/snapshots/{id}` | GET | Get snapshot history |
| `/api/scan` | POST | Trigger a scan |
| `/api/battlecards` | GET | Get battle card content |

## Usage

```bash
# Trigger a scan of all competitors
curl -X POST https://your-space.hf.space/api/scan

# Get recent changes
curl https://your-space.hf.space/api/changes
```

## Built for HP ZGX Competitive Positioning

This tool monitors:
- Dell Pro Max GB300
- ASUS ExpertCenter Pro ET900N G3
- NVIDIA DGX Station

Designed to support Sales enablement and competitive intelligence for the HP ZGX Fury launch.
