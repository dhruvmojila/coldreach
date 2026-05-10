# Outreach Guide

ColdReach Phase 5 closes the loop: after finding emails you can generate
a personalized cold email draft and track your outreach — all in one tool.

## Prerequisites

```bash
# 1. Get a free Groq API key (14,400 tokens/min free)
#    https://console.groq.com/

# 2. Add to .env
echo 'COLDREACH_GROQ_API_KEY=gsk_xxx' >> .env

# 3. Install Streamlit for the dashboard (optional)
pip install coldreach[dashboard]

# 4. Start the API server (needed for dashboard draft generation)
coldreach serve
```

---

## Flow A — CLI Draft (fastest)

Find emails and draft in one command:

```bash
coldreach find --domain stripe.com --name "Patrick Collison" --draft
```

ColdReach will:
1. Find `patrick@stripe.com` (or the best match)
2. Scrape `stripe.com` for company context
3. Ask you two quick questions:
   - **Your name:** `Jane Smith`
   - **What you want (one sentence):** `explore a partnership on embedded payments`
4. Groq generates a subject + 3-sentence body
5. Show the draft with `[c]opy / [s]ave / [q]uit`

**Skip the prompts** by providing all flags upfront:

```bash
coldreach find --domain stripe.com --draft \
  --name "Patrick Collison" \
  --sender-name "Jane Smith" \
  --intent "explore a partnership on embedded payments" \
  --template partnership
```

**Template types:**

| `--template` | Best for |
|---|---|
| `auto` | Let ColdReach detect from your intent (default) |
| `job_application` | Applying for a role |
| `partnership` | Business collaboration |
| `sales` | Selling a product or service |
| `introduction` | Building a relationship, no specific ask |

---

## Flow B — TUI Outreach tab (recommended)

![Draft panel — company preview, 3 subjects, copy in one keypress](images/draft.gif)

The fastest workflow — no browser needed:

```
coldreach
```

1. **Find tab** (`f`) → scan a domain → emails stream in
2. Select an email → press `d` → DraftPanel opens below
3. Company info appears immediately at the top (fetched in background)
4. Fill **Your name** + **What you want**, choose Fast or Quality model
5. Press **Generate** → 3 subject line variants appear + body
6. Press `1`, `2`, or `3` to pick a subject
7. Press `y` → full email copied to clipboard
8. Switch to **Outreach tab** (`o`) → contact auto-added with status `draft`
9. After sending: press `s` → status becomes `sent`
10. When they reply: press `R` → status becomes `replied`

```
┌─ Draft for patrick@stripe.com ─────────────────────────────────────────┐
│  Stripe  ·  Fintech  ·  San Francisco                                  │
│  "Global payments infrastructure for internet businesses"              │
│                                                                        │
│  Your name:    [Jane Smith              ]                              │
│  What you want:[explore a payment integration partnership    ]         │
│  Type:   [Auto] [Partner] [Sales] [Job] [Intro]                       │
│  Model:  [Fast (llama-3.1-8b)]  [Quality (llama-3.3-70b)]            │
│                           [Generate]  [Regenerate]                    │
│  ────────────────────────────────────────────────────────────────────  │
│  A: Partnership on Stripe's embedded payments  ← selected (press 1)  │
│  B: Quick question about your payment API program  (press 2)          │
│  C: Exploring fintech collaboration — Jane Smith  (press 3)           │
│                                                                        │
│  Hi Patrick, I've been following Stripe's recent expansion into...     │
│                                     [y: Copy full email]  [Esc: Close]│
└────────────────────────────────────────────────────────────────────────┘
```

**No Groq key?** The panel still works — it shows a template skeleton with `[PLACEHOLDER]` fields you can fill manually.

---

## Flow C — Dashboard (most visual)

```bash
coldreach dashboard
```

Opens at **http://localhost:8501** with three tabs:

### 📋 Contacts tab

- Shows all domains you've scanned (from the local cache)
- Each email shows: verification status, confidence score, discovery source
- Click **Draft** next to any email → jumps to the Compose tab pre-filled

