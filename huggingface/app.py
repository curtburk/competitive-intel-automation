"""
Competitive Intelligence Monitor - Backend API
Monitors competitor product pages and detects changes.
Designed for HP ZGX Fury competitive positioning.
"""

import os
import json
import hashlib
import difflib
from datetime import datetime, timezone
from typing import Optional
import re

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import resend

# ============================================================================
# CONFIGURATION
# ============================================================================

COMPETITORS = {
    "dell": {
        "name": "Dell Pro Max GB300",
        "url": "https://www.dell.com/en-us/shop/desktop-computers/dell-pro-max-with-gb300/spd/dell-pro-max-fct6263-desktop",
        "selectors": {
            "price": ["span.ps-dell-price", "div.price-value", "span[data-testid='price']"],
            "specs": ["div.tech-specs", "div.ps-specs", "table.specs-table"],
            "title": ["h1", "h1.product-title"],
            "availability": ["div.availability", "span.stock-status", "div.delivery-message"]
        }
    },
    "asus": {
        "name": "ASUS ExpertCenter Pro ET900N G3",
        "url": "https://www.asus.com/displays-desktops/workstations/performance/expertcenter-pro-et900n-g3/",
        "selectors": {
            "price": ["span.price", "div.product-price"],
            "specs": ["div.spec-content", "div.ProductSpecFull", "section.TechSpec"],
            "title": ["h1", "h1.product-name"],
            "availability": ["div.availability", "span.stock"]
        }
    },
    "nvidia": {
        "name": "NVIDIA DGX Station",
        "url": "https://www.nvidia.com/en-us/products/workstations/dgx-station/",
        "selectors": {
            "price": ["span.price", "div.product-price"],
            "specs": ["div.specs", "section.specifications", "div.feature-list"],
            "title": ["h1", "h1.page-title"],
            "availability": ["div.availability", "a.buy-now"]
        }
    }
}

# MSI, Supermicro, and Gigabyte block automated requests (403 Forbidden).
# To monitor these, you would need:
# 1. A paid proxy service, OR
# 2. Playwright with a paid HuggingFace tier (more memory), OR  
# 3. Manual monitoring

# Storage paths (HuggingFace Spaces persistent storage)
DATA_DIR = os.environ.get("DATA_DIR", "./data")
SNAPSHOTS_DIR = os.path.join(DATA_DIR, "snapshots")
CHANGES_FILE = os.path.join(DATA_DIR, "changes.json")

# Email configuration
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")

# ============================================================================
# INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Competitive Intelligence Monitor",
    description="Monitors competitor product pages for HP ZGX competitive positioning",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
if not os.path.exists(CHANGES_FILE):
    with open(CHANGES_FILE, "w") as f:
        json.dump([], f)

# Initialize Resend if configured
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# ============================================================================
# MODELS
# ============================================================================

class ScanRequest(BaseModel):
    competitor_id: Optional[str] = None  # None = scan all

class ChangeRecord(BaseModel):
    id: str
    competitor_id: str
    competitor_name: str
    detected_at: str
    change_type: str
    summary: str
    details: dict
    previous_snapshot: Optional[str]
    current_snapshot: str

