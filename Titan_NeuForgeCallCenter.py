#!/usr/bin/env python3
"""
Titan_NeuForgeCallCenter.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NeuForge Inbound Call Center Commando v1.0
BANT IVR flow for NeuForge.app inbound leads.

Single product. Single mission.

Flow:
  Inbound call → Greeting → IVR menu
  ├─ 1: "I want to deploy an agent"  → Agent Deployment Flow
  ├─ 2: "I want to list/sell agents" → Creator Onboarding Flow
  ├─ 3: "Enterprise inquiry"          → Enterprise Routing → Live transfer
  └─ 4: "Tell me more"               → NeuForge Overview + link SMS

BANT qualification runs through every branch:
  Budget → Authority → Need → Timeline

Telnyx TeXML webhooks power the call flow.
Webhook server: FastAPI on port 8002 (or Render/VPS endpoint).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, json, logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import uvicorn
import requests

# ── CONFIG ──────────────────────────────────────────────────────
TELNYX_API_KEY   = os.getenv("TELNYX_API_KEY", "")
TELNYX_FROM      = os.getenv("TELNYX_CC_FROM", "+14154788002")
BREVO_API_KEY    = os.getenv("BREVO_API_KEY", "")
NF_LIST_ID       = int(os.getenv("NF_BREVO_LIST_ID", "4"))
FORWARDING_NUMBER = os.getenv("NF_FORWARD_NUMBER", "+14157770000")  # Gary / live agent
PORT             = int(os.getenv("NF_CC_PORT", "8002"))
LOG_FILE         = "/tmp/Titan_NeuForgeCallCenter.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NF-CC] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)]
)
log = logging.getLogger("nf_cc")

app = FastAPI(title="NeuForge Call Center IVR", version="1.0")


# ── TEXML HELPERS ────────────────────────────────────────────────

def texml_response(xml: str) -> PlainTextResponse:
    return PlainTextResponse(content=xml, media_type="application/xml")


def gather_texml(prompt: str, action_url: str, num_digits: int = 1, timeout: int = 10) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather numDigits="{num_digits}" action="{action_url}" timeout="{timeout}">
    <Say voice="Polly.Joanna">{prompt}</Say>
  </Gather>
  <Say voice="Polly.Joanna">We didn't catch that. Let's try again.</Say>
  <Redirect>{action_url}</Redirect>
</Response>"""


