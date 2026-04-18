#!/usr/bin/env bash
# setup.sh — clone external OSINT tools required by docker compose
#
# Run this once after cloning coldreach:
#   ./scripts/setup.sh
#
# What it does:
#   - Clones theHarvester into ./theHarvester/
#   - Clones SpiderFoot into ./spiderfoot/
#   - Copies .env.example → .env (if .env doesn't exist yet)
#
# These directories are gitignored (they're external tools we build locally
# via Docker — we don't commit them to this repo).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Pinned versions (change these to update) ─────────────────────────────────
THEHARVESTER_REPO="https://github.com/laramies/theHarvester.git"
THEHARVESTER_REF="master"   # or pin to a tag: "v4.6.0"

SPIDERFOOT_REPO="https://github.com/smicallef/spiderfoot.git"
SPIDERFOOT_REF="v4.0.0"
# ─────────────────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[setup]${NC} $*"; }
warn()  { echo -e "${YELLOW}[setup]${NC} $*"; }

# ── theHarvester ──────────────────────────────────────────────────────────────
if [ -d "$ROOT/theHarvester/.git" ]; then
    warn "theHarvester already cloned — skipping (delete the folder to re-clone)"
else
    info "Cloning theHarvester @ $THEHARVESTER_REF ..."
    git clone --branch "$THEHARVESTER_REF" --depth 1 \
        "$THEHARVESTER_REPO" "$ROOT/theHarvester"
    info "theHarvester cloned ✓"
fi

# ── SpiderFoot ────────────────────────────────────────────────────────────────
if [ -d "$ROOT/spiderfoot/.git" ]; then
    warn "SpiderFoot already cloned — skipping (delete the folder to re-clone)"
else
    info "Cloning SpiderFoot @ $SPIDERFOOT_REF ..."
    git clone --branch "$SPIDERFOOT_REF" --depth 1 \
        "$SPIDERFOOT_REPO" "$ROOT/spiderfoot"
    info "SpiderFoot cloned ✓"
fi

# ── .env ──────────────────────────────────────────────────────────────────────
if [ ! -f "$ROOT/.env" ]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    info ".env created from .env.example — edit it to set your API keys"
else
    warn ".env already exists — not overwriting"
fi

echo ""
info "Setup complete. Next steps:"
echo "  1. docker compose build spiderfoot theharvester   # first time only"
echo "  2. docker compose up -d                           # start all services"
echo "  3. pip install -e .                               # install coldreach CLI"
echo "  4. coldreach find --domain acme.com --quick       # try it out"
echo ""
