# Information Architecture — ColdReach Dashboard

## Navigation (Left Sidebar)
```
⚡ ColdReach
─────────────
🏠  Home         ← overview: metrics + recent scans
🔍  Find Emails  ← scan a new domain (the hero action)
📋  Contacts     ← all discovered emails, filterable
✏️  Compose      ← draft generator
📤  Sent         ← outreach tracker
─────────────
● API Online
```

## Page: Home
- **4 metric cards** (row): Total contacts | Verified | Drafts | Replies
- **Recent domains** table (last 5 scanned, with "Re-scan" button)
- **Quick-start CTA** if no contacts yet: "Start by scanning a domain →"

## Page: Find Emails (the hero)
Step 1 — Input
  - Large domain input + "Scan" button (primary)
  - Mode pills: Quick (30s) · Standard (3min) · Full (8min)
  - Hint: "No CLI needed — just enter a domain"

Step 2 — Live Scan (replaces form when scan starts)
  - Animated progress bar (0→100%)
  - Source pills appearing one-by-one as each source completes
    (web · whois · github · reddit · searxng · spiderfoot · harvester)
  - "X emails found so far..." live counter
  - Each email appears as a mini-card as it's discovered
  - "Stop scan" button

Step 3 — Done
  - Summary: "Found 14 emails for stripe.com"
  - CTA: "Browse contacts →" | "Draft emails →"

## Page: Contacts
- **Filter bar**: domain selector | status filter (All/Verified/Unknown/Catch-all) | search
- **Card grid** (3 col on wide, 1 col on narrow)
  Each card:
    Email address (monospace)
    Status badge (color-coded)
    Confidence bar
    Source tag
    [Draft] button
- Empty state: "No contacts yet — scan a domain first"

## Page: Compose
- **Step 1**: Pick a contact (search/select from contacts or type email + domain)
- **Step 2**: Fill your info (name + 1-sentence intent)
- **Step 3**: Draft appears (streamed word-by-word)
  - Copy | Save | Send (future) buttons
- Saved drafts listed below

## Page: Sent
- **Metrics row**: Sent | Replied | Reply rate
- **Table**: email | subject | sent date | status | notes
- Click row → expand to see draft content
- Buttons: Mark Replied | Archive
