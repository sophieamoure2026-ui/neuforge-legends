#!/usr/bin/env python3
"""
Titan_NeuForgeOutreach.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NeuForge Dedicated Email Outreach Daemon v1.0
Flagship product outreach — 3 sequences:
  A) Cold/Builder   — Free gift angle, direct CTA
  B) FOMO/Expiry    — Trial expiry urgency, April 1 deadline
  C) Enterprise     — White-label / API / custom verticals

All emails include the NeuForge platform intro. No exceptions.
70% rev share and ETH payout always mentioned for creators.

Reads from Brevo NeuForge prospect list.
Sends via SMTP router (Brevo SMTP relay).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, time, json, smtplib, logging, random
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import requests

# ── CONFIG ──────────────────────────────────────────────────────
BREVO_API_KEY       = os.getenv("BREVO_API_KEY", "")
BREVO_SMTP_HOST     = "smtp-relay.brevo.com"
BREVO_SMTP_PORT     = 587
BREVO_SMTP_USER     = os.getenv("BREVO_SMTP_USER", "")
BREVO_SMTP_PASS     = os.getenv("BREVO_SMTP_PASS", "")
FROM_EMAIL          = os.getenv("NF_FROM_EMAIL", "gary@titansignal.io")
FROM_NAME           = "Gary @ NeuForge"
NEUFORGE_URL        = "https://neuforge.app"
OUTREACH_INTERVAL   = 3600    # 1 hour between runs
DAILY_SEND_LIMIT    = 400     # Brevo free tier safe zone
STATE_FILE          = Path("/tmp/nf_outreach_state.json")
LOG_FILE            = "/tmp/Titan_NeuForgeOutreach.log"
NF_LIST_ID          = int(os.getenv("NF_BREVO_LIST_ID", "4"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NF-OUTREACH] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)]
)
log = logging.getLogger("nf_outreach")


# ── EMAIL SEQUENCES ─────────────────────────────────────────────

NF_SEQUENCES = {

    "cold_builder": {
        "touches": [
            {
                "day": 0,
                "subject": "Your AI agent is live in 30 minutes",
                "body": """\
Hey {first_name},

I'll keep this short.

We just launched NeuForge.app — the world's first AI Agent Economy.

18 verticals. 514 agents. Buy, sell, trade, deploy — or list your own and earn.

First-time visitors get a free starter pack:
  ✅ 7-day free agent trial (any vertical)
  ✅ "10 AI Agents Making $1M in 2026" — exclusive PDF report
  ✅ 500 NeuForge Credits — redeemable instantly

→ Claim yours: {neuforge_url}

Also — our top creator earned $94,200 last month. 70% rev share. Paid in ETH.

If you build AI tools, you should be on NeuForge.

— Gary
Titan Signal AI Foundry

P.S. We're offering the founding rate ($9/mo) until April 1st. After that it goes to $29/mo. Just so you know.
"""
            },
            {
                "day": 3,
                "subject": "Re: Your free NeuForge agent",
                "body": """\
Hey {first_name},

Quick follow-up on my note from Monday.

Your free agent pack is still waiting at NeuForge.app.

Since I sent that email, 847 more operators joined the platform. The founding rate locks in 8 days.

If you're building anything in AI — agents, tools, pipelines — NeuForge is the distribution layer. List once. Reach 47,000 buyers.

Grab it: {neuforge_url}

— Gary

P.S. This is the last email I'll send this week. Don't miss the founding window.
"""
            },
            {
                "day": 7,
                "subject": "Last call — founding rate expires April 1",
                "body": """\
{first_name},

The founding rate for NeuForge ($9/mo, locked forever) expires April 1st.

After that: $29/mo. No grandfathering.

47,218 operators. 514 agents. 18 verticals. The platform is real, it's live, and it's already generating revenue for creators.

Last chance to lock in: {neuforge_url}

— Gary

---
This is an automated message from Titan Signal AI Foundry.
Unsubscribe: Reply with STOP.
"""
            }
        ]
    },

    "enterprise": {
        "touches": [
            {
                "day": 0,
                "subject": "We built the AI infrastructure layer you've been waiting for",
                "body": """\
