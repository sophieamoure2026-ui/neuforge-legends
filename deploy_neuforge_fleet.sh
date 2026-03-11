#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  deploy_neuforge_fleet.sh
#  NeuForge Commando Fleet — VPS-1 Deployment Script
#  Deploys 6 daemons: Harvester, Outreach, SMS, VGM, CallCenter, Selector
#  Target: 187.77.194.119 (VPS-1) — /opt/titan
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# ── CONFIG ──────────────────────────────────────────────────────────
VPS_HOST="${VPS_HOST:-root@187.77.194.119}"
VPS_DIR="/opt/titan"
LOCAL_SCRATCH="${HOME}/.gemini/antigravity/scratch"
SYSTEMD_DIR="/etc/systemd/system"

# Color helpers
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() {
  echo -e "\n${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${CYAN}${BOLD}║  🚀  NEUFORGE COMMANDO FLEET — DEPLOYMENT                    ║${RESET}"
  echo -e "${CYAN}${BOLD}║  VPS-1: 187.77.194.119 | 6 Daemons + Selector               ║${RESET}"
  echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}\n"
}

ok()   { echo -e "  ${GREEN}✅  $1${RESET}"; }
warn() { echo -e "  ${YELLOW}⚠️   $1${RESET}"; }
step() { echo -e "\n${BOLD}── $1${RESET}"; }

# ── DAEMON FILES TO DEPLOY ──────────────────────────────────────────
DAEMON_FILES=(
  "Titan_NeuForgeHarvester.py"
  "Titan_NeuForgeOutreach.py"
  "Titan_NeuForgeSMS.py"
  "Titan_NeuForgeVGM.py"
  "Titan_NeuForgeCallCenter.py"
  "Titan_CommandoSelector.py"
  "neuforge_injection.py"
)

SERVICES=(
  "titan-nf-harvester"
  "titan-nf-outreach"
  "titan-nf-sms"
  "titan-nf-vgm"
  "titan-nf-callcenter"
  "titan-commando-selector"
)

SERVICE_FILES=(
  "systemd/titan-nf-harvester.service"
  "systemd/titan-nf-outreach.service"
  "systemd/titan-nf-sms.service"
  "systemd/titan-nf-vgm.service"
  "systemd/titan-nf-callcenter.service"
  "systemd/titan-commando-selector.service"
)

# ═══════════════════════════════════════════════════════════════════
banner

# ── STEP 1: SCP daemon python files ─────────────────────────────────
step "STEP 1 — Uploading daemon Python files → VPS-1:${VPS_DIR}"
ssh "${VPS_HOST}" "mkdir -p ${VPS_DIR}"
for f in "${DAEMON_FILES[@]}"; do
  LOCAL_PATH="${LOCAL_SCRATCH}/${f}"
  if [ -f "${LOCAL_PATH}" ]; then
    scp "${LOCAL_PATH}" "${VPS_HOST}:${VPS_DIR}/${f}"
    ok "Uploaded: ${f}"
  else
    warn "NOT FOUND locally — skipping: ${f}"
  fi
done

# ── STEP 2: SCP systemd service files ───────────────────────────────
step "STEP 2 — Installing systemd service files"
for i in "${!SERVICES[@]}"; do
  SVC="${SERVICES[$i]}"
  LOCAL_SVC="neuforge-legends/${SERVICE_FILES[$i]}"
  REMOTE_SVC="${SYSTEMD_DIR}/${SVC}.service"
  if [ -f "${LOCAL_SVC}" ]; then
    scp "${LOCAL_SVC}" "${VPS_HOST}:${REMOTE_SVC}"
    ok "Installed: ${SVC}.service"
  else
    warn "Service file NOT FOUND: ${LOCAL_SVC}"
  fi
done

# ── STEP 3: systemctl daemon-reload ─────────────────────────────────
step "STEP 3 — Reloading systemd daemon on VPS-1"
ssh "${VPS_HOST}" "systemctl daemon-reload"
ok "systemd daemon reloaded"

# ── STEP 4: Enable + Start all services ─────────────────────────────
step "STEP 4 — Enabling and starting NeuForge fleet"
for SVC in "${SERVICES[@]}"; do
  ssh "${VPS_HOST}" "systemctl enable ${SVC} && systemctl restart ${SVC}"
  STATUS=$(ssh "${VPS_HOST}" "systemctl is-active ${SVC}" 2>/dev/null || echo "failed")
  if [ "${STATUS}" = "active" ]; then
    ok "${SVC}: ACTIVE ✔"
  else
    warn "${SVC}: status=${STATUS} — check logs: journalctl -u ${SVC} -n 50"
  fi
done

# ── STEP 5: Final health check ───────────────────────────────────────
step "STEP 5 — Fleet Health Summary"
echo ""
echo -e "${BOLD}  Service                      Status${RESET}"
echo -e "  ──────────────────────────────────────────────"
for SVC in "${SERVICES[@]}"; do
  STATUS=$(ssh "${VPS_HOST}" "systemctl is-active ${SVC}" 2>/dev/null || echo "failed")
  if [ "${STATUS}" = "active" ]; then
    echo -e "  ${GREEN}● ${SVC}: active${RESET}"
  else
    echo -e "  ${RED}✗ ${SVC}: ${STATUS}${RESET}"
  fi
done

echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║  NeuForge Commando Fleet DEPLOYMENT COMPLETE                ║${RESET}"
echo -e "${CYAN}${BOLD}║  Monitor: journalctl -fu titan-nf-harvester                ║${RESET}"
echo -e "${CYAN}${BOLD}║  Atlas:   http://187.77.194.119:8000/health                ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
