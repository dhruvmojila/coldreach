#!/usr/bin/env bash
# ColdReach — first-time setup wizard
#
# Usage:
#   ./scripts/setup.sh
#
# What it does:
#   1. Checks prerequisites (Docker, git, Python)
#   2. Clones theHarvester + SpiderFoot (if not already present)
#   3. Copies .env.example → .env (if .env doesn't exist)
#   4. Builds custom Docker images (SpiderFoot, theHarvester)
#   5. Starts all services and waits until healthy
#   6. Runs coldreach status to confirm everything is up
#
# Re-running is safe — already-done steps are skipped.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Pinned versions ───────────────────────────────────────────────────────────
THEHARVESTER_REPO="https://github.com/laramies/theHarvester.git"
THEHARVESTER_REF="master"

SPIDERFOOT_REPO="https://github.com/smicallef/spiderfoot.git"
SPIDERFOOT_REF="v4.0.0"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC}  $*"; }
info() { echo -e "  ${CYAN}→${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
die()  { echo -e "\n  ${RED}✗  ERROR:${NC} $*\n"; exit 1; }

header() {
  echo ""
  echo -e "  ${BOLD}${CYAN}$*${NC}"
  echo "  $(printf '─%.0s' $(seq 1 ${#1}))"
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Prerequisites
# ─────────────────────────────────────────────────────────────────────────────
header "Checking prerequisites"

# Docker
if ! command -v docker &>/dev/null; then
  die "Docker not found. Install from: https://docs.docker.com/get-docker/"
fi
DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
DOCKER_MAJOR=$(echo "$DOCKER_VERSION" | cut -d. -f1)
if [ "$DOCKER_MAJOR" -lt 24 ] 2>/dev/null; then
  warn "Docker $DOCKER_VERSION detected. Version 24+ recommended."
else
  ok "Docker $DOCKER_VERSION"
fi

# Docker Compose v2
if ! docker compose version &>/dev/null; then
  die "Docker Compose v2 not found. Update Docker Desktop or install the compose plugin:\n  https://docs.docker.com/compose/install/"
fi
COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "unknown")
ok "Docker Compose $COMPOSE_VERSION"

# Git
if ! command -v git &>/dev/null; then
  die "git not found. Install from: https://git-scm.com/"
fi
ok "git $(git --version | awk '{print $3}')"

# Python
PYTHON_CMD=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PY_VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
      PYTHON_CMD="$cmd"
      ok "Python $PY_VER"
      break
    fi
  fi
done
if [ -z "$PYTHON_CMD" ]; then
  die "Python 3.11+ not found. Install from: https://python.org/downloads/"
fi

# Disk space (need ~4GB for Docker images)
AVAIL_KB=$(df -k "$ROOT" | awk 'NR==2 {print $4}')
AVAIL_GB=$(echo "$AVAIL_KB / 1024 / 1024" | bc 2>/dev/null || echo "?")
if [ "$AVAIL_KB" -lt 4000000 ] 2>/dev/null; then
  warn "Low disk space (~${AVAIL_GB}GB free). Docker images need ~4GB."
else
  ok "Disk space (~${AVAIL_GB}GB free)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 2. Clone external OSINT tools
# ─────────────────────────────────────────────────────────────────────────────
header "Cloning OSINT tools"

if [ -d "$ROOT/theHarvester/.git" ]; then
  ok "theHarvester already present — skipping"
else
  info "Cloning theHarvester @ $THEHARVESTER_REF ..."
  git clone --branch "$THEHARVESTER_REF" --depth 1 \
      "$THEHARVESTER_REPO" "$ROOT/theHarvester" \
      2>&1 | grep -E "Cloning|done\." || true
  ok "theHarvester cloned"
fi

if [ -d "$ROOT/spiderfoot/.git" ]; then
  ok "SpiderFoot already present — skipping"
else
  info "Cloning SpiderFoot @ $SPIDERFOOT_REF ..."
  git clone --branch "$SPIDERFOOT_REF" --depth 1 \
      "$SPIDERFOOT_REPO" "$ROOT/spiderfoot" \
      2>&1 | grep -E "Cloning|done\." || true
  ok "SpiderFoot cloned"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. Environment file
# ─────────────────────────────────────────────────────────────────────────────
header "Environment"

if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  ok ".env created from .env.example"
  info "Optional: add your Groq API key to .env for AI-powered email generation"
else
  ok ".env already exists"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 4. Build Docker images
# ─────────────────────────────────────────────────────────────────────────────
header "Building Docker images"
info "Building spiderfoot and theharvester (takes 3–8 min on first run)..."
cd "$ROOT"
docker compose build spiderfoot theharvester 2>&1 | \
  grep -E "^\[|^Step|^Successfully|ERROR|error" || true
ok "Images built"

# ─────────────────────────────────────────────────────────────────────────────
# 5. Start services
# ─────────────────────────────────────────────────────────────────────────────
header "Starting services"
info "Starting all services..."
docker compose up -d

info "Waiting for all services to become healthy (up to 90s)..."
# docker compose up --wait uses health checks; fall back to sleep if not supported
if docker compose up --wait --timeout 90 2>/dev/null; then
  ok "All services healthy"
else
  warn "Some services may still be starting. Waiting 15s..."
  sleep 15
fi

# ─────────────────────────────────────────────────────────────────────────────
# 6. Verify
# ─────────────────────────────────────────────────────────────────────────────
header "Verification"

echo ""
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || \
  docker compose ps
echo ""

if command -v coldreach &>/dev/null; then
  info "Running coldreach status..."
  coldreach status
else
  warn "coldreach CLI not installed yet."
  info "Install it with:  pip install coldreach  or  uv sync"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}${GREEN}Setup complete!${NC}"
echo ""
echo "  Try it:"
echo ""
echo -e "    ${CYAN}coldreach find --domain stripe.com --quick${NC}"
echo -e "    ${CYAN}coldreach find --company \"Acme Corp\" --name \"Jane Smith\"${NC}"
echo ""
echo "  Useful commands:"
echo ""
echo -e "    ${CYAN}make status${NC}     check service health"
echo -e "    ${CYAN}make logs${NC}       follow service logs"
echo -e "    ${CYAN}make down${NC}       stop everything"
echo ""
