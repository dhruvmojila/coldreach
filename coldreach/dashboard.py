"""
ColdReach Outreach Dashboard — Professional Streamlit web app.

Launch:  coldreach dashboard
Direct:  streamlit run coldreach/dashboard.py

Navigation (left sidebar):
  Home       — metrics overview + recent scans
  Find       — scan a domain with live SSE progress
  Contacts   — card grid of all discovered emails
  Compose    — Groq-powered draft generator
  Sent       — outreach tracker
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import httpx
import streamlit as st

_API = "http://localhost:8765"
_DRAFTS = Path("~/.coldreach/drafts.json").expanduser()
_OUTREACH = Path("~/.coldreach/outreach.json").expanduser()

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ColdReach",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens + global CSS ────────────────────────────────────────────────

st.markdown(
    """
<style>
/* ── Reset Streamlit defaults ── */
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding: 1.5rem 2rem 2rem;}
[data-testid="stSidebar"] {background: #13151f; border-right: 1px solid #2a2d3e;}
[data-testid="stSidebar"] > div:first-child {padding: 1.2rem 1rem;}

/* ── Typography ── */
body, .stApp {font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;}
h1 {font-size: 1.5rem !important; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0.25rem !important;}
h2 {font-size: 1.1rem !important; font-weight: 600; letter-spacing: -0.01em; color: #c9cde8;}
h3 {font-size: 0.95rem !important; font-weight: 600;}

/* ── Sidebar nav ── */
.nav-logo {font-size: 1.25rem; font-weight: 800; color: #5b8cff; letter-spacing: -0.03em; margin-bottom: 1.5rem; padding: 0 0.25rem;}
.nav-logo span {color: #ffffff;}
.nav-btn {
    display: flex; align-items: center; gap: 0.6rem;
    padding: 0.55rem 0.75rem; border-radius: 8px;
    font-size: 0.88rem; font-weight: 500; color: #9aa0c0;
    cursor: pointer; transition: all 0.15s; margin-bottom: 0.2rem;
    text-decoration: none; border: none; background: none; width: 100%;
}
.nav-btn:hover {background: #1f2235; color: #e0e4f7;}
.nav-btn.active {background: #1a2850; color: #7aa6ff; font-weight: 600;}
.nav-divider {border-top: 1px solid #2a2d3e; margin: 1rem 0;}

/* ── Metric cards ── */
.metric-card {
    background: #1a1d27; border: 1px solid #2a2d3e; border-radius: 12px;
    padding: 1.1rem 1.25rem; height: 100%;
}
.metric-label {font-size: 0.75rem; font-weight: 500; color: #6b7099; text-transform: uppercase; letter-spacing: 0.06em;}
.metric-value {font-size: 2rem; font-weight: 700; color: #e8ecff; font-variant-numeric: tabular-nums; line-height: 1.1; margin-top: 0.25rem;}
.metric-delta {font-size: 0.8rem; margin-top: 0.3rem;}
.metric-delta.up {color: #34d399;}
.metric-delta.neutral {color: #6b7099;}

/* ── Email cards ── */
.email-card {
    background: #1a1d27; border: 1px solid #2a2d3e; border-radius: 10px;
    padding: 0.9rem 1rem; margin-bottom: 0.6rem;
    transition: border-color 0.15s;
}
.email-card:hover {border-color: #3a3f5e;}
.email-addr {font-family: "SF Mono", "Fira Code", monospace; font-size: 0.88rem; font-weight: 600; color: #c9cde8;}
.email-meta {font-size: 0.75rem; color: #6b7099; margin-top: 0.25rem;}

/* ── Badges ── */
.badge {display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.2rem 0.55rem; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.02em;}
.badge-valid {background: #0d2e1f; color: #34d399; border: 1px solid #134d31;}
.badge-catchall {background: #2e2408; color: #f59e0b; border: 1px solid #4d3a0a;}
.badge-unknown {background: #1a1d27; color: #6b7099; border: 1px solid #2a2d3e;}
.badge-invalid {background: #2e0e0e; color: #f87171; border: 1px solid #4d1515;}
.badge-sent {background: #0e1a2e; color: #5b8cff; border: 1px solid #1a3366;}
.badge-replied {background: #0d2e20; color: #6ee7b7; border: 1px solid #134d33;}

/* ── Confidence bar ── */
.conf-bar-bg {background: #2a2d3e; border-radius: 4px; height: 4px; margin-top: 0.4rem;}
.conf-bar-fill {background: #5b8cff; border-radius: 4px; height: 4px;}

/* ── Source pill ── */
.source-pill {display: inline-block; background: #1f2235; color: #7a82aa; border-radius: 6px; padding: 0.15rem 0.5rem; font-size: 0.7rem; font-weight: 500; margin-right: 0.3rem;}
.source-pill.done {background: #0f2a18; color: #34d399;}
.source-pill.active {background: #1a2850; color: #7aa6ff; animation: pulse 1.5s infinite;}

/* ── Progress ── */
.scan-counter {font-size: 1.5rem; font-weight: 700; color: #5b8cff; font-variant-numeric: tabular-nums;}
.scan-domain {font-size: 0.95rem; color: #6b7099; margin-top: 0.1rem;}

/* ── Buttons (override Streamlit) ── */
.stButton > button {border-radius: 8px; font-weight: 600; font-size: 0.875rem; border: none; transition: all 0.15s;}
.stButton > button[kind="primary"] {background: #5b8cff !important; color: #fff !important;}
.stButton > button[kind="primary"]:hover {background: #4a7aee !important;}
.stButton > button[kind="secondary"] {background: #1f2235 !important; color: #c9cde8 !important; border: 1px solid #2a2d3e !important;}

/* ── Input fields ── */
.stTextInput > div > div > input {background: #1a1d27 !important; border: 1px solid #2a2d3e !important; border-radius: 8px !important; color: #e0e4f7 !important; font-size: 0.9rem !important;}
.stTextInput > div > div > input:focus {border-color: #5b8cff !important; box-shadow: 0 0 0 2px rgba(91,140,255,0.15) !important;}
.stTextArea textarea {background: #1a1d27 !important; border: 1px solid #2a2d3e !important; border-radius: 8px !important; color: #e0e4f7 !important;}

/* ── Section headers ── */
.section-header {display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid #2a2d3e;}
.page-title {font-size: 1.3rem; font-weight: 700; color: #e8ecff; letter-spacing: -0.02em;}
.page-subtitle {font-size: 0.85rem; color: #6b7099; margin-top: 0.15rem;}

/* ── Empty state ── */
.empty-state {text-align: center; padding: 3rem 1rem; color: #6b7099;}
.empty-state-icon {font-size: 2.5rem; margin-bottom: 0.75rem;}
.empty-state-title {font-size: 1rem; font-weight: 600; color: #9aa0c0; margin-bottom: 0.4rem;}
.empty-state-sub {font-size: 0.85rem;}

/* ── Animations ── */
@keyframes pulse {0%,100%{opacity:1;}50%{opacity:0.5;}}
@keyframes fadeIn {from{opacity:0;transform:translateY(4px);}to{opacity:1;transform:none;}}
.fade-in {animation: fadeIn 0.3s ease;}

/* ── Draft output ── */
.draft-box {background: #13151f; border: 1px solid #2a2d3e; border-radius: 10px; padding: 1.25rem; font-size: 0.9rem; line-height: 1.6; color: #c9cde8;}
.draft-subject {font-size: 0.8rem; font-weight: 600; color: #5b8cff; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.5rem;}
</style>
""",
    unsafe_allow_html=True,
)

# ── Data helpers ──────────────────────────────────────────────────────────────


def _api_ok() -> bool:
    try:
        return httpx.get(f"{_API}/", timeout=2.0).status_code == 200
    except Exception:
        return False


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _load_drafts() -> list:
    return _load_json(_DRAFTS, [])


def _load_outreach() -> dict:
    return _load_json(_OUTREACH, {})


def _save_outreach(state: dict) -> None:
    _save_json(_OUTREACH, state)


@st.cache_data(ttl=30)
def _cached_domains() -> list[dict]:
    try:
        resp = httpx.get(f"{_API}/api/cache", timeout=5.0)
        if resp.status_code == 200:
            return resp.json().get("domains", [])
    except Exception:
        pass
    return []


@st.cache_data(ttl=30)
def _cached_emails(domain: str) -> list[dict]:
    try:
        resp = httpx.post(
            f"{_API}/api/find",
            json={"domain": domain, "quick": True, "no_cache": False},
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json().get("emails", [])
    except Exception:
        pass
    return []


def _all_contacts() -> list[dict]:
    """Return flat list of all {email, domain, status, confidence, source}."""
    domains = [d["domain"] for d in _cached_domains() if not d.get("expired")]
    contacts = []
    for domain in domains[:30]:
        for em in _cached_emails(domain):
            contacts.append({**em, "domain": domain})
    return contacts


def _badge_html(status: str) -> str:
    dot = {"valid": "●", "catch_all": "◐", "unknown": "○", "invalid": "✕"}.get(status, "○")
    label = status.replace("_", "-")
    cls = f"badge-{status.replace('_', '')}".replace("catchall", "catchall")
    return f'<span class="badge {cls}">{dot} {label}</span>'


def _conf_bar(pct: int) -> str:
    color = "#34d399" if pct >= 70 else "#f59e0b" if pct >= 40 else "#6b7099"
    return (
        f'<div class="conf-bar-bg"><div class="conf-bar-fill" '
        f'style="width:{pct}%;background:{color};"></div></div>'
    )


# ── Sidebar navigation ────────────────────────────────────────────────────────

api_online = _api_ok()

with st.sidebar:
    st.markdown('<div class="nav-logo">⚡ <span>ColdReach</span></div>', unsafe_allow_html=True)

    pages = {
        "Home": "🏠",
        "Find Emails": "🔍",
        "Contacts": "📋",
        "Compose": "✏️",
        "Sent": "📤",
    }

    if "page" not in st.session_state:
        st.session_state.page = "Home"

    for label, icon in pages.items():
        active = "active" if st.session_state.page == label else ""
        if st.button(
            f"{icon}  {label}",
            key=f"nav_{label}",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state.page = label
            # Clear any running scan state when navigating away
            if label != "Find Emails":
                st.session_state.pop("scan_job_id", None)
            st.rerun()

    st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)

    if api_online:
        st.markdown(
            '<p style="font-size:0.75rem;color:#34d399;padding:0 0.75rem;">● API online</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="font-size:0.75rem;color:#f87171;padding:0 0.75rem;">○ API offline</p>',
            unsafe_allow_html=True,
        )
        st.caption("Run `coldreach serve` to enable scan & draft.")


page = st.session_state.page

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════════════════════

if page == "Home":
    contacts = _all_contacts()
    outreach = _load_outreach()
    drafts = _load_drafts()
    domains = _cached_domains()

    total = len(contacts)
    verified = sum(1 for c in contacts if c.get("status") == "valid")
    sent = sum(1 for v in outreach.values() if v.get("status") == "sent")
    replied = sum(1 for v in outreach.values() if v.get("status") == "replied")

    st.markdown(
        '<div class="page-title">Dashboard</div>'
        '<div class="page-subtitle">Your outreach overview</div>',
        unsafe_allow_html=True,
    )
    st.markdown("&nbsp;", unsafe_allow_html=True)

    # Metric cards
    cols = st.columns(4)
    metrics = [
        ("Contacts", total, "people discovered"),
        ("Verified", verified, "SMTP confirmed"),
        ("Drafts saved", len(drafts), "ready to send"),
        ("Replied", replied, f"of {sent} sent"),
    ]
    for col, (label, value, sub) in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                f'<div class="metric-delta neutral">{sub}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("&nbsp;", unsafe_allow_html=True)

    if not domains:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-state-icon">🔍</div>'
            '<div class="empty-state-title">No contacts yet</div>'
            '<div class="empty-state-sub">Scan your first domain to get started.</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Scan your first domain →", type="primary"):
            st.session_state.page = "Find Emails"
            st.rerun()
    else:
        st.markdown(
            '<div class="section-header"><h2>Recent scans</h2></div>', unsafe_allow_html=True
        )
        for d in domains[:8]:
            dom = d["domain"]
            expired = "⚠️ expired" if d.get("expired") else "✓ cached"
            color = "#f59e0b" if d.get("expired") else "#34d399"
            cached_at = d.get("cached_at", "")[:10]
            col_a, col_b, col_c = st.columns([3, 2, 1])
            col_a.markdown(
                f'<span style="font-weight:600;color:#c9cde8;">{dom}</span>',
                unsafe_allow_html=True,
            )
            col_b.markdown(
                f'<span style="font-size:0.8rem;color:{color};">{expired}</span>'
                f'<span style="font-size:0.75rem;color:#6b7099;margin-left:0.5rem;">{cached_at}</span>',
                unsafe_allow_html=True,
            )
            if col_c.button("Scan again", key=f"rescan_{dom}", type="secondary"):
                st.session_state.page = "Find Emails"
                st.session_state.prefill_domain = dom
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: FIND EMAILS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Find Emails":
    st.markdown(
        '<div class="page-title">Find Emails</div>'
        '<div class="page-subtitle">Scan any company domain — results appear live as each source completes.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("&nbsp;", unsafe_allow_html=True)

    if not api_online:
        st.warning(
            "⚠️  The API server is offline. Start it with `coldreach serve` then refresh.", icon="🔴"
        )
        st.stop()

    # ── Input form ────────────────────────────────────────────────────────────
    prefill = st.session_state.pop("prefill_domain", "")

    with st.container():
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            domain_input = st.text_input(
                "Domain",
                value=prefill,
                placeholder="stripe.com",
                label_visibility="collapsed",
            )
        with col_btn:
            scan_clicked = st.button("Scan →", type="primary", use_container_width=True)

        mode_cols = st.columns(3)
        mode = "standard"
        labels = {
            "quick": "⚡ Quick · 30s",
            "standard": "🔍 Standard · 3min",
            "full": "🌐 Full scan · 8min",
        }
        for i, (m, lbl) in enumerate(labels.items()):
            with mode_cols[i]:
                if st.button(
                    lbl,
                    key=f"mode_{m}",
                    use_container_width=True,
                    type="primary"
                    if st.session_state.get("scan_mode", "standard") == m
                    else "secondary",
                ):
                    st.session_state.scan_mode = m
                    st.rerun()
        mode = st.session_state.get("scan_mode", "standard")

    st.markdown("&nbsp;", unsafe_allow_html=True)

    # ── Live scan ─────────────────────────────────────────────────────────────
    if scan_clicked and domain_input.strip():
        domain_clean = domain_input.strip().lower().removeprefix("www.")
        st.session_state.scan_domain = domain_clean
        st.session_state.scan_emails = []
        st.session_state.scan_sources_done = []
        st.session_state.scan_complete = False
        st.session_state.scan_error = None
        st.session_state.scan_total_sources = 0
        st.session_state.scan_percent = 0

        # Start the v2 job
        try:
            resp = httpx.post(
                f"{_API}/api/v2/scan",
                json={
                    "domain": domain_clean,
                    "quick": mode == "quick",
                    "full_scan": mode == "full",
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                st.session_state.scan_job_id = resp.json()["job_id"]
            else:
                st.session_state.scan_error = f"Could not start scan (HTTP {resp.status_code})"
        except Exception as exc:
            st.session_state.scan_error = str(exc)

    # Show scan UI if a job is running or complete
    if "scan_job_id" in st.session_state or st.session_state.get("scan_complete"):
        domain = st.session_state.get("scan_domain", "")
        job_id = st.session_state.get("scan_job_id")
        emails_so_far = st.session_state.get("scan_emails", [])
        sources_done = st.session_state.get("scan_sources_done", [])
        complete = st.session_state.get("scan_complete", False)
        percent = st.session_state.get("scan_percent", 0)
        total_sources = st.session_state.get("scan_total_sources", 0)

        # ── Poll the job once per page load ──────────────────────────────────
        if job_id and not complete:
            try:
                poll = httpx.get(f"{_API}/api/v2/scan/{job_id}", timeout=5.0)
                if poll.status_code == 200:
                    data = poll.json()
                    st.session_state.scan_emails = data.get("emails", [])
                    st.session_state.scan_sources_done = data.get("sources_done", [])
                    if data.get("status") in ("complete", "cancelled"):
                        st.session_state.scan_complete = True
                        st.session_state.pop("scan_job_id", None)
                        _cached_emails.clear()
                        _cached_domains.clear()
                elif poll.status_code == 404:
                    # Job cleaned up — mark done
                    st.session_state.scan_complete = True
                    st.session_state.pop("scan_job_id", None)
            except Exception:
                pass

            emails_so_far = st.session_state.get("scan_emails", [])
            sources_done = st.session_state.get("scan_sources_done", [])
            complete = st.session_state.get("scan_complete", False)

        # ── Progress display ──────────────────────────────────────────────────
        n_emails = len(emails_so_far)

        col_stat, col_stop = st.columns([6, 1])
        with col_stat:
            if complete:
                st.markdown(
                    f'<div class="scan-counter">{n_emails} emails found</div>'
                    f'<div class="scan-domain">Scan complete · {domain}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="scan-counter">{n_emails} found so far…</div>'
                    f'<div class="scan-domain">Scanning {domain}</div>',
                    unsafe_allow_html=True,
                )

        if not complete and job_id:
            with col_stop:
                if st.button("Stop", key="stop_scan", type="secondary"):
                    try:
                        httpx.delete(f"{_API}/api/v2/scan/{job_id}", timeout=3.0)
                    except Exception:
                        pass
                    st.session_state.scan_complete = True
                    st.session_state.pop("scan_job_id", None)
                    st.rerun()

        # Progress bar
        if not complete:
            prog_pct = min(99, max(5, len(sources_done) * 14)) if sources_done else 5
            st.progress(prog_pct / 100)

        # Source pills
        all_sources = [
            "web_crawler",
            "whois",
            "github",
            "reddit",
            "search_engine",
            "intelligent_search",
            "theharvester",
            "spiderfoot",
        ]
        pills_html = ""
        for src in all_sources:
            if src in sources_done:
                pills_html += f'<span class="source-pill done">✓ {src}</span>'
            elif not complete:
                pills_html += f'<span class="source-pill active">⋯ {src}</span>'
        if pills_html:
            st.markdown(
                f'<div style="margin:0.6rem 0 1rem;">{pills_html}</div>',
                unsafe_allow_html=True,
            )

        # Email cards appearing live
        if emails_so_far:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            outreach = _load_outreach()
            for em in emails_so_far:
                addr = em.get("email", "")
                status = em.get("status", "unknown")
                conf = em.get("confidence", 0)
                src = em.get("source", "").split("/")[-1]
                tracked = outreach.get(addr, {}).get("status", "")
                extra_badge = f"&nbsp;{_badge_html(tracked)}" if tracked else ""

                st.markdown(
                    f'<div class="email-card fade-in">'
                    f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                    f'<span class="email-addr">{addr}</span>'
                    f"<span>{_badge_html(status)}{extra_badge}</span>"
                    f"</div>"
                    f'<div class="email-meta">'
                    f'<span class="source-pill">{src}</span>'
                    f'<span style="color:#9aa0c0;">{conf}% confidence</span>'
                    f"</div>"
                    f"{_conf_bar(conf)}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Auto-refresh while scanning
        if not complete and job_id:
            time.sleep(2)
            st.rerun()

        if complete and emails_so_far:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("View all contacts →", type="primary", use_container_width=True):
                st.session_state.page = "Contacts"
                st.rerun()
            if c2.button("Draft emails →", use_container_width=True):
                st.session_state.page = "Compose"
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CONTACTS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Contacts":
    st.markdown(
        '<div class="page-title">Contacts</div>'
        '<div class="page-subtitle">All discovered email addresses across your scanned domains.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("&nbsp;", unsafe_allow_html=True)

    contacts = _all_contacts()
    outreach = _load_outreach()

    if not contacts:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-state-icon">📭</div>'
            '<div class="empty-state-title">No contacts yet</div>'
            '<div class="empty-state-sub">Scan a domain in the Find tab to discover emails.</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Go to Find Emails", type="primary"):
            st.session_state.page = "Find Emails"
            st.rerun()
    else:
        # Filter bar
        filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 3])
        domains_avail = sorted({c["domain"] for c in contacts})
        selected_domain = filter_col1.selectbox(
            "Domain", ["All"] + domains_avail, label_visibility="collapsed"
        )
        status_filter = filter_col2.selectbox(
            "Status",
            ["All", "Valid", "Unknown", "Catch-all", "Invalid"],
            label_visibility="collapsed",
        )
        search = filter_col3.text_input(
            "Search", placeholder="Search emails…", label_visibility="collapsed"
        )

        # Apply filters
        filtered = contacts
        if selected_domain != "All":
            filtered = [c for c in filtered if c["domain"] == selected_domain]
        if status_filter != "All":
            map_s = {
                "Valid": "valid",
                "Unknown": "unknown",
                "Catch-all": "catch_all",
                "Invalid": "invalid",
            }
            filtered = [c for c in filtered if c.get("status") == map_s[status_filter]]
        if search:
            filtered = [c for c in filtered if search.lower() in c.get("email", "").lower()]

        st.caption(f"{len(filtered)} contacts")
        st.markdown("&nbsp;", unsafe_allow_html=True)

        # Card grid (2 per row)
        for i in range(0, len(filtered), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j >= len(filtered):
                    break
                em = filtered[i + j]
                addr = em.get("email", "")
                status = em.get("status", "unknown")
                conf = em.get("confidence", 0)
                src = em.get("source", "").split("/")[-1]
                domain = em.get("domain", "")
                tracked_status = outreach.get(addr, {}).get("status", "")
                tracked_badge = f"&nbsp;{_badge_html(tracked_status)}" if tracked_status else ""

                with col:
                    st.markdown(
                        f'<div class="email-card">'
                        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;">'
                        f"<div>"
                        f'<div class="email-addr">{addr}</div>'
                        f'<div class="email-meta" style="margin-top:0.3rem;">'
                        f'<span class="source-pill">{src}</span>'
                        f'<span style="color:#9aa0c0;">{domain}</span>'
                        f"</div>"
                        f"</div>"
                        f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.25rem;">'
                        f"{_badge_html(status)}{tracked_badge}"
                        f'<span style="font-size:0.75rem;color:#6b7099;">{conf}%</span>'
                        f"</div>"
                        f"</div>"
                        f"{_conf_bar(conf)}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    idx = i + j  # unique across the full filtered list
                    btn_col1, btn_col2 = col.columns(2)
                    if btn_col1.button(
                        "✏️ Draft", key=f"draft_{idx}_{addr[:20]}", use_container_width=True, type="secondary"
                    ):
                        st.session_state.compose_email = addr
                        st.session_state.compose_domain = domain
                        st.session_state.page = "Compose"
                        st.rerun()
                    if btn_col2.button(
                        "📤 Sent" if tracked_status != "sent" else "💬 Replied",
                        key=f"mark_{idx}_{addr[:20]}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        new_status = "sent" if tracked_status != "sent" else "replied"
                        outreach[addr] = {
                            **outreach.get(addr, {}),
                            "status": new_status,
                            "domain": domain,
                            f"{new_status}_at": datetime.now().isoformat(),
                        }
                        _save_outreach(outreach)
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: COMPOSE
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Compose":
    st.markdown(
        '<div class="page-title">Compose</div>'
        '<div class="page-subtitle">Groq writes a personalised cold email. You review and copy.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("&nbsp;", unsafe_allow_html=True)

    if not api_online:
        st.warning("API server offline — start `coldreach serve` to generate drafts.", icon="⚠️")
        st.stop()

    # Pre-fill from contacts click
    prefill_email = st.session_state.pop("compose_email", "")
    prefill_domain = st.session_state.pop("compose_domain", "")

    left, right = st.columns([2, 3])

    with left:
        st.markdown("#### Your details")
        your_name = st.text_input(
            "Your name",
            value=st.session_state.get("compose_name", ""),
            placeholder="Jane Smith",
        )
        if your_name:
            st.session_state.compose_name = your_name

        st.markdown("#### Their details")
        to_email = st.text_input(
            "Recipient email", value=prefill_email, placeholder="ceo@company.com"
        )
        to_domain = st.text_input("Company domain", value=prefill_domain, placeholder="company.com")

        intent = st.text_area(
            "What do you want?",
            placeholder="Explore a partnership on B2B payments for SMBs in India.",
            height=90,
            max_chars=200,
        )

        email_type = st.selectbox(
            "Email type",
            ["auto", "partnership", "job_application", "sales", "introduction"],
            format_func=lambda x: {
                "auto": "🤖 Auto-detect",
                "partnership": "🤝 Partnership",
                "job_application": "💼 Job application",
                "sales": "💰 Sales outreach",
                "introduction": "👋 Introduction",
            }[x],
        )

        generate = st.button(
            "✨ Generate draft",
            type="primary",
            use_container_width=True,
            disabled=not all([your_name, to_email, to_domain, intent]),
        )

    with right:
        st.markdown("#### Draft")

        if generate:
            with st.spinner("Fetching company context…"):
                # Call the draft API
                result = None
                error = None
                try:
                    with httpx.stream(
                        "POST",
                        f"{_API}/api/v2/draft",
                        json={
                            "email": to_email,
                            "domain": to_domain,
                            "sender_name": your_name,
                            "sender_intent": intent,
                            "email_type": email_type,
                        },
                        timeout=60.0,
                    ) as resp:
                        for line in resp.iter_lines():
                            if line.startswith("data:"):
                                try:
                                    payload = json.loads(line[5:].strip())
                                    if "subject" in payload and "body" in payload:
                                        result = payload
                                    elif "detail" in payload:
                                        error = payload["detail"]
                                except Exception:
                                    pass
                except Exception as exc:
                    error = str(exc)

            if error:
                st.error(f"Could not generate draft: {error}")
                if "groq" in error.lower() or "api key" in error.lower():
                    st.info(
                        "Add `COLDREACH_GROQ_API_KEY=gsk_xxx` to `.env` and restart the server."
                    )
            elif result:
                st.session_state.last_draft = result
                st.session_state.last_draft_meta = {
                    "to": to_email,
                    "domain": to_domain,
                    "sender": your_name,
                    "intent": intent,
                }

        draft = st.session_state.get("last_draft")
        meta = st.session_state.get("last_draft_meta", {})

        if draft:
            st.markdown(
                f'<div class="draft-box">'
                f'<div class="draft-subject">Subject</div>'
                f'<div style="font-weight:600;color:#e0e4f7;margin-bottom:1rem;">{draft["subject"]}</div>'
                f'<div style="white-space:pre-wrap;">{draft["body"]}</div>'
                f'<div style="margin-top:1rem;color:#6b7099;">Best,<br>{meta.get("sender", "")}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("&nbsp;", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            full_text = (
                f"Subject: {draft['subject']}\n\n{draft['body']}\n\nBest,\n{meta.get('sender', '')}"
            )

            if c1.button("📋 Copy to clipboard", use_container_width=True, type="primary"):
                st.code(full_text, language=None)
                st.success("Draft shown above — select all and copy (Ctrl+A, Ctrl+C)")

            if c2.button("💾 Save draft", use_container_width=True):
                drafts = _load_drafts()
                drafts.append(
                    {
                        "to": meta.get("to"),
                        "subject": draft["subject"],
                        "body": draft["body"],
                        "sender": meta.get("sender"),
                        "domain": meta.get("domain"),
                        "created_at": datetime.now().isoformat(),
                    }
                )
                _save_json(_DRAFTS, drafts)
                st.success("Draft saved!")

        else:
            st.markdown(
                '<div class="empty-state" style="padding:2rem;">'
                '<div class="empty-state-icon">✉️</div>'
                '<div class="empty-state-title">Fill in the form and hit Generate</div>'
                '<div class="empty-state-sub">Groq reads the company website and writes a personalised email in seconds.</div>'
                "</div>",
                unsafe_allow_html=True,
            )

    # Saved drafts
    drafts = _load_drafts()
    if drafts:
        st.markdown("---")
        st.markdown("#### Saved drafts")
        for i, d in enumerate(reversed(drafts[-5:])):
            with st.expander(f"✉️ {d.get('to', '?')} — {d.get('subject', '')[:55]}"):
                st.markdown(
                    f'<div class="draft-box">{d.get("body", "")}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(f"Saved {d.get('created_at', '')[:19]}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SENT
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Sent":
    st.markdown(
        '<div class="page-title">Outreach Tracker</div>'
        '<div class="page-subtitle">Track replies and manage your sent emails.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("&nbsp;", unsafe_allow_html=True)

    outreach = _load_outreach()

    if not outreach:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-state-icon">📤</div>'
            '<div class="empty-state-title">Nothing sent yet</div>'
            '<div class="empty-state-sub">Mark emails as sent from the Contacts page.</div>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        sent_count = sum(1 for v in outreach.values() if v.get("status") == "sent")
        replied_count = sum(1 for v in outreach.values() if v.get("status") == "replied")
        reply_rate = f"{int(replied_count / max(sent_count, 1) * 100)}%" if sent_count else "—"

        cols = st.columns(3)
        for col, (label, value) in zip(
            cols,
            [("Sent", sent_count), ("Replied", replied_count), ("Reply rate", reply_rate)],
        ):
            col.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("&nbsp;", unsafe_allow_html=True)

        for addr, info in sorted(
            outreach.items(), key=lambda x: x[1].get("sent_at", ""), reverse=True
        ):
            status = info.get("status", "sent")
            domain = info.get("domain", "")
            sent_at = info.get("sent_at", "")[:10]
            replied_at = info.get("replied_at", "")[:10]

            col_a, col_b, col_c, col_d = st.columns([3, 2, 2, 1])
            col_a.markdown(
                f'<span class="email-addr" style="font-size:0.85rem;">{addr}</span>'
                f'<br><span style="font-size:0.75rem;color:#6b7099;">{domain}</span>',
                unsafe_allow_html=True,
            )
            col_b.markdown(_badge_html(status), unsafe_allow_html=True)
            col_c.markdown(
                f'<span style="font-size:0.8rem;color:#9aa0c0;">Sent {sent_at}</span>'
                + (
                    f'<br><span style="font-size:0.75rem;color:#34d399;">Replied {replied_at}</span>'
                    if replied_at
                    else ""
                ),
                unsafe_allow_html=True,
            )
            if col_d.button(
                "Mark replied" if status == "sent" else "✓", key=f"rep_{addr}", type="secondary"
            ):
                outreach[addr] = {
                    **info,
                    "status": "replied",
                    "replied_at": datetime.now().isoformat(),
                }
                _save_outreach(outreach)
                st.rerun()
