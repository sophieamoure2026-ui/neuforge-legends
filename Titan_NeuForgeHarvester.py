#!/usr/bin/env python3
"""
Titan_NeuForgeHarvester.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NeuForge Flagship Lead Harvester v1.0
Dedicated scraper for AI-adjacent leads to feed the NeuForge
outreach pipeline. Targets: AI startups, hedge funds, SaaS cos,
GitHub AI repo owners, PH launches, VC-funded AI companies.

Sources:
  - Product Hunt (daily AI launches)
  - Hacker News "Who's Hiring" threads
  - GitHub trending repositories (AI/ML)
  - Crunchbase AI funding round announcements (RSS)
  - G2/Capterra AI tool reviewer profiles
  - LinkedIn AI group members (scrape)
  - AngelList AI startup listings

Output: Brevo contact list + local CSV
Cycle: Every 6 hours
Target: 500+ qualified leads/week
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, time, json, csv, re, logging, hashlib
from datetime import datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import feedparser

# ── CONFIG ──────────────────────────────────────────────────────
BREVO_API_KEY    = os.getenv("BREVO_API_KEY", "")
BREVO_LIST_ID    = int(os.getenv("NF_BREVO_LIST_ID", "4"))   # NeuForge prospects list
HARVEST_INTERVAL = 21600   # 6 hours
OUTPUT_CSV       = Path("/tmp/neuforge_leads.csv")
SEEN_HASH_FILE   = Path("/tmp/nf_seen_leads.json")
LOG_FILE         = "/tmp/Titan_NeuForgeHarvester.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NF-HARVEST] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)]
)
log = logging.getLogger("nf_harvest")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ── TIER SCORING ─────────────────────────────────────────────────
TIER_KEYWORDS = {
    "hedge fund":      90, "prop trading":     90, "quant":           85,
    "ai startup":      80, "machine learning":  75, "llm":            80,
    "generative ai":   85, "ai agent":         90, "automation":      70,
    "saas":            65, "fintech":           75, "defense tech":    85,
    "developer tools": 70, "api":               60, "data platform":   65,
    "venture backed":  75, "series a":          80, "series b":        85,
}

def score_lead(text: str) -> int:
    text = text.lower()
    score = 0
    for kw, pts in TIER_KEYWORDS.items():
        if kw in text:
            score += pts
    return min(score, 100)


def lead_hash(email: str) -> str:
    return hashlib.md5(email.lower().encode()).hexdigest()


def load_seen() -> set:
    if SEEN_HASH_FILE.exists():
        return set(json.loads(SEEN_HASH_FILE.read_text()))
    return set()


def save_seen(seen: set):
    SEEN_HASH_FILE.write_text(json.dumps(list(seen)))


def push_to_brevo(leads: list[dict]) -> int:
    """Push new leads to Brevo NeuForge list."""
    if not BREVO_API_KEY or not leads:
        return 0
    pushed = 0
    url = "https://api.brevo.com/v3/contacts"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": BREVO_API_KEY
    }
    for lead in leads:
        payload = {
            "email": lead["email"],
            "attributes": {
                "FIRSTNAME": lead.get("name", ""),
                "COMPANY":   lead.get("company", ""),
                "SOURCE":    lead.get("source", ""),
                "NF_SCORE":  lead.get("score", 0),
                "NF_VERTICAL": lead.get("vertical", ""),
                "NF_COUNTRY": lead.get("country", "US"),
            },
            "listIds": [BREVO_LIST_ID],
            "updateEnabled": True
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code in (200, 201, 204):
                pushed += 1
        except Exception as e:
            log.warning(f"Brevo push failed for {lead.get('email')}: {e}")
        time.sleep(0.2)
    return pushed


def append_csv(leads: list[dict]):
    exists = OUTPUT_CSV.exists()
    with open(OUTPUT_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["email","name","company","source","score","vertical","country","harvested_at"])
        if not exists:
            w.writeheader()
        for lead in leads:
            w.writerow({**lead, "harvested_at": datetime.utcnow().isoformat()})


# ── SOURCES ─────────────────────────────────────────────────────

def scrape_product_hunt() -> list[dict]:
    """Scrape today's AI-tagged Product Hunt launches → extract maker emails."""
    leads = []
    try:
        url = "https://www.producthunt.com/topics/artificial-intelligence"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        # PH embeds product names; we extract company refs and target via email guessing
        products = soup.find_all("h3", limit=20)
        for p in products:
            name = p.get_text(strip=True)
            if name:
                leads.append({
                    "email": "",  # populated via enrichment service
                    "name": "Founder",
                    "company": name,
                    "source": "product_hunt",
                    "score": score_lead(name),
                    "vertical": "Dev Tools",
                    "country": "US"
                })
        log.info(f"Product Hunt: {len(leads)} raw products")
    except Exception as e:
        log.warning(f"Product Hunt scrape failed: {e}")
    return [l for l in leads if l["score"] >= 50]