### ✏️ Compose tab

Fill in:
- **Recipient email** (pre-filled from Contacts click)
- **Company domain** (pre-filled)
- **Your name**
- **What you want** — one sentence is enough; Groq does the rest
- **Email type** — or leave on Auto

Click **Generate Draft** → the email appears on screen. Copy it with the code block
and paste into Gmail, Outlook, or wherever you send from.

### 📤 Sent tab

- Mark emails as **Sent** or **Replied** manually
- View all saved drafts
- See your reply rate at a glance

Tracking data is stored in `~/.coldreach/outreach.json` — just a local JSON file.

---

## Flow C — Chrome Extension Draft

After finding emails on a job posting:

1. Click **✏️** next to any email in the extension popup
2. Fill in: your name, your one-sentence intent
3. Click **Generate** — the draft streams in word-by-word
4. Copy with one click → paste into Gmail

---

## How Groq personalization works

ColdReach uses [DSPy](https://dspy.ai/) with Groq for structured email generation:

```
domain → scrape homepage/about page
       → extract: company name, description, industry, location
       → feed to Groq (llama-3.1-8b-instant or llama-3.3-70b-versatile)
       → structured output: { subject_a, subject_b, subject_c, body }
```

**3 subject variants** — Groq generates three distinct angles in one call:
- **A** — specific, references the company or role
- **B** — question or curiosity-driven
- **C** — direct and minimal

Pick the one that fits your style. The TUI lets you switch with `1`/`2`/`3`.

**Model choice:**
| Model | Speed | Quality | Best for |
|-------|-------|---------|----------|
| Fast (llama-3.1-8b-instant) | ~2s | Good | Most drafts |
| Quality (llama-3.3-70b-versatile) | ~8s | Excellent | High-value contacts |

**What makes it not generic:**
- Company description comes from their actual website (not Wikipedia)
- Template guidance tells Groq the tone, length, and what to avoid
- Subjects are constrained to <60 chars, no clickbait
- Body is capped at 4 sentences — forces clarity

**What Groq DOESN'T know:**
- Your personal history with the company
- Their current open roles
- Internal contacts

You should review and edit every draft before sending.

---

## Outreach tracking

Contacts and drafts are stored in `~/.coldreach/cache.db` (same SQLite file as the email cache):

```bash
# View outreach contacts via SQLite
sqlite3 ~/.coldreach/cache.db "SELECT email, status, subject FROM outreach ORDER BY created_at DESC"

# Count by status
sqlite3 ~/.coldreach/cache.db "SELECT status, COUNT(*) FROM outreach GROUP BY status"
```

The TUI Outreach tab (`o`) gives you a full UI to manage this. Status flow:

```
new → draft → sent → replied
```

---

## API integration

The draft endpoint works with any HTTP client — useful for automation:

```python
import httpx

resp = httpx.post("http://localhost:8765/api/v2/draft", json={
    "email": "ceo@company.com",
    "domain": "company.com",
    "sender_name": "Jane Smith",
    "sender_intent": "partnership discussion",
    "email_type": "partnership",
})

for line in resp.text.split("\n"):
    if line.startswith("data:"):
        import json
        payload = json.loads(line[5:])
        if "body" in payload:
            print(payload["subject"])
            print(payload["body"])
```

---

## Troubleshooting

**"Groq API key required"**
→ In the TUI, the draft panel will show a template skeleton — you can still draft manually.
→ For CLI/API: add `COLDREACH_GROQ_API_KEY=gsk_xxx` to your `.env`.

**"Draft generation failed"**
→ Check `coldreach serve` is running (`coldreach status`). Groq may be rate-limited —
wait 60s and try again (free tier: 14,400 tokens/min resets every minute).

**Context is generic / wrong company**
→ The site may be a JavaScript SPA that plain httpx can't render. Try:
`coldreach find --domain company.com --crawl4ai --draft`

**Draft quality is poor**
→ Be more specific in your intent. "I want to discuss business" → "I want to explore
integrating your payment API into our B2B SaaS for the SMB segment."
