# Design Brief — ColdReach Dashboard

## Problem
The existing dashboard looks like a developer prototype: plain tabs, expandable rows,
no visual hierarchy. Non-technical users (founders, job seekers, sales reps) feel lost.

## Goal
A professional outreach workspace at Apollo.io quality — one where a non-developer
can land, immediately understand their contacts, scan a new domain, draft an email,
and track their outreach without ever touching a CLI.

## Users
- **Indie founders** finding partnership contacts
- **Job seekers** finding hiring managers
- **Sales reps** building lead lists
None are developers. They compare this to Apollo.io, Hunter.io, Notion.

## Core Flows (must all work from dashboard)
1. **Scan** — enter domain → live progress → emails appear one-by-one
2. **Browse** — see all contacts with clear status badges
3. **Draft** — one-click per email → fill name + intent → AI writes the email
4. **Track** — mark sent / replied, see reply rate

## Aesthetic
- **Reference**: Apollo.io, Linear, Notion — clean, data-dense, trustworthy
- **Theme**: Dark (`#0f1117` base, `#1a1d27` cards, `#5b8cff` accent)
- **NOT**: Streamlit's default widget look, Bootstrap primary blue, "app" feel
- **Typography**: System font stack, tight letter-spacing for headings, tabular nums for metrics
- **Motion**: Subtle — only scan progress animates; nothing bounces

## Layout
- **Left sidebar** (220px): logo + nav links (Home · Find · Contacts · Compose · Sent)
- **Main area**: context-aware page content
- **No tabs inside main area** — each nav item IS its own page

## Key Differentiators vs Current Build
- Scan page with live SSE progress (spinner → source pills appearing → email cards populating)
- Contacts as a card grid (not dropdowns)
- Status badge system (Verified / Catch-all / Unknown / Sent / Replied)
- Compose panel as a focused 3-step wizard (not a form dump)
