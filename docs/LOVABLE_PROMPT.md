# Competitive Intelligence Dashboard - Lovable Prompt

Copy and paste this into Lovable to generate the frontend.

---

## PROMPT

Build a competitive intelligence dashboard for monitoring AI workstation competitors. This is an internal tool for HP product marketing.

### Design System

- **Primary color**: HP Blue #024AD8
- **Background**: White #FFFFFF
- **Text**: Dark gray #1F2937
- **Success/positive**: Green #10B981
- **Warning**: Yellow #F59E0B  
- **Error/alert**: Red #EF4444
- **Cards**: White with subtle shadow, rounded corners (8px)
- **Font**: System font stack (Inter if available)
- **Style**: Clean, professional, minimal — not flashy

### Backend API

Base URL: `https://curtburk-competitive-intel-monitor.hf.space`

Endpoints:
- `GET /api/competitors` — returns list of competitors with scan status
- `GET /api/changes` — returns recent changes (newest first)
- `GET /api/changes/{competitor_id}` — changes for specific competitor
- `GET /api/battlecards` — competitive positioning content
- `POST /api/scan` with body `{}` — triggers manual scan

### Page Structure

**Header**
- Title: "Competitive Intelligence" (left aligned)
- Subtitle: "HP ZGX vs. Dell, ASUS, NVIDIA" (smaller, gray)
- "Scan Now" button (right aligned, HP Blue, triggers POST /api/scan)
- Show loading spinner on button while scan is running
- Show toast notification when scan completes

**Competitor Cards Section**
Three cards in a row (responsive: stack on mobile):

Card 1: Dell Pro Max GB300
Card 2: ASUS ExpertCenter Pro ET900N G3
Card 3: NVIDIA DGX Station

Each card shows:
- Competitor name (bold)
- Competitor logo or icon placeholder
- "Last scanned: [timestamp]" 
- "Last change: [timestamp]" or "No changes detected" if null
- Small badge showing snapshot count
- "View Details" button that expands to show recent changes for that competitor

Data comes from GET /api/competitors

**Changes Feed Section**
Header: "Recent Changes" with a refresh icon button

List of change cards, newest first (from GET /api/changes):
- Left border color indicates competitor (Dell=blue, ASUS=teal, NVIDIA=green)
- Competitor name + change type as title
- Timestamp (relative: "2 hours ago", "Yesterday", etc.)
- Summary text
- Expandable section showing diff details if available
- Link icon to open competitor URL in new tab

Show "No changes detected yet" empty state if no changes

**Battle Cards Tab/Section**
Tab navigation or collapsible section with three battle cards (from GET /api/battlecards):

Display the `legal_notice` at the top of the section in a subtle gray banner.

Each battle card:
- Competitor name + HP product as header (e.g., "Dell Pro Max GB300 vs HP ZGX Fury")
- "Last updated: [date]" + `legal_review_status` badge
- **Executive Summary** — the `executive_summary` text
- **Shared Platform Note** — display `shared_platform_note` in an info callout (blue background) — this is important context
- **HP Advantages** — render each item from `hp_advantages` array:
  - Bold claim text
  - Detail text below
  - Source link (show "[NEEDS_VERIFICATION]" in yellow if source_url contains that string)
- **Competitor Limitations** — render each item from `competitor_limitations` array:
  - Bold claim text
  - Detail text below
  - Source link + verification_status badge (green if "Verified", yellow if "NEEDS_VERIFICATION")
- **Talk Track** — quoted text block with copy button
- **Verticals** — collapsible section showing `verticals.federal` and `verticals.healthcare` if present
- "Edit" button (disabled, placeholder for future)

At the bottom, show `positioning_guidance.legal_reminder` in a footer note.

### Interactions

1. Page load: Fetch /api/competitors and /api/changes simultaneously
2. "Scan Now" button: 
   - Disable button, show spinner
   - POST /api/scan with body {}
   - On success: show toast "Scan complete", refetch competitors and changes
   - On error: show error toast
