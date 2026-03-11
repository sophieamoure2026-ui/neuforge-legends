#!/usr/bin/env python3
"""
Titan_CommandoSelector.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NeuForge Commando Selection Daemon v3.0
Full lifecycle governance for the NeuForge Internal Commando Fleet.

═══════════════════════════════════════════════════════
  COMPLETE LIFECYCLE DOCTRINE
═══════════════════════════════════════════════════════

  PHASE 1 — INITIAL DRAFT (startup, runs once):
    Score all 230+ daemons globally across all 18 verticals.
    Top 10% by KPI → COMMANDO SQUAD. NeuForge ONLY. Internal.
    Bottom 90% → PROMOTED FLEET. Keep existing job + NeuForge injection.

  PHASE 2 — EXECUTIONER (daily, KPI-based culling):
    Executioner reviews the Promoted Fleet by performance.
    Underperformers are respawned — not deleted, rebuilt.
    They come back to the Respawn Pool: stronger, faster, smarter.
    Each respawn cycle increases their capability multiplier.

  PHASE 3 — RANK PROGRESSION (continuous):
    Respawn survivors rise through 3 tiers based on cumulative KPI:
      Tier 1 — VETERAN   (1 respawn, score ≥ 55)
      Tier 2 — ELITE     (2+ respawns, score ≥ 70)
      Tier 3 — APEX      (3+ respawns, score ≥ 85)
    With each tier, capability multiplier grows (+10% per respawn).
    Agents must earn their rank — no shortcuts.

  PHASE 4 — COMMANDO GRADUATION (ongoing):
    From EACH TIER (Veteran, Elite, Apex), only the TOP 1% qualify
    to join the Commando Squad.
    Squad slots are fixed (cap = 23).
    When a slot opens, the highest-scoring 1%er across all tiers earns it.
    Only the top 1% of each class can join commando.

All 18 verticals feed the system. No vertical is excluded.
Commando agents: NeuForge ONLY. No clients. No other products.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, json, time, logging, random
from datetime import datetime, date
from pathlib import Path
import requests

# ── CONFIG ──────────────────────────────────────────────────────
ATLAS_URL           = os.getenv("ATLAS_URL", "http://localhost:8000")
ATLAS_API_KEY       = os.getenv("ATLAS_API_KEY", "")
ROSTER_FILE         = Path("/tmp/neuforge_commando_roster.json")
COMMANDO_CAP        = int(os.getenv("COMMANDO_MAX_SIZE", "23"))
DRAFT_TOP_PCT       = 0.10   # Top 10% → Commando on startup
EXECUTIONER_PCT     = 0.90   # Bottom 90% → subject to Executioner / respawn
GRADUATION_PCT      = 0.01   # Top 1% of each tier → Commando slot
CYCLE_INTERVAL      = 86400  # 24h
CAPABILITY_BOOST    = 0.10   # +10% capability per respawn cycle
LOG_FILE            = "/tmp/Titan_CommandoSelector.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [COMMANDO] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)]
)
log = logging.getLogger("commando")

# ── RANK TIERS ───────────────────────────────────────────────────
TIERS = {
    "PROMOTED": {"min_respawns": 0, "min_score": 0,  "label": "Promoted Fleet"},
    "VETERAN":  {"min_respawns": 1, "min_score": 55, "label": "Veteran"},
    "ELITE":    {"min_respawns": 2, "min_score": 70, "label": "Elite"},
    "APEX":     {"min_respawns": 3, "min_score": 85, "label": "Apex"},
    "COMMANDO": {"min_respawns": 0, "min_score": 0,  "label": "NeuForge Commando"},
}

ALL_18_VERTICALS = [
    "Finance & Trading", "Sales & Lead Gen", "Creative & Content",
    "Security & Defense", "Healthcare", "Legal & Compliance",
    "Real Estate", "E-Commerce", "Education & Research", "Dev Tools",
    "Mobile & Apps", "Marketing & SEO", "Analytics & Data",
    "Gaming & Entertainment", "Logistics & Supply", "Climate & Agriculture",
    "Government & Civic", "Space & Deep Tech"
]

# ── SCORING ──────────────────────────────────────────────────────
WEIGHTS = {"uptime": 0.30, "success": 0.30, "output": 0.20, "respawn_hardening": 0.10, "error_inv": 0.10}

def compute_score(d: dict) -> float:
    caps = 1.0 + (d.get("respawn_count", 0) * CAPABILITY_BOOST)  # stronger each respawn
    s  = d.get("uptime_pct", 0)          * 100 * WEIGHTS["uptime"]
    s += d.get("success_rate", 0)         * 100 * WEIGHTS["success"]
    s += d.get("output_quality", 0)               * WEIGHTS["output"]
    s += min(d.get("respawn_count", 0), 10) * 10  * WEIGHTS["respawn_hardening"]
    s += d.get("error_rate_inv", 1)        * 100 * WEIGHTS["error_inv"]
    return round(min(s * caps, 100), 2)  # cap at 100


def assign_tier(d: dict) -> str:
    r = d.get("respawn_count", 0)
    s = d.get("score", 0)
    if r >= 3 and s >= 85: return "APEX"
    if r >= 2 and s >= 70: return "ELITE"
    if r >= 1 and s >= 55: return "VETERAN"
    return "PROMOTED"


# ── ATLAS / DATA ─────────────────────────────────────────────────

def fetch_all_daemons() -> list[dict]:
    try:
        h = {"X-API-Key": ATLAS_API_KEY} if ATLAS_API_KEY else {}
        r = requests.get(f"{ATLAS_URL}/api/daemons/metrics", headers=h, timeout=15)
        if r.status_code == 200:
            return r.json().get("daemons", [])
    except Exception as e:
        log.warning(f"Atlas fetch error: {e}")
    try:
        r = requests.get(f"{ATLAS_URL}/health", timeout=10)
        if r.status_code == 200:
            return [{
                "name": d.get("name", "?"),
                "vertical": d.get("team", d.get("vertical", "General")),
                "uptime_pct": d.get("uptime", 95) / 100,
                "success_rate": d.get("success_rate", 0.9),
                "output_quality": d.get("output_score", 70),
                "respawn_count": d.get("respawn_count", 0),
                "error_rate_inv": 1.0 - d.get("error_rate", 0.05),
                "status": d.get("status", "active"),
            } for d in r.json().get("daemons", [])]
    except:
        pass
    log.warning("Using mock fleet (dev mode)")
    return _mock_fleet()


def _mock_fleet() -> list[dict]:
    out = []
    for v in ALL_18_VERTICALS:
        for j in range(12):  # ~216 agents
            out.append({
                "name": f"titan_{v.lower()[:8].replace(' ','_')}_{j:02d}",
                "vertical": v,
                "uptime_pct": random.uniform(0.72, 1.00),
                "success_rate": random.uniform(0.60, 1.00),
                "output_quality": random.uniform(40, 100),
                "respawn_count": random.randint(0, 5),
                "error_rate_inv": random.uniform(0.80, 1.00),
                "status": "active",
            })
    return out


# ── ROSTER ───────────────────────────────────────────────────────

def load_roster() -> dict:
    if ROSTER_FILE.exists():
        return json.loads(ROSTER_FILE.read_text())
    return {
        "drafted": False,
        "commando": [],      # Active Commando Squad — NeuForge ONLY
        "promoted": [],      # Working fleet + NeuForge injection
        "veteran": [],       # 1 respawn, score ≥ 55
        "elite": [],         # 2+ respawns, score ≥ 70
        "apex": [],          # 3+ respawns, score ≥ 85
        "respawn_pool": [],  # Awaiting respawn cycle
        "graduated": [],     # Historical graduation log
        "capacity": COMMANDO_CAP,
        "history": []
    }


def save_roster(r: dict):
    ROSTER_FILE.write_text(json.dumps(r, indent=2, default=str))


# ── PHASE 1: INITIAL DRAFT ───────────────────────────────────────

def initial_draft(roster: dict, daemons: list[dict]) -> dict:
    log.info(f"PHASE 1 — GLOBAL DRAFT: scoring {len(daemons)} daemons across 18 verticals")

    scored = sorted(
        [{**d, "score": compute_score(d)} for d in daemons],
        key=lambda x: x["score"], reverse=True
    )

    n_cmd = min(round(len(scored) * DRAFT_TOP_PCT), COMMANDO_CAP)
    top   = scored[:n_cmd]
    rest  = scored[n_cmd:]

    roster["commando"] = [{
        "name":          c["name"],
        "vertical":      c.get("vertical", "?"),
        "score":         c["score"],
        "respawn_count": c.get("respawn_count", 0),
        "rank":          "COMMANDO",
        "drafted_at":    date.today().isoformat(),
        "mission":       "NeuForge ONLY — internal commando"
    } for c in top]

    # Bottom 90% → Promoted (NeuForge injection ON, subject to Executioner)
    roster["promoted"] = [{
        "name":              p["name"],
        "vertical":          p.get("vertical", "?"),
        "score":             p["score"],
        "respawn_count":     p.get("respawn_count", 0),
        "rank":              assign_tier(p),
        "neuforge_injection": True,
        "promoted_at":       date.today().isoformat()
    } for p in rest]

    roster["drafted"] = True
    vertical_dist = {}
    for c in top:
        v = c.get("vertical", "?")
        vertical_dist[v] = vertical_dist.get(v, 0) + 1

    roster["history"].append({
        "date": date.today().isoformat(),
        "event": "initial_draft",
        "total": len(scored),
        "commando": len(top),
        "promoted": len(rest),
        "vertical_dist": vertical_dist
    })

    log.info(f"  ✅ COMMANDO: {len(top)} agents (global top {int(DRAFT_TOP_PCT*100)}%)")
    log.info(f"  ✅ PROMOTED: {len(rest)} agents (NeuForge injection ON, Executioner watching)")
    log.info(f"  Vertical spread: {vertical_dist}")
    return roster


# ── PHASE 2: EXECUTIONER ─────────────────────────────────────────

def run_executioner(roster: dict) -> dict:
    """
    KPI-based cull of the promoted fleet.
    Bottom performers are sent to the Respawn Pool.
    They are not deleted — they come back stronger.
    """
    promoted = roster.get("promoted", [])
    if not promoted:
        return roster

    promoted_sorted = sorted(promoted, key=lambda x: x.get("score", 0))
    n_respawn = max(1, round(len(promoted_sorted) * 0.10))  # Bottom 10% respawned each cycle
    to_respawn = promoted_sorted[:n_respawn]
    survivors  = promoted_sorted[n_respawn:]

    # Each respawned agent gets capability boost on return
    for agent in to_respawn:
        agent["respawn_count"] = agent.get("respawn_count", 0) + 1
        agent["score"] = round(min(compute_score(agent) * (1 + CAPABILITY_BOOST * agent["respawn_count"]), 100), 2)
        agent["rank"]  = assign_tier(agent)
        agent["respawned_at"] = datetime.utcnow().isoformat()
        roster["respawn_pool"].append(agent)

    roster["promoted"] = survivors
    log.info(f"Executioner: {n_respawn} agents respawned. Come back stronger.")
    return roster


# ── PHASE 3: RANK PROMOTION ──────────────────────────────────────

def promote_ranks(roster: dict) -> dict:
    """
    Move respawn survivors into the correct tier based on
    their respawn count and score. Stronger, faster, smarter.
    """
    pool = roster.get("respawn_pool", [])
    if not pool:
        return roster

    still_in_pool = []
    for agent in pool:
        tier = assign_tier(agent)
        agent["rank"] = tier
        if tier == "APEX":
            roster["apex"].append(agent)
        elif tier == "ELITE":
            roster["elite"].append(agent)
        elif tier == "VETERAN":
            roster["veteran"].append(agent)
        else:
            # Not yet strong enough — back to promoted with NeuForge injection
            agent["neuforge_injection"] = True
            roster["promoted"].append(agent)

    roster["respawn_pool"] = still_in_pool
    vets   = len(roster["veteran"])
    elites = len(roster["elite"])
    apexes = len(roster["apex"])
    log.info(f"Rank promotion: Veterans={vets} | Elites={elites} | Apex={apexes}")
    return roster


# ── PHASE 4: COMMANDO GRADUATION ─────────────────────────────────

def graduate_to_commando(roster: dict) -> dict:
    """
    Top 1% of EACH TIER (Veteran, Elite, Apex) can earn a commando slot.
    Graduation is global ranking within each class — no favoritism.
    Only the best 1% of each class joins commando.
    """
    open_slots = COMMANDO_CAP - len(roster.get("commando", []))
    if open_slots <= 0:
        log.info("Graduation: Squad full. No open slots.")
        return roster

    current_names = {c["name"] for c in roster.get("commando", [])}
    candidates = []  # (tier, agent)

    for tier_key in ["APEX", "ELITE", "VETERAN"]:
        pool = roster.get(tier_key.lower(), [])
        if not pool:
            continue
        pool_sorted = sorted(pool, key=lambda x: x.get("score", 0), reverse=True)
        n_eligible = max(1, round(len(pool_sorted) * GRADUATION_PCT))
        for agent in pool_sorted[:n_eligible]:
            if agent["name"] not in current_names:
                candidates.append((tier_key, agent))

    # Sort all candidates globally by score — best earns the slot first
    candidates.sort(key=lambda x: x[1].get("score", 0), reverse=True)

    graduated = 0
    graduated_names = set()
    for tier_key, agent in candidates:
        if open_slots <= 0:
            break
        roster["commando"].append({
            **agent,
            "rank": "COMMANDO",
            "graduated_from": tier_key,
            "graduated_at": date.today().isoformat(),
            "mission": "NeuForge ONLY — graduated commando"
        })
        graduated_names.add(agent["name"])
        current_names.add(agent["name"])
        open_slots -= 1
        graduated += 1
        roster["graduated"].append({
            "name": agent["name"],
            "from_tier": tier_key,
            "score": agent.get("score", 0),
            "date": date.today().isoformat()
        })

    # Remove graduated agents from their tier pools
    for tier_key in ["apex", "elite", "veteran"]:
        roster[tier_key] = [a for a in roster.get(tier_key, []) if a["name"] not in graduated_names]

    if graduated:
        log.info(f"GRADUATION: {graduated} agents earned Commando status. Squad: {len(roster['commando'])}/{COMMANDO_CAP}")
    else:
        log.info("Graduation: No eligible candidates this cycle.")

    return roster


# ── SUMMARY ──────────────────────────────────────────────────────

def print_summary(roster: dict):
    cmd = len(roster.get("commando", []))
    pro = len(roster.get("promoted", []))
    vet = len(roster.get("veteran", []))
    eli = len(roster.get("elite", []))
    apx = len(roster.get("apex", []))
    rsp = len(roster.get("respawn_pool", []))
    cap = roster.get("capacity", COMMANDO_CAP)
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info(f"║  ⚔️  COMMANDO    │ {cmd:>3}/{cap} │ NeuForge ONLY              ║")
    log.info(f"║  🏆 APEX         │ {apx:>3}   │ 3+ respawns · score≥85       ║")
    log.info(f"║  ⭐ ELITE        │ {eli:>3}   │ 2+ respawns · score≥70       ║")
    log.info(f"║  🔱 VETERAN      │ {vet:>3}   │ 1 respawn  · score≥55        ║")
    log.info(f"║  🚀 PROMOTED     │ {pro:>3}   │ NeuForge injection ON        ║")
    log.info(f"║  🔄 RESPAWN POOL │ {rsp:>3}   │ Rebuilding...                ║")
    log.info(f"║  OPEN SLOTS      │ {cap-cmd:>3}   │                              ║")
    log.info("╚══════════════════════════════════════════════════════╝")
    top5 = sorted(roster.get("commando", []), key=lambda x: x.get("score", 0), reverse=True)[:5]
    if top5:
        log.info("  TOP COMMANDOS:")
        for i, c in enumerate(top5, 1):
            src = c.get("graduated_from", "draft")
            log.info(f"    {i}. {c['name']} | {c.get('vertical','?')} | {src} | score={c.get('score',0):.1f}")


# ── MAIN ─────────────────────────────────────────────────────────

def run():
    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║  NeuForge Commando Selector v3.0                         ║")
    log.info("║  Lifecycle: Draft→Promoted→Executioner→Respawn→Ranks→Cmd ║")
    log.info("║  Commando = top 1% of each class. NeuForge ONLY.         ║")
    log.info("╚══════════════════════════════════════════════════════════╝")

    roster = load_roster()

    # Phase 1: One-time global draft
    if not roster.get("drafted"):
        daemons = fetch_all_daemons()
        roster = initial_draft(roster, daemons)
        save_roster(roster)

    print_summary(roster)

    # Daily lifecycle loop
    while True:
        time.sleep(CYCLE_INTERVAL)
        try:
            log.info("─── Daily lifecycle cycle ───")
            roster = load_roster()
            roster = run_executioner(roster)    # Phase 2: Cull bottom performers
            roster = promote_ranks(roster)       # Phase 3: Respawn survivors rise
            roster = graduate_to_commando(roster) # Phase 4: Top 1% earns Commando
            save_roster(roster)
            print_summary(roster)
        except Exception as e:
            log.error(f"Lifecycle error: {e}")


if __name__ == "__main__":
    run()