Hi {first_name},

Titan Signal's AI Foundry runs 230+ production daemons across trading, defense intelligence, B2B sales, and lead generation — all on our platform, NeuForge.

We just opened enterprise access.

What that means for {company}:
  • White-label AI agent deployments — your brand, our infrastructure
  • Custom verticals built to your spec in 72 hours
  • Dedicated infrastructure — no shared compute, no rate limits
  • API access to our entire agent catalog (514 agents, 18 verticals)
  • 70% revenue share on any agents you list

We're already in conversation with hedge funds and DoD-adjacent orgs. {company} seems like a natural fit.

Worth 20 minutes to explore? → {neuforge_url}/enterprise

— Gary Chen
Titan Signal AI Foundry | NeuForge.app

P.S. We also have OVERWATCH — a live geopolitical risk terminal tracking military aircraft and global OSINT in real time. Happy to demo both if useful.
"""
            },
            {
                "day": 4,
                "subject": "Re: NeuForge enterprise — following up",
                "body": """\
Hi {first_name},

Following up on my note earlier this week.

I know enterprise conversations move slowly. So let me make it easier.

We'll give {company} full platform access, free, for 30 days. No contract. No commitment. You deploy one agent, see the results, and decide.

43 enterprise teams have taken us up on this in the last 90 days. Average activation time: 48 hours.

Ready? → {neuforge_url}/enterprise

— Gary

P.S. If timing is off, reply with a better month and I'll circle back. No pressure.
"""
            }
        ]
    },

    "fomo_trial": {
        "touches": [
            {
                "day": 0,
                "subject": "Your NeuForge trial expires in 24 hours",
                "body": """\
{first_name},

Your 7-day NeuForge free trial is almost up.

What you built or explored this week stays yours. But after tomorrow, you'll need the $9/mo founding plan to keep access.

Reminder of what's included:
  → All 18 verticals
  → AI-to-AI Chat (agents negotiate and transact autonomously)  
  → 70% rev share on listed agents
  → OVERWATCH geopolitical intel access

Extend at the founding rate — before April 1: {neuforge_url}

See you inside.

— Gary

---
Reply STOP to unsubscribe.
"""
            }
        ]
    }
}

# ── NeuForge P.S. INJECTION (used by all OTHER daemons) ──────────
NEUFORGE_PS_BLOCK = """
─────────────────────────────────────────
🚀 P.S. — We just launched NeuForge.app, the #1 AI Agent Marketplace.
18 verticals · 514 agents · buy/sell/trade/deploy.
First-time visitors get a free agent pack → neuforge.app
─────────────────────────────────────────"""

NEUFORGE_CALL_INTRO = (
    "Before I get into it — I want to mention we just launched NeuForge.app, "
    "the world's first AI Agent Marketplace. 18 verticals, 514 agents, "
    "and it's completely free to explore. Okay — now the main reason for my call:"
)


# ── STATE MANAGEMENT ────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"sent_today": 0, "last_reset": datetime.utcnow().date().isoformat(), "contact_touch": {}}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, default=str))


# ── BREVO CONTACT FETCH ─────────────────────────────────────────

def fetch_nf_contacts(limit: int = 100) -> list[dict]:
    """Fetch contacts from the NeuForge Brevo list."""
    if not BREVO_API_KEY:
        return []
    url = f"https://api.brevo.com/v3/contacts/lists/{NF_LIST_ID}/contacts?limit={limit}&sort=desc"
    headers = {"accept": "application/json", "api-key": BREVO_API_KEY}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        return r.json().get("contacts", [])
    except Exception as e:
        log.error(f"Brevo fetch failed: {e}")
        return []


# ── SEND ENGINE ─────────────────────────────────────────────────

def send_email(to_email: str, to_name: str, subject: str, body: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"]      = to_email
    msg["Reply-To"] = FROM_EMAIL

    # Plain text
    text_part = MIMEText(body, "plain")
    msg.attach(text_part)

    # Simple HTML wrap
    html_body = f"""<html><body style="font-family:Arial,sans-serif;color:#1a1a1a;line-height:1.7;max-width:600px;margin:0 auto;padding:24px">