class CompetitorStatus(BaseModel):
    id: str
    name: str
    url: str
    last_scanned: Optional[str]
    last_change: Optional[str]
    snapshot_count: int

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_page_content(url: str, competitor_id: str = None) -> tuple[str, str]:
    """Fetch page content and return (html, text)."""
    # NOTE: Explicitly NOT requesting Brotli (br) encoding because requests 
    # doesn't decompress it automatically, leading to garbled binary output.
    # Only request gzip and deflate which requests handles natively.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",  # No 'br' - requests doesn't handle Brotli
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Chromium";v="134", "Not(A:Brand";v="24", "Google Chrome";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        # Force encoding detection if not set properly
        if response.encoding is None or response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding or 'utf-8'
        
        html = response.text
        
        # Check for binary/garbled content (common sign of encoding issues)
        # If more than 5% of characters are replacement characters, something is wrong
        replacement_ratio = html.count('\ufffd') / max(len(html), 1)
        if replacement_ratio > 0.05:
            # Try decoding as UTF-8 from raw bytes
            try:
                html = response.content.decode('utf-8', errors='ignore')
            except:
                pass
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Final sanity check: if text is mostly non-printable, flag it
        printable_ratio = sum(c.isprintable() or c.isspace() for c in text) / max(len(text), 1)
        if printable_ratio < 0.8:
            raise HTTPException(
                status_code=500, 
                detail=f"Page content appears garbled (only {printable_ratio:.0%} printable). Site may require JavaScript rendering."
            )
        
        return html, text
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch {url}: {str(e)}")


def extract_structured_data(html: str, selectors: dict) -> dict:
    """Extract structured data using CSS selectors."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    
    for field, selector_list in selectors.items():
        for selector in selector_list:
            try:
                element = soup.select_one(selector)
                if element:
                    data[field] = element.get_text(strip=True)
                    break
            except:
                continue
        if field not in data:
            data[field] = None
    
    return data


def compute_hash(content: str) -> str:
    """Compute MD5 hash of content."""
    return hashlib.md5(content.encode()).hexdigest()


def get_latest_snapshot(competitor_id: str) -> Optional[dict]:
    """Get the most recent snapshot for a competitor."""
    competitor_dir = os.path.join(SNAPSHOTS_DIR, competitor_id)
    if not os.path.exists(competitor_dir):
        return None
    
    snapshots = sorted(os.listdir(competitor_dir), reverse=True)
    if not snapshots:
        return None
    
    with open(os.path.join(competitor_dir, snapshots[0]), "r") as f:
        return json.load(f)


def save_snapshot(competitor_id: str, snapshot: dict) -> str:
    """Save a snapshot and return the filename."""
    competitor_dir = os.path.join(SNAPSHOTS_DIR, competitor_id)
    os.makedirs(competitor_dir, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.json"
    
    with open(os.path.join(competitor_dir, filename), "w") as f:
        json.dump(snapshot, f, indent=2)
    
    return filename


def compute_diff(old_text: str, new_text: str) -> list[str]:
    """Compute a human-readable diff between two texts."""
    old_lines = old_text.split("\n")
    new_lines = new_text.split("\n")
    
    differ = difflib.unified_diff(old_lines, new_lines, lineterm="", n=2)
    
    # Filter to only show meaningful changes
    changes = []
    for line in differ:
        if line.startswith("+") and not line.startswith("+++"):
            changes.append(f"Added: {line[1:].strip()}")
        elif line.startswith("-") and not line.startswith("---"):
            changes.append(f"Removed: {line[1:].strip()}")
    
    # Limit to most significant changes
    return changes[:20]


def record_change(change: dict):
    """Record a change to the changes log."""
    with open(CHANGES_FILE, "r") as f:
        changes = json.load(f)
    
    changes.insert(0, change)
    
    # Keep only last 100 changes
    changes = changes[:100]
    
    with open(CHANGES_FILE, "w") as f:
        json.dump(changes, f, indent=2)


def send_alert_email(change: dict):
    """Send email alert for detected change."""
    if not RESEND_API_KEY or not ALERT_EMAIL:
        print("Email not configured, skipping alert")
        return
    
    subject = f"[Competitive Intel] {change['competitor_name']} — {change['change_type']}"
    
    # Build email body
    body = f"""
Change detected: {change['detected_at']}

COMPETITOR: {change['competitor_name']}
URL: {COMPETITORS[change['competitor_id']]['url']}

CHANGE TYPE: {change['change_type']}

SUMMARY:
{change['summary']}

DETAILS:
"""
    
    if change.get('details', {}).get('diff'):
        for diff_line in change['details']['diff'][:10]:
            body += f"  • {diff_line}\n"
    
    body += f"""

---
View full history in the Competitive Intelligence Dashboard.
"""
    
    try:
        resend.Emails.send({
            "from": "Competitive Intel <alerts@resend.dev>",
            "to": [ALERT_EMAIL],
            "subject": subject,
            "text": body
        })
        print(f"Alert email sent to {ALERT_EMAIL}")
    except Exception as e:
        print(f"Failed to send email: {e}")


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """Health check and API info."""
    return {
        "service": "Competitive Intelligence Monitor",
        "status": "operational",
        "competitors_tracked": len(COMPETITORS),
        "version": "1.0.0"
    }


@app.get("/api/competitors")
def list_competitors():
    """List all tracked competitors with their status."""
    statuses = []
    
    for comp_id, comp_info in COMPETITORS.items():
        competitor_dir = os.path.join(SNAPSHOTS_DIR, comp_id)
        
        # Count snapshots
        snapshot_count = 0
        last_scanned = None
        if os.path.exists(competitor_dir):
            snapshots = sorted(os.listdir(competitor_dir), reverse=True)
            snapshot_count = len(snapshots)
            if snapshots:
                # Parse timestamp from filename
                last_scanned = snapshots[0].replace(".json", "").replace("_", " ")
        
        # Find last change for this competitor
        last_change = None
        with open(CHANGES_FILE, "r") as f:
            changes = json.load(f)
            for change in changes:
                if change.get("competitor_id") == comp_id:
                    last_change = change.get("detected_at")
                    break
        
        statuses.append({
            "id": comp_id,
            "name": comp_info["name"],
            "url": comp_info["url"],
            "last_scanned": last_scanned,
            "last_change": last_change,
            "snapshot_count": snapshot_count
        })
    
    return {"competitors": statuses}


@app.get("/api/changes")
def get_changes(limit: int = 20):
    """Get recent changes across all competitors."""
    with open(CHANGES_FILE, "r") as f:
        changes = json.load(f)
    
    return {"changes": changes[:limit]}


@app.get("/api/changes/{competitor_id}")
def get_competitor_changes(competitor_id: str, limit: int = 10):
    """Get changes for a specific competitor."""
    if competitor_id not in COMPETITORS:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    with open(CHANGES_FILE, "r") as f:
        all_changes = json.load(f)
    
    competitor_changes = [c for c in all_changes if c.get("competitor_id") == competitor_id]
    
    return {"changes": competitor_changes[:limit]}


@app.get("/api/snapshots/{competitor_id}")
def get_snapshots(competitor_id: str, limit: int = 10):
    """Get snapshot history for a competitor."""
    if competitor_id not in COMPETITORS:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    competitor_dir = os.path.join(SNAPSHOTS_DIR, competitor_id)
    if not os.path.exists(competitor_dir):
        return {"snapshots": []}
    
    snapshots = sorted(os.listdir(competitor_dir), reverse=True)[:limit]
    
    snapshot_list = []
    for filename in snapshots:
        with open(os.path.join(competitor_dir, filename), "r") as f:
            data = json.load(f)
            snapshot_list.append({
                "filename": filename,
                "timestamp": data.get("timestamp"),
                "content_hash": data.get("content_hash"),
                "structured_data": data.get("structured_data", {})
            })
    
    return {"snapshots": snapshot_list}


@app.post("/api/scan")
def trigger_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Trigger a scan of competitor pages."""
    if request.competitor_id and request.competitor_id not in COMPETITORS:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    competitors_to_scan = [request.competitor_id] if request.competitor_id else list(COMPETITORS.keys())
    
    results = []
    
    for comp_id in competitors_to_scan:
        comp_info = COMPETITORS[comp_id]
        
        try:
            # Fetch current page (uses Playwright for sites that require it)
            html, text = get_page_content(comp_info["url"], competitor_id=comp_id)
            content_hash = compute_hash(text)
            structured_data = extract_structured_data(html, comp_info["selectors"])
            
            # Get previous snapshot
            previous = get_latest_snapshot(comp_id)
            
            # Create new snapshot
            snapshot = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content_hash": content_hash,
                "text_content": text[:50000],  # Limit stored text
                "structured_data": structured_data
            }
            
            # Detect changes
            change_detected = False
            change_details = {}
            
            if previous:
                if previous.get("content_hash") != content_hash:
                    change_detected = True
                    
                    # Compute diff
                    diff = compute_diff(
                        previous.get("text_content", ""),
                        text[:50000]
                    )
                    
                    # Check structured data changes
                    struct_changes = {}
                    for field, new_value in structured_data.items():
                        old_value = previous.get("structured_data", {}).get(field)
                        if old_value != new_value and (old_value or new_value):
                            struct_changes[field] = {"old": old_value, "new": new_value}
                    
                    change_details = {
                        "diff": diff,
                        "structured_changes": struct_changes
                    }
            else:
                # First scan
                change_detected = True
                change_details = {"note": "Initial scan - baseline established"}
            
            # Save snapshot
            snapshot_file = save_snapshot(comp_id, snapshot)
            
            # Record change if detected
            if change_detected:
                # Determine change type
                if not previous:
                    change_type = "Initial Scan"
                    summary = "Baseline snapshot captured"
                elif change_details.get("structured_changes"):
                    fields_changed = list(change_details["structured_changes"].keys())
                    change_type = f"Content Update ({', '.join(fields_changed)})"
                    summary = "; ".join([
                        f"{k}: {v['old']} → {v['new']}" 
                        for k, v in change_details["structured_changes"].items()
                    ])
                else:
                    change_type = "Page Content Changed"
                    summary = f"{len(change_details.get('diff', []))} text changes detected"
                
                change_record = {
                    "id": f"{comp_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                    "competitor_id": comp_id,
                    "competitor_name": comp_info["name"],
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "change_type": change_type,
                    "summary": summary,
                    "details": change_details,
                    "previous_snapshot": previous.get("timestamp") if previous else None,
                    "current_snapshot": snapshot["timestamp"]
                }
                
                record_change(change_record)
                
                # Send email alert (in background for non-initial scans)
                if previous:
                    background_tasks.add_task(send_alert_email, change_record)
            
            results.append({
                "competitor_id": comp_id,
                "competitor_name": comp_info["name"],
                "status": "success",
                "change_detected": change_detected,
                "snapshot_file": snapshot_file,
                "change_type": change_details.get("note") or (change_type if change_detected else None)
            })
            
        except Exception as e:
            results.append({
                "competitor_id": comp_id,
                "competitor_name": comp_info["name"],
                "status": "error",
                "error": str(e)
            })
    
    return {"results": results}


