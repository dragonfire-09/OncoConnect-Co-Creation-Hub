"""
OncoConnect — Supabase Data Layer
All database operations in one place.
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime


# ─────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    """Create and cache Supabase client."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def sb() -> Client:
    """Shortcut to get Supabase client."""
    return get_supabase()


# ─────────────────────────────────────────────
# APPROVALS
# ─────────────────────────────────────────────
def get_approvals() -> dict:
    """
    Returns: {"Turkey": True/False, "Poland": ..., "Spain": ...}
    """
    res = sb().table("approvals").select("country, approved").execute()
    return {row["country"]: row["approved"] for row in res.data}


def set_approval(country: str, approved: bool, performed_by: str, role: str):
    """Approve or revoke a country's approval."""
    now = datetime.utcnow().isoformat()

    # Update approval
    update_data = {
        "approved": approved,
        "approved_by": performed_by if approved else None,
        "approved_at": now if approved else None,
        "updated_at": now,
    }
    sb().table("approvals").update(update_data).eq("country", country).execute()

    # Log the action
    sb().table("approval_log").insert(
        {
            "action": "approved" if approved else "revoked",
            "country": country,
            "performed_by": performed_by,
            "role": role,
        }
    ).execute()


def get_approval_log() -> list:
    """Get full approval history."""
    res = (
        sb()
        .table("approval_log")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


# ─────────────────────────────────────────────
# PARTNER FEEDBACK
# ─────────────────────────────────────────────
def get_partner_feedback() -> list:
    """Get all partner feedback, newest first."""
    res = (
        sb()
        .table("partner_feedback")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def add_partner_feedback(
    partner_country: str,
    organisation: str,
    section: str,
    feedback: str,
    priority: str,
    submitted_by: str,
):
    """Insert new partner feedback."""
    sb().table("partner_feedback").insert(
        {
            "partner_country": partner_country,
            "organisation": organisation,
            "section": section,
            "feedback": feedback,
            "priority": priority,
            "status": "Open",
            "submitted_by": submitted_by,
        }
    ).execute()


def update_feedback_status(feedback_id: int, new_status: str, response: str = None):
    """Update feedback status (Admin feature)."""
    data = {"status": new_status}
    if response:
        data["response"] = response
    sb().table("partner_feedback").update(data).eq("id", feedback_id).execute()


# ─────────────────────────────────────────────
# PATIENT FEEDBACK
# ─────────────────────────────────────────────
def get_patient_feedback() -> list:
    """Get all patient feedback."""
    res = (
        sb()
        .table("patient_feedback")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def add_patient_feedback(data: dict):
    """Insert new patient feedback."""
    sb().table("patient_feedback").insert(data).execute()


# ─────────────────────────────────────────────
# ANNOUNCEMENTS
# ─────────────────────────────────────────────
def get_announcements() -> list:
    """Get all announcements, newest first."""
    res = (
        sb()
        .table("announcements")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def add_announcement(title: str, content: str, author: str, priority: str):
    """Insert new announcement."""
    sb().table("announcements").insert(
        {
            "title": title,
            "content": content,
            "author": author,
            "priority": priority,
        }
    ).execute()


# ─────────────────────────────────────────────
# STATS (for dashboard)
# ─────────────────────────────────────────────
def get_stats() -> dict:
    """Get counts for dashboard metrics."""
    approvals = get_approvals()
    fb = sb().table("partner_feedback").select("id", count="exact").execute()
    pf = sb().table("patient_feedback").select("id", count="exact").execute()
    ann = sb().table("announcements").select("id", count="exact").execute()

    return {
        "approvals": approvals,
        "approved_count": sum(1 for v in approvals.values() if v),
        "feedback_count": fb.count if fb.count else 0,
        "patient_feedback_count": pf.count if pf.count else 0,
        "announcement_count": ann.count if ann.count else 0,
    }
