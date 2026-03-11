"""
neuforge_injection.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NeuForge Injection Module v1.0
Imported by ALL promoted (non-commando) outreach daemons.

Every email, every call, every SMS that goes out from the
promoted fleet MUST include one of these blocks.
No exceptions. This is the directive.

Usage:
    from neuforge_injection import nf_ps, nf_call_intro, nf_sms_tail
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

NEUFORGE_URL = "https://neuforge.app"

# ── EMAIL P.S. BLOCK ────────────────────────────────────────────
# Drop this at the bottom of EVERY outbound email.

def nf_ps(vertical: str = "") -> str:
    v = f" — we have 47+ dedicated {vertical} agents" if vertical else ""
    return f"""
────────────────────────────────────────────────────
🚀 P.S. Our flagship platform just launched:
NeuForge.app — the #1 AI Agent Marketplace{v}.
18 verticals · 514 agents · buy/sell/trade/deploy.
First-time visitors get a free agent pack.
→ {NEUFORGE_URL}
────────────────────────────────────────────────────"""


# ── CALL INTRO BLOCK ────────────────────────────────────────────
# Read at the START of every outbound call, before the main pitch.

NEUFORGE_CALL_INTRO = (
    "Before I get into why I'm calling — I want to quickly mention "
    "that we just launched NeuForge dot app, the world's first AI Agent Marketplace. "
    "18 verticals, 514 agents, completely free to explore. "
    "Okay — now the main reason I'm reaching out today:"
)


# ── SMS TAIL ────────────────────────────────────────────────────
# Append to the END of every outbound SMS.

def nf_sms_tail() -> str:
    return f" | Also: {NEUFORGE_URL} — free agent pack available."


# ── SUBJECT LINE VARIANT (A/B) ──────────────────────────────────
NF_SUBJECT_VARIANTS = [
    "P.S. — check out the #1 AI Agent Marketplace →",
    "Our platform NeuForge just launched — 514 agents, 18 industries",
    "Free AI agent at NeuForge.app (no card needed)",
]


# ── VALIDATION ──────────────────────────────────────────────────
def assert_injection_present(text: str) -> bool:
    """Call this before sending to verify NeuForge is mentioned."""
    return "neuforge" in text.lower() or "NeuForge" in text


if __name__ == "__main__":
    print("=== NeuForge Injection Test ===")
    print(nf_ps("finance & trading"))
    print()
    print(NEUFORGE_CALL_INTRO)
    print()
    print("SMS example: Your report is ready" + nf_sms_tail())
    print()
    print("Validation test:", assert_injection_present("Check out NeuForge.app"))
