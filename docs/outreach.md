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

## Flow B — Dashboard (most visual)

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
       → feed to Groq (llama-3.1-8b-instant)
       → structured output: { subject, body }
```

**What makes it not generic:**
- Company description comes from their actual website (not Wikipedia)
- Template guidance tells Groq the tone, length, and what to avoid
- Subject is constrained to <60 chars, no clickbait
- Body is capped at 4 sentences — forces clarity

**What Groq DOESN'T know:**
- Your personal history with the company
- Their current open roles
- Internal contacts

You should review and edit every draft before sending.

---

## Saving drafts

Drafts are saved to `~/.coldreach/drafts.json`:

```bash
# View all saved drafts
cat ~/.coldreach/drafts.json | jq '.[].subject'

# Clear drafts
rm ~/.coldreach/drafts.json
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
→ Add `COLDREACH_GROQ_API_KEY=gsk_xxx` to your `.env` and restart `coldreach serve`.

**"Draft generation failed"**
→ Check `coldreach serve` is running (`coldreach status`). Groq may be rate-limited —
wait 60s and try again (free tier: 14,400 tokens/min resets every minute).

**Context is generic / wrong company**
→ The site may be a JavaScript SPA that plain httpx can't render. Try:
`coldreach find --domain company.com --crawl4ai --draft`

**Draft quality is poor**
→ Be more specific in your intent. "I want to discuss business" → "I want to explore
integrating your payment API into our B2B SaaS for the SMB segment."
