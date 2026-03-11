#!/usr/bin/env python3
"""
Titan_NeuForgeSMS.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NeuForge SMS Commando v1.0
6-touch SMS drip — single product, single mission: NeuForge.app.

These messages NEVER pitch anything else. No Apex Leads.
No OVERWATCH. No trading signals. NeuForge only.
That's the commando directive.

Touch schedule:
  T1: Day 0  — Free pack CTA, 2 min after capture
  T2: Day 1  — Social proof (47k operators)
  T3: Day 3  — Founding rate urgency ($9 → $29 on Apr 1)
  T4: Day 5  — Vertical match personalization
  T5: Day 7  — Trial expiry warning
  T6: Day 14 — Re-engagement (new agents in their vertical)

Provider: Telnyx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, time, json, logging, random
from datetime import datetime, date
from pathlib import Path
import requests

# ── CONFIG ──────────────────────────────────────────────────────
TELNYX_API_KEY   = os.getenv("TELNYX_API_KEY", "")
TELNYX_FROM      = os.getenv("TELNYX_SMS_FROM", "+14154788000")  # NeuForge number
BREVO_API_KEY    = os.getenv("BREVO_API_KEY", "")
NF_LIST_ID       = int(os.getenv("NF_BREVO_LIST_ID", "4"))
NEUFORGE_URL     = "https://neuforge.app"
CYCLE_INTERVAL   = 3600        # 1 hour
DAILY_SMS_LIMIT  = 300
STATE_FILE       = Path("/tmp/nf_sms_state.json")
LOG_FILE         = "/tmp/Titan_NeuForgeSMS.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NF-SMS] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)]
)
log = logging.getLogger("nf_sms")

# ── SMS SEQUENCE ─────────────────────────────────────────────────
# Rules: < 160 chars per segment where possible. Clear CTA. Always ends with opt-out path.

SMS_SEQUENCE = [
    {
        "touch": 1, "day_offset": 0,
        "msg": "🎁 Your NeuForge free pack is ready. 7-day agent trial + PDF report + 500 credits. Claim: {url} | Reply STOP to opt out"
    },
    {
        "touch": 2, "day_offset": 1,
        "msg": "47,000 operators just joined NeuForge.app — the #1 AI Agent Marketplace. Your free trial is still active: {url} | STOP to opt out"
    },
    {
        "touch": 3, "day_offset": 3,
        "msg": "🔒 NeuForge founding rate ($9/mo locked forever) expires Apr 1. After that: $29/mo. No exceptions. Lock in: {url} | STOP"
    },
    {
        "touch": 4, "day_offset": 5,
        "msg": "Quick q — what industry are you in? We have dedicated AI agents for {vertical}. Check them: {url} | STOP to opt out"
    },
    {
        "touch": 5, "day_offset": 7,
        "msg": "⚠️ Your NeuForge free trial ends TODAY. Keep access at $9/mo (founding rate, locks Apr 1): {url} | STOP"
    },
    {
        "touch": 6, "day_offset": 14,
        "msg": "New NeuForge agents just listed in your vertical. 514 total, 18 industries. Still free to browse: {url} | STOP"
    },
]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"sent_today": 0, "last_reset": date.today().isoformat(), "contact_touch": {}, "opted_out": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, default=str))


def fetch_nf_contacts(limit: int = 200) -> list[dict]:
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


def send_sms(to_number: str, message: str) -> bool:
    if not TELNYX_API_KEY or not to_number:
        return False
    try:
        r = requests.post(
            "https://api.telnyx.com/v2/messages",
            json={"from": TELNYX_FROM, "to": to_number, "text": message},
            headers={"Authorization": f"Bearer {TELNYX_API_KEY}", "Content-Type": "application/json"},
            timeout=15
        )
        return r.status_code in (200, 201, 202)
    except Exception as e:
        log.warning(f"SMS send failed to {to_number}: {e}")
        return False


def sms_cycle():
    state = load_state()
    today_str = date.today().isoformat()

    if state.get("last_reset") != today_str:
        state["sent_today"] = 0
        state["last_reset"] = today_str

    if state["sent_today"] >= DAILY_SMS_LIMIT:
        log.info(f"Daily SMS limit hit ({DAILY_SMS_LIMIT}). Sleeping.")
        return

    contacts = fetch_nf_contacts(limit=300)
    sent_cycle = 0
    opted_out = set(state.get("opted_out", []))

    for contact in contacts:
        if state["sent_today"] >= DAILY_SMS_LIMIT:
            break

        attrs = contact.get("attributes", {})
        phone = attrs.get("SMS") or attrs.get("PHONE") or ""
        email = contact.get("email", "")
        vertical = attrs.get("NF_VERTICAL") or "your industry"

        if not phone or phone in opted_out:
            continue

        ct = state["contact_touch"].get(email, {})
        touch_idx = ct.get("touch_idx", 0)
        last_sent_str = ct.get("last_sent")

        if touch_idx >= len(SMS_SEQUENCE):
            continue

        touch = SMS_SEQUENCE[touch_idx]
        required_day = touch["day_offset"]

        if last_sent_str and touch_idx > 0:
            last_date = date.fromisoformat(last_sent_str)
            if (date.today() - last_date).days < required_day:
                continue

        msg = touch["msg"].format(url=NEUFORGE_URL, vertical=vertical)
        if send_sms(phone, msg):
            state["contact_touch"][email] = {
                "touch_idx": touch_idx + 1,
                "last_sent": today_str
            }
            state["sent_today"] += 1
            sent_cycle += 1
            log.info(f"📱 [T{touch['touch']}] → {phone} | {email}")
            time.sleep(random.uniform(5, 12))

    save_state(state)
    log.info(f"SMS cycle done. Sent: {sent_cycle} | Today: {state['sent_today']}/{DAILY_SMS_LIMIT}")


def run():
    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║  Titan NeuForge SMS Commando v1.0 — ONLINE      ║")
    log.info("║  Mission: NeuForge.app only. 6-touch drip.       ║")
    log.info("╚══════════════════════════════════════════════════╝")
    while True:
        try:
            sms_cycle()
        except Exception as e:
            log.error(f"SMS cycle error: {e}")
        time.sleep(CYCLE_INTERVAL)


if __name__ == "__main__":
    run()