3. Competitor card "View Details": Expand inline to show that competitor's changes
4. Changes feed: Auto-refresh every 5 minutes (optional, can skip)
5. Battle card "Copy" on talk track: Copy text to clipboard, show "Copied!" feedback

### Responsive Behavior

- Desktop: 3 competitor cards in row, changes feed below
- Tablet: 2 cards per row
- Mobile: Stack everything vertically, full-width cards

### Empty States

- No changes: "No changes detected yet. The system will alert you when competitor pages update."
- API error: "Unable to load data. Check your connection and try again." with retry button

### Technical Notes

- Use React with TypeScript
- Use Tailwind for styling
- Use React Query or SWR for data fetching (or simple useEffect + fetch)
- Use date-fns or similar for relative timestamps
- No authentication needed (API is public)

---

## FOLLOW-UP PROMPTS

After initial generation, you may need these refinements:

### If cards look too cramped:
"Add more padding to the competitor cards and increase spacing between sections"

### If colors are wrong:
"Change the primary button color to #024AD8 (HP Blue) and make sure it's used consistently"

### If API calls fail:
"Add error handling to all API calls with user-friendly error messages and retry buttons"

### To add the scan status indicator:
"Add a small green dot next to competitors that were scanned in the last 24 hours, yellow if 1-7 days, red if older"

### To add export functionality:
"Add an 'Export Report' button that downloads the current changes feed as a markdown file"

---

## API RESPONSE EXAMPLES

### GET /api/competitors
```json
{
  "competitors": [
    {
      "id": "dell",
      "name": "Dell Pro Max GB300",
      "url": "https://www.dell.com/...",
      "last_scanned": "20260324 160312",
      "last_change": "2026-03-24T16:03:12.123456+00:00",
      "snapshot_count": 3
    }
  ]
}
```

### GET /api/changes
```json
{
  "changes": [
    {
      "id": "dell_20260324160312",
      "competitor_id": "dell",
      "competitor_name": "Dell Pro Max GB300",
      "detected_at": "2026-03-24T16:03:12.123456+00:00",
      "change_type": "Page Content Changed",
      "summary": "5 text changes detected",
      "details": {
        "diff": ["Added: Now shipping", "Removed: Coming soon"]
      }
    }
  ]
}
```

### GET /api/battlecards
```json
{
  "legal_notice": "This content follows HP Legal Training Guide requirements...",
  "battlecards": [
    {
      "competitor_id": "dell",
      "competitor_name": "Dell Pro Max GB300",
      "hp_product": "HP ZGX Fury",
      "last_updated": "2026-03-24",
      "executive_summary": "Both Dell Pro Max GB300 and HP ZGX Fury utilize the NVIDIA GB300...",
      "shared_platform_note": "Both products share the same NVIDIA GB300 reference architecture...",
      "hp_advantages": [
        {
          "claim": "HP ZGX Toolkit VS Code extension available at no additional licensing cost",
          "detail": "Device discovery, SSH key authentication, and compute offload...",
          "source": "HP ZGX Onboard documentation",
          "source_url": "https://www.hp.com/us-en/workstations/zgx-onboard.html"
        }
      ],
      "competitor_limitations": [
        {
          "claim": "Dell Pro Max GB300 ships with NVIDIA DGX OS and NVIDIA AI software stack",
          "detail": "Production deployment may require NVIDIA AI Enterprise licensing.",
          "source": "Dell Pro Max GB300 product page",
          "source_url": "https://www.dell.com/...",
          "verification_status": "NEEDS_VERIFICATION"
        }
      ],
      "talk_track": "Dell and HP both offer the GB300 platform...",
      "verticals": {
        "federal": "Dell has not announced a hardware-level air-gap configuration...",
        "healthcare": "Both platforms support local PHI processing..."
      },
      "legal_review_status": "Pending review - ipmarketingreview@hp.com"
    }
  ],
  "positioning_guidance": {
    "priority_order": ["1. Support infrastructure", "2. Software licensing costs", "..."],
    "avoid": ["Leading with raw performance claims", "..."],
    "legal_reminder": "All claims require verification before distribution..."
  }
}
```
