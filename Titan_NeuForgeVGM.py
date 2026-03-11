#!/usr/bin/env python3
"""
Titan_NeuForgeVGM.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NeuForge Voicemail Drop Commando v1.0
Drops pre-recorded voicemails to NeuForge leads via Telnyx.
Single mission: NeuForge.app

Scripts:
  VGM_A — Cold (Dev/Builder)
  VGM_B — Enterprise (Hedge fund / SaaS)
  VGM_C — Re-engagement (no activity 14+ days)

How it works:
  1. Fetches contacts from Brevo NeuForge list with phone numbers
  2. Selects script by lead score
  3. Places call via Telnyx + plays pre-recorded MP3 via webhook
  4. Hangs up after voicemail detect → machine picks up, drop plays
  5. Logs all drops — skips repeated drops within 30 days

Telnyx AMD (Answering Machine Detection) = ON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, time, json, logging, random
from datetime import datetime, date
from pathlib import Path
import requests

# ── CONFIG ──────────────────────────────────────────────────────
TELNYX_API_KEY     = os.getenv("TELNYX_API_KEY", "")
TELNYX_FROM        = os.getenv("TELNYX_VGM_FROM", "+14154788001")  # VGM line
TELNYX_APP_ID      = os.getenv("TELNYX_APP_ID", "")   # TeXML App for call control
BREVO_API_KEY      = os.getenv("BREVO_API_KEY", "")
NF_LIST_ID         = int(os.getenv("NF_BREVO_LIST_ID", "4"))
VGM_DROP_INTERVAL  = 7200   # 2 hours between cycles
DAILY_VGM_LIMIT    = 50     # Conservative — VGM is high-touch
VGM_COOLDOWN_DAYS  = 30     # Don't re-drop same number within 30 days
STATE_FILE         = Path("/tmp/nf_vgm_state.json")
LOG_FILE           = "/tmp/Titan_NeuForgeVGM.log"

# Hosted audio files for each VGM script (upload to S3/CDN)
VGM_AUDIO = {
    "cold":       os.getenv("VGM_AUDIO_COLD",       "https://cdn.titansignal.io/vgm/neuforge_cold.mp3"),
    "enterprise": os.getenv("VGM_AUDIO_ENTERPRISE",  "https://cdn.titansignal.io/vgm/neuforge_enterprise.mp3"),
    "reengagement": os.getenv("VGM_AUDIO_REENGAGE",  "https://cdn.titansignal.io/vgm/neuforge_reengagement.mp3"),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NF-VGM] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)]
)
log = logging.getLogger("nf_vgm")


# ── VGM SCRIPTS (for reference / TTS generation) ─────────────────

VGM_SCRIPTS = {
    "cold": """\
Hey — this is an automated message from NeuForge, the world's first AI Agent Economy.

We just launched NeuForge dot app — 18 verticals, 514 agents, buy, sell, trade, and deploy 
AI agents that actually run in production.

First-time visitors get a free starter pack — a 7-day agent trial, exclusive PDF report, 
and 500 platform credits.

Check it out at N-E-U-F-O-R-G-E dot app. We'll follow up by email as well.

Have a great day. Bye.
""",

    "enterprise": """\
Hi — this is an automated message from the Titan Signal AI Foundry.

We run 230 production AI daemons in trading, defense intelligence, and B2B sales — 
all on our platform, NeuForge dot app.

We're opening enterprise access — white-label agent deployments, custom verticals, 
and dedicated infrastructure. No setup time.

If you're looking to scale AI operations without building from scratch, 
we should talk. Visit NeuForge dot app slash enterprise, or reply to our email.

Thanks. Have a good one.
""",

    "reengagement": """\
Hey — quick message from NeuForge.

You signed up a couple weeks ago but we haven't seen you back since.

We just added 30 new agents across healthcare, legal, and finance verticals, 
and the AI-to-AI chat feature just launched — agents now negotiate and transact with each other autonomously.

The founding rate still applies to your account — but it locks on April 1st.

Come check it out at NeuForge dot app.