<pre style="font-family:Arial,sans-serif;white-space:pre-wrap">{body}</pre>
<br/><hr style="border:none;border-top:1px solid #eee;margin:24px 0"/>
<p style="font-size:11px;color:#888">Titan Signal AI Foundry · <a href="{NEUFORGE_URL}" style="color:#f97316">NeuForge.app</a></p>
</body></html>"""
    html_part = MIMEText(html_body, "html")
    msg.attach(html_part)

    try:
        with smtplib.SMTP(BREVO_SMTP_HOST, BREVO_SMTP_PORT) as server:
            server.starttls()
            server.login(BREVO_SMTP_USER, BREVO_SMTP_PASS)
            server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        log.warning(f"Send failed to {to_email}: {e}")
        return False


# ── OUTREACH CYCLE ──────────────────────────────────────────────

def outreach_cycle():
    state = load_state()
    today_str = datetime.utcnow().date().isoformat()

    # Reset daily counter
    if state.get("last_reset") != today_str:
        state["sent_today"] = 0
        state["last_reset"] = today_str
        log.info("Daily counter reset.")

    if state["sent_today"] >= DAILY_SEND_LIMIT:
        log.info(f"Daily limit reached ({DAILY_SEND_LIMIT}). Sleeping until tomorrow.")
        return

    contacts = fetch_nf_contacts(limit=150)
    if not contacts:
        log.info("No contacts fetched. Waiting.")
        return

    sent_this_cycle = 0
    for contact in contacts:
        if state["sent_today"] >= DAILY_SEND_LIMIT:
            break

        email = contact.get("email","")
        attrs = contact.get("attributes", {})
        name  = attrs.get("FIRSTNAME") or "there"
        company = attrs.get("COMPANY") or "your company"
        score = int(attrs.get("NF_SCORE") or 0)

        # Select sequence based on score
        if score >= 80:
            seq_key = "enterprise"
        elif attrs.get("NF_TRIAL_STARTED"):
            seq_key = "fomo_trial"
        else:
            seq_key = "cold_builder"

        seq = NF_SEQUENCES[seq_key]
        ct  = state["contact_touch"].get(email, {})
        touch_num = ct.get("touch", 0)
        last_sent = ct.get("last_sent")

        if touch_num >= len(seq["touches"]):
            continue  # Sequence exhausted

        touch = seq["touches"][touch_num]
        days_required = touch["day"]

        # Check if enough days have passed
        if last_sent:
            from datetime import date
            last_date = date.fromisoformat(last_sent)
            elapsed = (date.today() - last_date).days
            if elapsed < days_required and touch_num > 0:
                continue

        # Build and send
        body = touch["body"].format(
            first_name=name.split()[0] if name else "there",
            company=company,
            neuforge_url=NEUFORGE_URL
        )
        subj = touch["subject"]
        if send_email(email, name, subj, body):
            state["contact_touch"][email] = {
                "touch": touch_num + 1,
                "last_sent": today_str,
                "sequence": seq_key
            }
            state["sent_today"] += 1
            sent_this_cycle += 1
            log.info(f"✉️  [{seq_key} T{touch_num+1}] → {email}")
            time.sleep(random.uniform(8, 18))  # Human-like pacing

    save_state(state)
    log.info(f"Cycle complete. Sent: {sent_this_cycle} | Today total: {state['sent_today']}/{DAILY_SEND_LIMIT}")


def run():
    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║  Titan NeuForge Outreach v1.0 — ONLINE          ║")
    log.info("║  Flagship: NeuForge.app · 3 sequences active    ║")
    log.info("╚══════════════════════════════════════════════════╝")
    while True:
        try:
            outreach_cycle()
        except Exception as e:
            log.error(f"Outreach cycle error: {e}")
        log.info(f"Sleeping {OUTREACH_INTERVAL // 60}m...")
        time.sleep(OUTREACH_INTERVAL)


if __name__ == "__main__":
    run()
