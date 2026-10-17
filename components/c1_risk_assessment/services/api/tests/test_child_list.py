"""Tests for children monitoring worklist helpers."""

from datetime import date
from types import SimpleNamespace

from app.models.enums import FollowUpStatus
from app.services.child_list import (
    follow_up_context,
    list_summary,
    progress_display,
    requires_clinical_attention,
)


def test_progress_display_insufficient_for_single_visit():
    assert progress_display("baseline", 1, True) == "insufficient_history"
    assert progress_display(None, 0, False) == "not_available"


def test_follow_up_overdue_days():
    follow = SimpleNamespace(expected_date=date(2026, 1, 1), status=FollowUpStatus.SCHEDULED)
    expected, status, days = follow_up_context(follow, date(2026, 2, 22))
    assert status == "overdue"
    assert days == 52


def test_summary_counts_unique_children():
    items = [
        {"requires_attention": True, "clinician_review_status": "AWAITING_REVIEW", "follow_up_display_status": "scheduled"},
        {"requires_attention": False, "clinician_review_status": "REVIEWED", "follow_up_display_status": "overdue"},
        {"requires_attention": True, "clinician_review_status": "IN_REVIEW", "follow_up_display_status": "scheduled"},
    ]
    s = list_summary(items)
    assert s["children_under_monitoring"] == 3
    assert s["requiring_clinical_attention"] == 2
    assert s["awaiting_clinical_review"] == 2
    assert s["follow_up_upcoming"] == 2
    assert s["follow_up_overdue"] == 1


def test_requires_attention_from_review_and_progress():
    assert requires_clinical_attention({"clinician_review_status": "AWAITING_REVIEW", "clinical_attention": []})
    assert requires_clinical_attention({"progress_display": "deteriorating", "clinical_attention": []})
    assert not requires_clinical_attention({"progress_display": "improving", "clinical_attention": [], "clinician_review_status": "REVIEWED"})