@app.get("/api/battlecards")
def get_battlecards():
    """
    Battle card content following HP Legal Training Guide requirements.
    All claims require verification before external distribution.
    Legal review contact: ipmarketingreview@hp.com (5-10 business days)
    """
    return {
        "legal_notice": "This content follows HP Legal Training Guide requirements for comparative marketing materials. All assertions should include verifiable source links before distribution. Content pending Legal review.",
        "battlecards": [
            {
                "competitor_id": "dell",
                "competitor_name": "Dell Pro Max GB300",
                "hp_product": "HP ZGX Fury",
                "last_updated": "2026-03-24",
                "executive_summary": "Both Dell Pro Max GB300 and HP ZGX Fury utilize the NVIDIA GB300 Grace Blackwell Ultra Desktop Superchip. Differentiation focuses on software licensing, support infrastructure, and enterprise deployment tooling rather than underlying compute platform.",
                "shared_platform_note": "Both products share the same NVIDIA GB300 reference architecture. Focus positioning on implementation, support, and total cost of ownership.",
                "hp_advantages": [
                    {
                        "claim": "HP ZGX Toolkit VS Code extension available at no additional licensing cost",
                        "detail": "Device discovery, SSH key authentication, and compute offload from Windows, Mac, or Linux without enterprise licensing fees.",
                        "source": "HP ZGX Onboard documentation",
                        "source_url": "https://www.hp.com/us-en/workstations/zgx-onboard.html"
                    },
                    {
                        "claim": "Enterprise network compatible without mDNS or multicast traffic requirements",
                        "detail": "ZGX Toolkit uses standard SSH protocols. Does not require Apple Bonjour Print Services or .local address resolution.",
                        "source": "HP ZGX Toolkit documentation",
                        "source_url": "[NEEDS_VERIFICATION]"
                    },
                    {
                        "claim": "HP global enterprise support infrastructure",
                        "detail": "Standard HP enterprise support channels, spare parts availability, and warranty terms through established HP procurement.",
                        "source": "HP Support",
                        "source_url": "https://support.hp.com"
                    }
                ],
                "competitor_limitations": [
                    {
                        "claim": "Dell Pro Max GB300 ships with NVIDIA DGX OS and NVIDIA AI software stack",
                        "detail": "Production deployment may require NVIDIA AI Enterprise licensing. Verify current licensing requirements.",
                        "source": "Dell Pro Max GB300 product page",
                        "source_url": "https://www.dell.com/en-us/shop/desktop-computers/dell-pro-max-with-gb300/spd/dell-pro-max-fct6263-desktop",
                        "verification_status": "NEEDS_VERIFICATION - confirm current licensing terms"
                    },
                    {
                        "claim": "Dell announced shipping to 'select customers' first",
                        "detail": "Broader availability expected over coming months per Dell announcement.",
                        "source": "Dell press release (2026-03-16)",
                        "source_url": "https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~03~dell-technologies-first-to-ship-nvidia-gb300-desktop-for-autonomous-ai-agents-with-nvidia-openshell.htm",
                        "verification_status": "Verified"
                    }
                ],
                "talk_track": "Dell and HP both offer the GB300 platform — the underlying silicon is identical. The difference is in how you deploy and support it. Dell bundles the full NVIDIA stack, which may include enterprise licensing costs for production use. HP ZGX Fury gives you the same compute with a free toolkit, flexible software options, and HP's enterprise support infrastructure. For regulated industries, that flexibility matters.",
                "verticals": {
                    "federal": "Dell has not announced a hardware-level air-gap configuration. HP ZGX offers Federal variant with WiFi and Bluetooth physically desoldered. [VERIFY Dell Federal offerings before use]",
                    "healthcare": "Both platforms support local PHI processing. HP advantage is software flexibility — compliance teams can review the open-source ZGX Toolkit stack."
                },
                "legal_review_status": "Pending review - ipmarketingreview@hp.com"
            },
            {
                "competitor_id": "asus",
                "competitor_name": "ASUS ExpertCenter Pro ET900N G3",
                "hp_product": "HP ZGX Fury",
                "last_updated": "2026-03-24",
                "executive_summary": "Both ASUS ET900N G3 and HP ZGX Fury utilize the NVIDIA GB300 Grace Blackwell Ultra Desktop Superchip. ASUS positions as a hardware-first offering; HP differentiates on enterprise deployment readiness, vertical solutions, and support infrastructure.",
                "shared_platform_note": "Both products share the same NVIDIA GB300 reference architecture. Focus positioning on enterprise support, vertical solutions, and total cost of ownership.",
                "hp_advantages": [
                    {
                        "claim": "HP enterprise sales and support infrastructure",
                        "detail": "Established HP enterprise procurement channels, global support organization, and spare parts logistics.",
                        "source": "HP Corporate",
                        "source_url": "https://www.hp.com/us-en/shop/cv/workstations"
                    },
                    {
                        "claim": "HP vertical-specific configurations for Federal and Healthcare",
                        "detail": "Federal: Common Criteria EAL4+ certified BIOS, hardware-level wireless elimination option. Healthcare: compliance-friendly open-source stack.",
                        "source": "HP ZGX QuickSpecs",
                        "source_url": "https://h20195.www2.hp.com/v2/GetDocument.aspx?docname=c09212373"
                    },
                    {
                        "claim": "HP ZGX Toolkit with VS Code integration",
                        "detail": "Native development workflow from Windows, Mac, or Linux workstations without additional licensing.",
                        "source": "HP ZGX Onboard documentation",
                        "source_url": "https://www.hp.com/us-en/workstations/zgx-onboard.html"
                    }
                ],
                "competitor_limitations": [
                    {
                        "claim": "ASUS enterprise support model less established than HP for workstation deployments",
                        "detail": "ASUS primarily known for consumer and component markets. Enterprise workstation support infrastructure less mature than HP.",
                        "source": "General market positioning",
                        "source_url": "[NEEDS_VERIFICATION - requires specific support comparison data]",
                        "verification_status": "NEEDS_VERIFICATION"
                    },
                    {
                        "claim": "ASUS ET900N G3 availability listed as 'late Q1 2026'",
                        "detail": "Per ASUS CES 2026 announcement. Verify current shipping status.",
                        "source": "ASUS press release (2026-01-07)",
                        "source_url": "https://www.asus.com/us/business/resources/news/expertcenter-pro-et900n-g3-ces-2026/",
                        "verification_status": "Verified - confirm current availability"
                    }
                ],
                "talk_track": "ASUS builds excellent hardware — their ET900N G3 uses the same GB300 silicon as HP ZGX Fury. The question for enterprise buyers is support and deployment. ASUS is primarily a component and consumer brand. HP has decades of enterprise workstation deployment experience, established procurement relationships, and vertical solutions for Federal and Healthcare. If you're deploying multiple units in a regulated environment, those differences matter.",
                "verticals": {
                    "federal": "No ASUS Federal-specific configuration announced. HP offers hardware-level wireless elimination and Common Criteria EAL4+ certified BIOS.",
                    "healthcare": "Both platforms support local compute. HP advantage is established healthcare IT relationships and compliance-friendly open-source tooling."
                },
                "legal_review_status": "Pending review - ipmarketingreview@hp.com"
            },
            {
                "competitor_id": "nvidia",
                "competitor_name": "NVIDIA DGX Station",
                "hp_product": "HP ZGX Fury",
                "last_updated": "2026-03-24",
                "executive_summary": "NVIDIA DGX Station is the reference platform for the GB300 Grace Blackwell Ultra Desktop Superchip. HP ZGX Fury is built on the same architecture with HP value-add in tooling, support, and software flexibility. Both products offer identical core compute capabilities.",
                "shared_platform_note": "HP ZGX Fury is an OEM implementation of the NVIDIA DGX Station reference design. The underlying compute platform is identical. Differentiation is entirely in software, support, and deployment flexibility.",
                "hp_advantages": [
                    {
                        "claim": "HP ZGX Toolkit available at no additional licensing cost",
                        "detail": "VS Code extension for device discovery and compute offload. No NVIDIA AI Enterprise license required for ZGX Toolkit functionality.",
                        "source": "HP ZGX Onboard documentation",
                        "source_url": "https://www.hp.com/us-en/workstations/zgx-onboard.html"
                    },
                    {
                        "claim": "Software stack flexibility — NVIDIA AI Enterprise optional, not required",
                        "detail": "HP ZGX Fury supports open-source stack (PyTorch, vLLM, etc.) without mandatory enterprise licensing. NVAIE available as option for customers who want it.",
                        "source": "HP ZGX product positioning",
                        "source_url": "[NEEDS_VERIFICATION]"
                    },
                    {
                        "claim": "HP enterprise PC deployment expertise and global support",
                        "detail": "Standard HP workstation support, procurement, and spare parts infrastructure. Familiar processes for IT teams already deploying HP hardware.",
                        "source": "HP Support",
                        "source_url": "https://support.hp.com"
                    }
                ],
                "competitor_limitations": [
                    {
                        "claim": "NVIDIA DGX Station bundles NVIDIA DGX OS and AI software stack",
                        "detail": "Preconfigured with NVIDIA AI Enterprise software. Production use licensing terms apply.",
                        "source": "NVIDIA DGX Station product page",
                        "source_url": "https://www.nvidia.com/en-us/products/workstations/dgx-station/",
                        "verification_status": "Verified - confirm current licensing terms"
                    },
                    {
                        "claim": "NVIDIA Sync device discovery uses mDNS (.local addresses)",
                        "detail": "May not work in enterprise networks blocking multicast traffic. Requires Apple Bonjour Print Services for Windows users.",
                        "source": "[NEEDS_VERIFICATION - requires NVIDIA documentation link]",
                        "source_url": "[NEEDS_VERIFICATION]",
                        "verification_status": "NEEDS_VERIFICATION"
                    }
                ],
                "talk_track": "DGX Station is the benchmark — it's NVIDIA's reference design, and HP ZGX Fury is built on the exact same platform. The silicon is identical. The difference is in how you acquire and support it. Buying direct from NVIDIA means their full software stack and licensing model. HP ZGX Fury gives you the same compute with your choice of software stack, a free VS Code-based toolkit, and HP's enterprise support. For teams that want flexibility, that matters.",
                "verticals": {
                    "federal": "HP offers Federal-specific configuration with hardware-level wireless elimination. Verify NVIDIA Federal offerings before comparison.",
                    "healthcare": "Both platforms support local PHI processing. HP advantage is software flexibility for compliance review."
                },
                "legal_review_status": "Pending review - ipmarketingreview@hp.com"
            }
        ],
        "positioning_guidance": {
            "priority_order": [
                "1. Support infrastructure — HP global enterprise support vs. alternative support models",
                "2. Software licensing costs — ZGX Toolkit free vs. potential enterprise licensing fees",
                "3. Developer tooling — VS Code native extension vs. configuration complexity",
                "4. Enterprise network compatibility — standard SSH vs. mDNS requirements",
                "5. Security posture — hardware-level controls, Common Criteria EAL4+, physical wireless desoldering for Federal",
                "6. Procurement and supply chain — standard HP channels, spare parts availability"
            ],
            "avoid": [
                "Leading with raw performance claims (all GB300 products have identical compute)",
                "Attacking platform quality when sharing the same underlying chip",
                "Making absolute security claims — use 'with enhanced security features' framing",
                "Using forbidden superlatives: best, always, never, superior, optimal, guarantee, ensure"
            ],
            "legal_reminder": "All claims require verification before distribution. Legal review contact: ipmarketingreview@hp.com (5-10 business days). Substantiation files must be retained for 6 years per HP policy."
        }
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
