# HN Launch — Show HN Post

Use this when submitting to Hacker News. Copy title and body verbatim.

---

## Title

```
Show HN: ColdReach – self-hosted email finder with TUI and Groq drafting (Hunter.io alternative)
```

## Body

```
I've been paying $49/month for Apollo.io to find emails for cold outreach. It works, but your
data lives on their servers, there are monthly rate limits, and you're tied to their workflow.

ColdReach runs entirely on your machine — nothing leaves your computer. It searches 8 parallel
sources (web crawling, GitHub commits, WHOIS, SearXNG, Reddit, SpiderFoot, theHarvester),
verifies results with real SMTP handshakes via a self-hosted Reacher container, and can draft a
personalized cold email using Groq (free tier, ~2s generation).

This release ships with:
- A full-screen terminal UI (Textual) that streams emails live as each source completes
- A Chrome extension for Greenhouse, Lever, Indeed, LinkedIn Jobs, and Workable
- Groq integration that scrapes the company site and generates 3 subject-line variants + body
- An outreach tracker inside the TUI — mark contacts as draft → sent → replied, all in SQLite
- A local FastAPI server at localhost:8765 for scripting and automation

Honest caveat: accuracy is 50–70% vs 85–90% for Hunter.io. The gap narrows for companies with
active GitHub presence. BYOK mode (plug in your own Hunter/Apollo key as a fallback) is planned
for the next release.

Would love to hear: is the self-hosted privacy trade-off worth it for your workflow, or does
accuracy make paid tools unavoidable?

GitHub: https://github.com/dhruvmojila/coldreach
```

---

## Submission checklist

- [ ] Submit at https://news.ycombinator.com/submit
- [ ] Post between 9–11am PT on a weekday (Mon–Wed tend to be highest traffic)
- [ ] Do not ask for upvotes in the post or in other channels
- [ ] Monitor comments for the first 2 hours and reply to every technical question
- [ ] If it gains traction, pin a "Thanks HN" update at the top of the README
