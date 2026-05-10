# Screenshot & GIF Capture Guide

Drop files into THIS folder (`docs/images/`) with the exact names below.
They are already referenced in README.md and docs pages — no editing needed.

---

## Terminal setup before recording

```bash
# Set terminal to exactly this size before every capture
# 140 columns × 40 rows — wide enough to show both panels cleanly
resize -s 40 140          # Linux
# or drag terminal manually to ~140×40
```

Use a dark terminal theme (any dark background). Font: monospace, 14–16px.

---

## File 1: `demo.gif` — **Most important. Goes at top of README.**

**Purpose:** The hero GIF. This is what people see on GitHub and share on Twitter.
It needs to show the core magic: live streaming emails.

**Steps to record:**
1. Open a fresh terminal at 140×40
2. Run `coldreach`
3. Wait 1 second for the TUI to load fully (all 5 tabs visible)
4. Click into the domain input (or it's already focused)
5. Type `stripe.com` slowly (so it's readable in the GIF)
6. Press Enter to start scan
7. Watch and record for ~15 seconds as:
   - Sources light up one by one (web_crawler → whois → github → searxng…)
   - Emails appear row by row in the results table
   - Progress bar fills
   - "Done — X emails found" appears at bottom
8. Stop recording

**Duration:** 20–25 seconds total
**Loop:** Yes, infinite loop
**Filename:** `demo.gif`

---

## File 2: `draft.gif` — **Second most important. Shows the unique feature.**

**Purpose:** Shows the find → draft → copy workflow. This is the product differentiator.

**Steps to record:**
1. Do a scan first (can continue from demo.gif recording, or start fresh)
2. Let the scan run until at least 5–10 emails appear
3. Use arrow keys to navigate to an email row (highlight it)
4. Press `d` — draft panel slides in below
5. Pause 1 second (let company info load at the top of the panel)
6. In "Your name" field: type your name
7. Tab to "What you want" field: type `explore a partnership on payments`
8. Press Enter or click Generate
9. Wait for 3 subject lines to appear
10. Press `2` to select the second subject (shows the feature works)
11. Press `y` — "Draft copied to clipboard" notification appears
12. Stop recording

**Duration:** 25–30 seconds
**Loop:** Yes
**Filename:** `draft.gif`

---

## File 3: `verify.png` — Static screenshot

**Purpose:** Goes in the Verify tab section of docs/tui.md

**Steps:**
1. `coldreach`
2. Press `v` to switch to Verify tab
3. Type any real email (e.g. `legal@stripe.com`)
4. Press Enter, wait for verification to complete
5. Screenshot when all 4 pipeline steps show ✓/○ and the score is visible

**What should be visible:** Email input, score (e.g. "85 / 100"), all check rows with icons
**Filename:** `verify.png`

---

## File 4: `status.png` — Static screenshot

**Purpose:** Goes in the Status tab section of docs/tui.md

**Steps:**
1. `coldreach`
2. Press `s` to switch to Status tab
3. Screenshot when all 4 service cards show "● ONLINE" with green dots and latency

**What should be visible:** All 4 cards (SearXNG, Reacher, SpiderFoot, theHarvester) green
**Filename:** `status.png`

---

## File 5: `outreach.png` — Static screenshot

**Purpose:** Goes in the Outreach tab section of docs/tui.md and README

**Steps:**
1. First, do 2–3 scans on different domains and press `d` on a few emails to generate drafts
2. Press `o` to switch to Outreach tab
3. On one contact, press `s` to mark as sent
4. On another, press `R` to mark as replied
5. Screenshot the table showing a mix of statuses (● draft, → sent, ✓ replied)

**What should be visible:** Stats header "X contacts · Y replied · Z sent", colored status icons
**Filename:** `outreach.png`

---

## File 6: `chrome-extension.png` — Static screenshot

**Purpose:** Goes in docs/chrome-extension.md

**Steps:**
1. Make sure `coldreach serve` is running
2. Install the Chrome extension from `chrome-extension/dist/`
3. Open a real job posting on Greenhouse, Lever, or Indeed
4. Click the ColdReach extension icon
5. Let it scan and find emails
6. Screenshot the popup showing found emails

**What should be visible:** Extension popup with at least 2–3 email results and confidence scores
**Filename:** `chrome-extension.png`

---

## Recommended recording tools

**For GIFs on Linux:**
- `peek` — simple GUI, click record, save as GIF
- `terminalizer` — `npm install -g terminalizer`, `terminalizer record demo`, `terminalizer render demo`
- `asciinema` + `agg` — best quality: `asciinema rec demo.cast`, then `agg demo.cast demo.gif`

**For screenshots on Linux:**
- `gnome-screenshot -a` — select area
- `flameshot gui` — annotate before saving
- `scrot` — command line

**GIF optimization (reduce file size):**
```bash
gifsicle -O3 --lossy=80 demo.gif -o demo.gif
```
Target: under 5MB per GIF (GitHub renders up to ~10MB but slower)