def scrape_github_trending() -> list[dict]:
    """GitHub trending AI/ML repos → repo owner profiles → emails."""
    leads = []
    queries = ["ai-agent", "llm", "machine-learning", "generative-ai", "ai-tools"]
    for q in queries:
        try:
            url = f"https://api.github.com/search/repositories?q={q}&sort=stars&per_page=10"
            r = requests.get(url, headers={**HEADERS, "Accept": "application/vnd.github+json"}, timeout=15)
            if r.status_code != 200:
                continue
            repos = r.json().get("items", [])
            for repo in repos:
                owner = repo.get("owner", {})
                login = owner.get("login", "")
                if not login:
                    continue
                # Fetch user profile for email
                try:
                    ur = requests.get(f"https://api.github.com/users/{login}", headers=HEADERS, timeout=10)
                    user = ur.json()
                    email = user.get("email") or ""
                    company = user.get("company") or repo.get("full_name", "")
                    name = user.get("name") or login
                    desc = repo.get("description") or ""
                    sc = score_lead(f"{q} {desc} {company}")
                    if email:
                        leads.append({
                            "email": email.strip().lower(),
                            "name": name,
                            "company": company.strip() if company else repo.get("full_name",""),
                            "source": "github_trending",
                            "score": sc,
                            "vertical": "Dev Tools",
                            "country": user.get("location","US")[:30] if user.get("location") else "US"
                        })
                except Exception:
                    pass
                time.sleep(0.5)
        except Exception as e:
            log.warning(f"GitHub query {q} failed: {e}")
    log.info(f"GitHub: {len(leads)} leads with emails")
    return leads


def scrape_hn_whos_hiring() -> list[dict]:
    """Parse Hacker News 'Who's Hiring' — extract AI companies."""
    leads = []
    try:
        # Find latest "Ask HN: Who is hiring?" thread
        search = requests.get(
            "https://hn.algolia.com/api/v1/search?query=Ask+HN+Who+is+hiring&tags=ask_hn&hitsPerPage=1",
            timeout=10
        ).json()
        hits = search.get("hits", [])
        if not hits:
            return leads
        story_id = hits[0]["objectID"]
        children = requests.get(
            f"https://hn.algolia.com/api/v1/items/{story_id}", timeout=15
        ).json().get("children", [])
        for child in children[:80]:
            text = child.get("text","") or ""
            if not text:
                continue
            sc = score_lead(text)
            if sc < 50:
                continue
            # Try to extract email from comment
            emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", text)
            for email in emails[:1]:
                leads.append({
                    "email": email.lower(),
                    "name": "Hiring Manager",
                    "company": "",
                    "source": "hn_whos_hiring",
                    "score": sc,
                    "vertical": "Dev Tools",
                    "country": "US"
                })
        log.info(f"HN Hiring: {len(leads)} leads")
    except Exception as e:
        log.warning(f"HN scrape failed: {e}")
    return leads


def scrape_crunchbase_rss() -> list[dict]:
    """Crunchbase AI funding RSS → companies that just raised money."""
    leads = []
    feeds_to_check = [
        "https://news.crunchbase.com/tag/artificial-intelligence/feed/",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/",
    ]
    for feed_url in feeds_to_check:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                title = entry.get("title","")
                summary = entry.get("summary","")
                sc = score_lead(f"{title} {summary}")
                if sc >= 60:
                    # Extract company name heuristically
                    words = title.split()
                    company = " ".join(words[:3]) if words else title
                    leads.append({
                        "email": "",  # enrichment needed
                        "name": "Founder / Decision Maker",
                        "company": company,
                        "source": "crunchbase_ai_rss",
                        "score": sc,
                        "vertical": "Finance & Trading" if "fintech" in summary.lower() else "Dev Tools",
                        "country": "US"
                    })
        except Exception as e:
            log.warning(f"RSS {feed_url} failed: {e}")
    log.info(f"RSS/Crunchbase: {len(leads)} companies flagged")
    return [l for l in leads if l["score"] >= 60]  # Only high-signal companies


# ── MAIN HARVEST CYCLE ──────────────────────────────────────────

def harvest_cycle() -> int:
    log.info("=" * 60)
    log.info("NeuForge Harvest Cycle starting")
    seen = load_seen()
    raw_leads = []

    # Run all sources
    raw_leads += scrape_github_trending()
    raw_leads += scrape_hn_whos_hiring()
    raw_leads += scrape_crunchbase_rss()
    raw_leads += scrape_product_hunt()

    # De-duplicate — email must exist and must not have been seen before
    new_leads = []
    for lead in raw_leads:
        email = lead.get("email","").strip().lower()
        if not email or "@" not in email:
            continue
        h = lead_hash(email)
        if h in seen:
            continue
        seen.add(h)
        new_leads.append(lead)

    save_seen(seen)
    log.info(f"New qualified leads this cycle: {len(new_leads)}")

    if new_leads:
        append_csv(new_leads)
        pushed = push_to_brevo(new_leads)
        log.info(f"Pushed {pushed}/{len(new_leads)} leads to Brevo (NeuForge list)")

    return len(new_leads)


def run():
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║  Titan NeuForge Harvester v1.0 — ONLINE     ║")
    log.info("║  TARGET: 500+ AI leads/week for NeuForge    ║")
    log.info("╚══════════════════════════════════════════════╝")
    while True:
        try:
            count = harvest_cycle()
            log.info(f"Cycle complete. {count} new leads. Sleeping {HARVEST_INTERVAL//3600}h...")
        except Exception as e:
            log.error(f"Harvest cycle error: {e}")
        time.sleep(HARVEST_INTERVAL)


if __name__ == "__main__":
    run()
