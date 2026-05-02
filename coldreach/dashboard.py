"""
ColdReach Outreach Dashboard — Streamlit web app.

Launch with:  coldreach dashboard
Or directly:  streamlit run coldreach/dashboard.py

Three tabs:
  Contacts  — browse all cached domains and their emails; one-click Draft
  Compose   — generate a Groq-powered cold email for any contact
  Sent      — track which emails you've sent and who replied
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import httpx
import streamlit as st

_API_BASE = "http://localhost:8765"
_DRAFTS_PATH = Path("~/.coldreach/drafts.json").expanduser()
_OUTREACH_PATH = Path("~/.coldreach/outreach.json").expanduser()

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ColdReach Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_drafts() -> list[dict]:
    if not _DRAFTS_PATH.exists():
        return []
    try:
        return json.loads(_DRAFTS_PATH.read_text())
    except Exception:
        return []


def _save_draft(draft: dict) -> None:
    _DRAFTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_drafts()
    existing.append(draft)
    _DRAFTS_PATH.write_text(json.dumps(existing, indent=2))


def _load_outreach() -> dict:
    """Load outreach tracking state: { email: { status, notes, sent_at } }"""
    if not _OUTREACH_PATH.exists():
        return {}
    try:
        return json.loads(_OUTREACH_PATH.read_text())
    except Exception:
        return {}


def _save_outreach(state: dict) -> None:
    _OUTREACH_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUTREACH_PATH.write_text(json.dumps(state, indent=2))


def _api_check() -> bool:
    """Return True if the ColdReach API server is reachable."""
    try:
        resp = httpx.get(f"{_API_BASE}/", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def _load_contacts() -> dict[str, list[dict]]:
    """Load contacts from the cache via API."""
    try:
        resp = httpx.get(f"{_API_BASE}/api/cache", timeout=5.0)
        if resp.status_code != 200:
            return {}
        cache_data = resp.json()
        domains = [d["domain"] for d in cache_data.get("domains", []) if not d.get("expired")]
        contacts: dict[str, list[dict]] = {}
        for domain in domains[:50]:  # cap at 50 domains
            try:
                scan = httpx.post(
                    f"{_API_BASE}/api/find",
                    json={"domain": domain, "quick": True, "no_cache": False},
                    timeout=10.0,
                )
                if scan.status_code == 200:
                    data = scan.json()
                    contacts[domain] = data.get("emails", [])
            except Exception:
                pass
        return contacts
    except Exception:
        return {}


def _generate_draft_api(
    email: str,
    domain: str,
    sender_name: str,
    sender_intent: str,
    email_type: str = "auto",
) -> dict | None:
    """Call /api/v2/draft and collect the complete draft."""
    try:
        with httpx.stream(
            "POST",
            f"{_API_BASE}/api/v2/draft",
            json={
                "email": email,
                "domain": domain,
                "sender_name": sender_name,
                "sender_intent": sender_intent,
                "email_type": email_type,
            },
            timeout=60.0,
        ) as resp:
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    try:
                        payload = json.loads(line[5:].strip())
                        if "subject" in payload and "body" in payload:
                            return payload
                        if "detail" in payload:
                            return {"error": payload["detail"]}
                    except Exception:
                        pass
    except Exception as exc:
        return {"error": str(exc)}
    return None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚡ ColdReach")
    st.caption("Open-source email discovery & outreach")
    st.divider()

    api_ok = _api_check()
    if api_ok:
        st.success("API server online", icon="✅")
    else:
        st.error("API server offline — run: coldreach serve", icon="🔴")
        st.code("coldreach serve", language="bash")

    st.divider()
    st.caption("v0.1.0 · [GitHub](https://github.com/dhruvmojila/coldreach)")

# ---------------------------------------------------------------------------
# Main content — 3 tabs
# ---------------------------------------------------------------------------

tab_contacts, tab_compose, tab_sent = st.tabs(["📋 Contacts", "✏️ Compose", "📤 Sent"])


# ── Tab 1: Contacts ──────────────────────────────────────────────────────────

with tab_contacts:
    st.header("Discovered Contacts")

    if not api_ok:
        st.warning("Start the API server to load contacts: `coldreach serve`")
    else:
        col_refresh, col_filter = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()

        @st.cache_data(ttl=60)
        def cached_contacts() -> dict:
            return _load_contacts()

        contacts = cached_contacts()
        outreach = _load_outreach()

        if not contacts:
            st.info("No cached contacts yet. Run `coldreach find --domain company.com` first.")
        else:
            domains = sorted(contacts.keys())
            selected_domain = st.selectbox("Domain", domains, label_visibility="collapsed")

            emails = contacts.get(selected_domain, [])
            if not emails:
                st.info(f"No emails found for {selected_domain}")
            else:
                st.caption(f"{len(emails)} email(s) found · {selected_domain}")

                for em in emails:
                    addr = em.get("email", "")
                    status_val = em.get("status", "unknown")
                    confidence = em.get("confidence", 0)
                    source = (
                        em.get("sources", [{}])[0].get("source", "—") if em.get("sources") else "—"
                    )

                    tracked = outreach.get(addr, {})
                    tracked_status = tracked.get("status", "new")

                    status_color = {
                        "valid": "🟢",
                        "catch_all": "🟡",
                        "unknown": "⚪",
                        "invalid": "🔴",
                    }.get(status_val, "⚪")

                    outreach_color = {"sent": "📤", "replied": "💬", "new": "🆕"}.get(
                        tracked_status, "🆕"
                    )

                    with st.expander(
                        f"{status_color} {addr}  ·  {confidence}%  ·  {outreach_color}",
                        expanded=False,
                    ):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Confidence", f"{confidence}%")
                        c2.metric("Verification", status_val)
                        c3.metric("Source", source.split("/")[-1])

                        if st.button("✏️ Draft email", key=f"draft_{addr}"):
                            st.session_state["compose_email"] = addr
                            st.session_state["compose_domain"] = selected_domain
                            st.rerun()

                        col_mark1, col_mark2 = st.columns(2)
                        if col_mark1.button("📤 Mark Sent", key=f"sent_{addr}"):
                            outreach[addr] = {
                                "status": "sent",
                                "sent_at": datetime.now().isoformat(),
                                "domain": selected_domain,
                            }
                            _save_outreach(outreach)
                            st.success("Marked as sent!")
                        if col_mark2.button("💬 Mark Replied", key=f"replied_{addr}"):
                            outreach[addr] = {
                                **outreach.get(addr, {}),
                                "status": "replied",
                                "replied_at": datetime.now().isoformat(),
                            }
                            _save_outreach(outreach)
                            st.success("Marked as replied! 🎉")


# ── Tab 2: Compose ───────────────────────────────────────────────────────────

with tab_compose:
    st.header("Draft a Cold Email")
    st.caption("Groq generates a personalized email based on the company's public website.")

    if not api_ok:
        st.warning("Start `coldreach serve` to use draft generation.")
    else:
        # Pre-fill from Contacts tab click
        prefill_email = st.session_state.get("compose_email", "")
        prefill_domain = st.session_state.get("compose_domain", "")

        with st.form("compose_form"):
            col_a, col_b = st.columns(2)
            recipient_email = col_a.text_input("Recipient email", value=prefill_email)
            domain_input = col_b.text_input("Company domain", value=prefill_domain)

            col_c, col_d = st.columns(2)
            your_name = col_c.text_input(
                "Your name",
                value=st.session_state.get("sender_name", ""),
                placeholder="Jane Smith",
            )
            email_type = col_d.selectbox(
                "Email type",
                ["auto", "job_application", "partnership", "sales", "introduction"],
                format_func=lambda x: {
                    "auto": "🤖 Auto-detect",
                    "job_application": "💼 Job Application",
                    "partnership": "🤝 Partnership",
                    "sales": "💰 Sales",
                    "introduction": "👋 Introduction",
                }[x],
            )

            intent = st.text_area(
                "What do you want from this person?",
                placeholder="I'd like to explore a partnership around embedded payments.",
                max_chars=200,
                height=80,
            )

            submitted = st.form_submit_button(
                "⚡ Generate Draft", type="primary", use_container_width=True
            )

        if submitted:
            if not all([recipient_email, domain_input, your_name, intent]):
                st.error("Please fill in all fields.")
            else:
                st.session_state["sender_name"] = your_name
                with st.spinner("Fetching company context & generating draft…"):
                    result = _generate_draft_api(
                        email=recipient_email,
                        domain=domain_input,
                        sender_name=your_name,
                        sender_intent=intent,
                        email_type=email_type,
                    )

                if result is None:
                    st.error("Draft generation failed. Check that `coldreach serve` is running.")
                elif "error" in result:
                    st.error(f"Error: {result['error']}")
                    if "groq" in result["error"].lower() or "api key" in result["error"].lower():
                        st.info("Add `COLDREACH_GROQ_API_KEY=gsk_xxx` to your `.env` file.")
                else:
                    st.success("Draft ready!")
                    st.subheader(f"Subject: {result['subject']}")
                    st.markdown("---")
                    st.text_area("Email body", value=result["body"], height=200, key="draft_body")
                    st.caption(f"*Best,  \n{your_name}*")
                    st.markdown("---")

                    col_copy, col_save = st.columns(2)
                    full_text = (
                        f"Subject: {result['subject']}\n\n{result['body']}\n\nBest,\n{your_name}"
                    )

                    col_copy.code(full_text, language=None)

                    if col_save.button("💾 Save Draft", use_container_width=True):
                        _save_draft(
                            {
                                "to": recipient_email,
                                "subject": result["subject"],
                                "body": result["body"],
                                "sender": your_name,
                                "domain": domain_input,
                                "type": result.get("email_type", "auto"),
                                "created_at": datetime.now().isoformat(),
                            }
                        )
                        st.success(f"Saved to {_DRAFTS_PATH}")


# ── Tab 3: Sent ──────────────────────────────────────────────────────────────

with tab_sent:
    st.header("Outreach Tracker")
    st.caption("Track which emails you've sent and who replied.")

    outreach = _load_outreach()
    drafts = _load_drafts()

    if not outreach and not drafts:
        st.info("No outreach tracked yet. Go to **Contacts** to mark emails as sent.")
    else:
        # Summary metrics
        sent_count = sum(1 for v in outreach.values() if v.get("status") == "sent")
        replied_count = sum(1 for v in outreach.values() if v.get("status") == "replied")
        drafts_count = len(drafts)

        m1, m2, m3 = st.columns(3)
        m1.metric("Drafts saved", drafts_count)
        m2.metric("Sent", sent_count)
        m3.metric(
            "Replied", replied_count, delta=f"{replied_count}/{max(sent_count, 1)} reply rate"
        )

        if outreach:
            st.subheader("Contact status")
            rows = [
                {
                    "Email": addr,
                    "Status": v.get("status", "new").capitalize(),
                    "Domain": v.get("domain", "—"),
                    "Sent at": v.get("sent_at", "—")[:10] if v.get("sent_at") else "—",
                    "Replied at": v.get("replied_at", "—")[:10] if v.get("replied_at") else "—",
                }
                for addr, v in outreach.items()
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

        if drafts:
            st.subheader("Saved drafts")
            for i, d in enumerate(reversed(drafts)):
                with st.expander(f"📧 {d.get('to', '?')} — {d.get('subject', 'No subject')[:60]}"):
                    st.text(f"To: {d.get('to')}")
                    st.text(f"Subject: {d.get('subject')}")
                    st.text_area("Body", value=d.get("body", ""), height=150, key=f"draft_view_{i}")
                    st.caption(f"Saved: {d.get('created_at', '?')[:19]}")
