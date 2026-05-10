"""Tests for OutreachTracker — SQLite-backed outreach contact tracker."""

from __future__ import annotations

import pytest

from coldreach.outreach.tracker import OutreachTracker


@pytest.fixture
def tracker(tmp_path):
    """OutreachTracker backed by a temp SQLite file."""
    db = str(tmp_path / "test_cache.db")
    return OutreachTracker(db_path=db)


class TestOutreachTracker:
    def test_upsert_new_contact(self, tracker):
        tracker.upsert("test@stripe.com", "stripe.com")
        contacts = tracker.list_contacts()
        assert len(contacts) == 1
        assert contacts[0].email == "test@stripe.com"
        assert contacts[0].status == "new"

    def test_upsert_idempotent(self, tracker):
        tracker.upsert("test@stripe.com", "stripe.com")
        tracker.upsert("test@stripe.com", "stripe.com")
        assert len(tracker.list_contacts()) == 1

    def test_save_draft(self, tracker):
        tracker.save_draft("test@stripe.com", "stripe.com", "Subject A", "Body text", "partnership")
        c = tracker.list_contacts()[0]
        assert c.status == "draft"
        assert c.subject == "Subject A"
        assert c.body == "Body text"
        assert c.email_type == "partnership"

    def test_mark_sent(self, tracker):
        tracker.upsert("test@stripe.com", "stripe.com")
        tracker.mark_sent("test@stripe.com")
        c = tracker.list_contacts()[0]
        assert c.status == "sent"
        assert c.sent_at is not None

    def test_mark_replied(self, tracker):
        tracker.upsert("test@stripe.com", "stripe.com")
        tracker.mark_replied("test@stripe.com")
        c = tracker.list_contacts()[0]
        assert c.status == "replied"
        assert c.replied_at is not None

    def test_remove(self, tracker):
        tracker.upsert("test@stripe.com", "stripe.com")
        tracker.remove("test@stripe.com")
        assert tracker.list_contacts() == []

    def test_stats(self, tracker):
        tracker.save_draft("a@x.com", "x.com", "S", "B", "sales")
        tracker.upsert("b@x.com", "x.com")
        tracker.mark_sent("b@x.com")
        tracker.upsert("c@x.com", "x.com")
        tracker.mark_replied("c@x.com")
        s = tracker.stats()
        assert s["total"] == 3
        assert s["draft"] == 1
        assert s["sent"] == 1
        assert s["replied"] == 1

    def test_email_normalized_lowercase(self, tracker):
        tracker.upsert("Test@Stripe.COM", "stripe.com")
        contacts = tracker.list_contacts()
        assert contacts[0].email == "test@stripe.com"

    def test_multiple_contacts_ordered_newest_first(self, tracker):
        tracker.upsert("a@x.com", "x.com")
        tracker.upsert("b@x.com", "x.com")
        contacts = tracker.list_contacts()
        assert contacts[0].email == "b@x.com"
        assert contacts[1].email == "a@x.com"