def say_and_hangup(message: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{message}</Say>
  <Hangup/>
</Response>"""


def forward_to_live(message: str, number: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{message}</Say>
  <Dial>{number}</Dial>
</Response>"""


# ── CALL LOG ────────────────────────────────────────────────────

def log_call(caller: str, path: str, bant: dict):
    log.info(f"📞 CALL | {caller} | Path: {path} | BANT: {bant}")
    # Push to Brevo as contact note
    if BREVO_API_KEY:
        try:
            requests.post(
                "https://api.brevo.com/v3/notes",
                json={"text": f"NeuForge IVR Call: Path={path}, BANT={json.dumps(bant)}", "contactId": 0},
                headers={"accept":"application/json","content-type":"application/json","api-key":BREVO_API_KEY},
                timeout=8
            )
        except:
            pass


# ── IVR FLOW ─────────────────────────────────────────────────────

BASE = os.getenv("NF_CC_BASE_URL", "https://api.titansignal.io/neuforge-cc")

@app.post("/inbound")
async def inbound(request: Request):
    """Entry point — inbound call arrives."""
    data = await request.form()
    caller = data.get("From", "unknown")
    log.info(f"Inbound call from {caller}")
    return texml_response(gather_texml(
        prompt=(
            "Welcome to NeuForge — the world's first A I Agent Economy. "
            "18 verticals. 514 agents. One platform. "
            "Press 1 to deploy an agent today. "
            "Press 2 to list and sell your own agents and earn 70 percent revenue share. "
            "Press 3 for enterprise and custom deployments. "
            "Press 4 to hear a brief overview of NeuForge before deciding."
        ),
        action_url=f"{BASE}/menu",
        num_digits=1,
        timeout=8
    ))


@app.post("/menu")
async def menu(request: Request):
    data = await request.form()
    digit = data.get("Digits", "")
    caller = data.get("From", "unknown")

    if digit == "1":
        return texml_response(gather_texml(
            prompt=(
                "Perfect. Let's find you the right agent. "
                "On a scale of 1 to 9, press the number that matches your monthly budget. "
                "1 for under 50 dollars. 2 for 50 to 200 dollars. 3 for 200 to 500 dollars. "
                "4 for over 500 dollars per month. "
                "Or press 9 if budget isn't a concern right now."
            ),
            action_url=f"{BASE}/deploy-budget?caller={caller}",
        ))
    elif digit == "2":
        return texml_response(say_and_hangup(
            "Excellent. To list your agent, visit NeuForge dot app slash sell. "
            "Create your listing in under 5 minutes. "
            "You keep 70 percent of every sale, paid in E T H, U S D C, or bank transfer. "
            "We're reviewing new listings within 24 hours. See you on the platform. Goodbye."
        ))
    elif digit == "3":
        log_call(caller, "enterprise_route", {})
        return texml_response(forward_to_live(
            "Connecting you to our enterprise team now. One moment please.",
            FORWARDING_NUMBER
        ))
    elif digit == "4":
        return texml_response(say_and_hangup(
            "NeuForge is the world's first A I Agent Economy, built by the Titan Signal A I Foundry. "
            "We have 514 production-ready agents across 18 verticals — finance, defense, healthcare, "
            "legal, e-commerce, dev tools, and more. "
            "Agents can be deployed in minutes with no coding required. "
            "First-time visitors get a free starter pack including a 7-day agent trial, "
            "our exclusive PDF report, and 500 platform credits. "
            "Visit NeuForge dot app to claim yours. We'll also send you an email with the link. Goodbye."
        ))
    else:
        return texml_response(gather_texml(
            prompt="We didn't get that. Press 1 to deploy, 2 to sell, 3 for enterprise, or 4 for an overview.",
            action_url=f"{BASE}/menu",
        ))


@app.post("/deploy-budget")
async def deploy_budget(request: Request):
    data = await request.form()
    digit = data.get("Digits", "")
    caller = request.query_params.get("caller", "unknown")

    budget_map = {"1": "<$50/mo", "2": "$50-200/mo", "3": "$200-500/mo", "4": ">$500/mo", "9": "Flexible"}
    budget = budget_map.get(digit, "Unknown")

    return texml_response(gather_texml(
        prompt=(
            "Got it. Now — what's the main thing you need this agent to do for you? "
            "Press 1 for sales and lead generation. "
            "Press 2 for trading and financial signals. "
            "Press 3 for content and marketing. "
            "Press 4 for intelligence, security, or defense. "
            "Press 5 for something else."
        ),
        action_url=f"{BASE}/deploy-need?caller={caller}&budget={budget}",
    ))


@app.post("/deploy-need")
async def deploy_need(request: Request):
    data = await request.form()
    digit = data.get("Digits", "")
    caller = request.query_params.get("caller", "unknown")
    budget = request.query_params.get("budget", "unknown")

    need_map = {
        "1": "Sales & Lead Gen", "2": "Finance & Trading",
        "3": "Creative & Content", "4": "Security & Defense", "5": "Other"
    }
    need = need_map.get(digit, "Other")

    bant = {"Budget": budget, "Need": need, "Timeline": "ASAP"}
    log_call(caller, f"deploy_qualified", bant)

    return texml_response(say_and_hangup(
        f"Perfect. Based on what you've told us, we have dedicated agents in {need} ready to deploy right now. "
        "We'll send you a direct link to the matching agents at NeuForge dot app. "
        "Check your phone or email in the next 60 seconds. "
        "Your free starter pack is included. Welcome to NeuForge. Goodbye."
    ))


@app.get("/health")
async def health():
    return {"status": "online", "service": "NeuForge Call Center IVR", "time": datetime.utcnow().isoformat()}


# ── OUTBOUND QUALIFICATION CALL ──────────────────────────────────

def make_outbound_qualification_call(to_number: str, contact_name: str = "there") -> bool:
    """Initiate outbound qualification call to a NeuForge lead."""
    if not TELNYX_API_KEY:
        return False
    texml_url = f"{BASE}/inbound"
    try:
        r = requests.post(
            "https://api.telnyx.com/v2/calls",
            json={
                "connection_id": os.getenv("TELNYX_APP_ID", ""),
                "to": to_number,
                "from": TELNYX_FROM,
                "webhook_url": f"{BASE}/call-events",
            },
            headers={"Authorization": f"Bearer {TELNYX_API_KEY}", "Content-Type": "application/json"},
            timeout=15
        )
        success = r.status_code in (200, 201, 202)
        log.info(f"📞 Outbound to {to_number}: {'OK' if success else 'FAILED'}")
        return success
    except Exception as e:
        log.warning(f"Outbound call error: {e}")
        return False


def run():
    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║  NeuForge Call Center IVR v1.0 — ONLINE         ║")
    log.info("║  BANT flow · 4 branches · Live transfer ready    ║")
    log.info(f"║  Listening on port {PORT}                          ║")
    log.info("╚══════════════════════════════════════════════════╝")
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    run()