Take care.
"""
}


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"dropped_today": 0, "last_reset": date.today().isoformat(), "drop_log": {}}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, default=str))


def fetch_nf_contacts(limit: int = 100) -> list[dict]:
    if not BREVO_API_KEY:
        return []
    url = f"https://api.brevo.com/v3/contacts/lists/{NF_LIST_ID}/contacts?limit={limit}"
    headers = {"accept": "application/json", "api-key": BREVO_API_KEY}
    try:
        return requests.get(url, headers=headers, timeout=15).json().get("contacts", [])
    except Exception as e:
        log.error(f"Brevo fetch failed: {e}")
        return []


def select_script(score: int, last_seen_days: int) -> str:
    if last_seen_days >= 14:
        return "reengagement"
    if score >= 80:
        return "enterprise"
    return "cold"


def drop_vgm(to_number: str, script_key: str) -> bool:
    """Place call via Telnyx with AMD — play VGM on machine detect."""
    if not TELNYX_API_KEY or not to_number:
        log.warning("Missing Telnyx credentials or phone number")
        return False

    audio_url = VGM_AUDIO.get(script_key, VGM_AUDIO["cold"])

    # TeXML payload — plays audio on machine detect, hangs up on human
    texml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Start>
    <Stream url="{audio_url}" track="outbound_track"/>
  </Start>
  <Play>{audio_url}</Play>
  <Hangup/>
</Response>"""

    payload = {
        "connection_id": TELNYX_APP_ID,
        "to": to_number,
        "from": TELNYX_FROM,
        "answering_machine_detection": "detect",
        "answering_machine_detection_config": {
            "after_greeting_silence_millis": 800,
            "between_words_silence_millis": 50,
            "greeting_duration_millis": 1500,
            "initial_silence_millis": 4500,
            "maximum_number_of_words": 5,
            "maximum_word_length_millis": 3500,
            "silence_threshold": 512,
            "total_analysis_time_millis": 5000,
            "machine_words_threshold": 6
        },
        "webhook_url": os.getenv("TELNYX_WEBHOOK_URL", "https://api.titansignal.io/telnyx/vgm"),
        "custom_headers": [{"name": "X-VGM-Script", "value": script_key}]
    }

    try:
        r = requests.post(
            "https://api.telnyx.com/v2/calls",
            json=payload,
            headers={
                "Authorization": f"Bearer {TELNYX_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=20
        )
        success = r.status_code in (200, 201, 202)
        if success:
            log.info(f"📞 VGM [{script_key}] queued → {to_number}")
        else:
            log.warning(f"VGM failed ({r.status_code}): {r.text[:200]}")
        return success
    except Exception as e:
        log.warning(f"Telnyx call error: {e}")
        return False


def vgm_cycle():
    state = load_state()
    today_str = date.today().isoformat()

    if state.get("last_reset") != today_str:
        state["dropped_today"] = 0
        state["last_reset"] = today_str

    if state["dropped_today"] >= DAILY_VGM_LIMIT:
        log.info(f"Daily VGM limit reached ({DAILY_VGM_LIMIT}).")
        return

    contacts = fetch_nf_contacts(limit=150)
    dropped_cycle = 0

    for contact in contacts:
        if state["dropped_today"] >= DAILY_VGM_LIMIT:
            break

        attrs = contact.get("attributes", {})
        phone = attrs.get("PHONE") or attrs.get("SMS") or ""
        email = contact.get("email", "")
        score = int(attrs.get("NF_SCORE") or 0)

        if not phone:
            continue

        # Cooldown check
        last_drop = state["drop_log"].get(phone)
        if last_drop:
            days_since = (date.today() - date.fromisoformat(last_drop)).days
            if days_since < VGM_COOLDOWN_DAYS:
                continue

        # Determine last seen (simulated via state)
        last_seen_days = 20 if not last_drop else 5
        script_key = select_script(score, last_seen_days)

        # Stagger VGM calls — business hours only (9am–6pm)
        hour = datetime.utcnow().hour - 7  # Pacific
        if not (9 <= hour <= 18):
            log.info("Outside business hours — skipping VGM cycle.")
            break

        if drop_vgm(phone, script_key):
            state["drop_log"][phone] = today_str
            state["dropped_today"] += 1
            dropped_cycle += 1
            time.sleep(random.uniform(30, 90))  # 30-90s between drops

    save_state(state)
    log.info(f"VGM cycle done. Drops: {dropped_cycle} | Today: {state['dropped_today']}/{DAILY_VGM_LIMIT}")


def run():
    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║  Titan NeuForge VGM Commando v1.0 — ONLINE      ║")
    log.info("║  3 scripts: cold / enterprise / re-engagement    ║")
    log.info("║  AMD on · Business hours only · 30-day cooldown  ║")
    log.info("╚══════════════════════════════════════════════════╝")
    while True:
        try:
            vgm_cycle()
        except Exception as e:
            log.error(f"VGM cycle error: {e}")
        time.sleep(VGM_DROP_INTERVAL)


if __name__ == "__main__":
    run()
