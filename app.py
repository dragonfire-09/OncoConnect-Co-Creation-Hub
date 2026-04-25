"""
OncoConnect Co-Creation Hub
Erasmus+ KA210 Small-Scale Partnership
AI-Integrated Proposal Governance Platform
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════
st.set_page_config(
    page_title="OncoConnect Co-Creation Hub",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════
# SUPABASE CONNECTION
# ═══════════════════════════════════════════════════
SUPABASE_OK = False
try:
    from supabase import create_client, Client

    @st.cache_resource
    def get_supabase() -> Client:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)

    _client = get_supabase()
    SUPABASE_OK = True
except Exception as e:
    SUPABASE_OK = False


def sb():
    if SUPABASE_OK:
        return get_supabase()
    return None


# ═══════════════════════════════════════════════════
# OPENAI CONNECTION
# ═══════════════════════════════════════════════════
AI_ENABLED = False
try:
    import openai
    ai_key = st.secrets.get("openai", {}).get("api_key", "")
    if ai_key:
        openai_client = openai.OpenAI(api_key=ai_key)
        AI_ENABLED = True
except Exception:
    AI_ENABLED = False


# ═══════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════
SUBMISSION_DEADLINE = datetime(2027, 5, 15, 17, 0, 0)
PREPARATION_START = datetime(2025, 6, 5)
PROJECT_START = datetime(2025, 9, 1)
TOTAL_BUDGET = 60000

PARTNER_MAP = {
    "Turkey": "Kanser Savaşçıları Derneği",
    "Poland": "Fundacja Onkologiczna Rakiety",
    "Spain": "Universitat de Barcelona",
}
FLAGS = {"Turkey": "🇹🇷", "Poland": "🇵🇱", "Spain": "🇪🇸"}
ROLE_BADGES = {"Admin": "🛡️ Admin", "Partner": "🤝 Partner", "Patient": "💚 Patient"}

USERS_DB = {
    "admin": {"password": "admin123", "name": "Project Admin", "role": "Admin", "country": "All", "org": "OncoConnect"},
    "turkey": {"password": "tr2025", "name": "KSD Coordinator", "role": "Partner", "country": "Turkey", "org": "Kanser Savaşçıları Derneği"},
    "poland": {"password": "pl2025", "name": "Rakiety Team", "role": "Partner", "country": "Poland", "org": "Fundacja Onkologiczna Rakiety"},
    "spain": {"password": "es2025", "name": "UB Research Team", "role": "Partner", "country": "Spain", "org": "Universitat de Barcelona"},
    "patient": {"password": "patient123", "name": "Patient Participant", "role": "Patient", "country": "N/A", "org": "N/A"},
}

PROPOSAL_SECTIONS = [
    "Needs Analysis", "Objectives", "Methodology", "Work Packages",
    "Impact", "Dissemination", "Budget", "Ethics/Data Protection", "Consortium",
]


# ═══════════════════════════════════════════════════
# DB FUNCTIONS — APPROVALS
# ═══════════════════════════════════════════════════
def db_get_approvals() -> dict:
    default = {"Turkey": False, "Poland": False, "Spain": False}
    if not SUPABASE_OK:
        return st.session_state.get("local_approvals", default)
    try:
        res = sb().table("approvals").select("country, approved").execute()
        return {row["country"]: row["approved"] for row in res.data}
    except Exception:
        return default


def db_set_approval(country_name, approved, performed_by, user_role):
    now_str = datetime.utcnow().isoformat()
    if not SUPABASE_OK:
        if "local_approvals" not in st.session_state:
            st.session_state["local_approvals"] = {"Turkey": False, "Poland": False, "Spain": False}
        st.session_state["local_approvals"][country_name] = approved
        return
    try:
        sb().table("approvals").update({
            "approved": approved,
            "approved_by": performed_by if approved else None,
            "approved_at": now_str if approved else None,
            "updated_at": now_str,
        }).eq("country", country_name).execute()
        sb().table("approval_log").insert({
            "action": "approved" if approved else "revoked",
            "country": country_name,
            "performed_by": performed_by,
            "role": user_role,
        }).execute()
    except Exception as e:
        st.error(f"DB Error: {e}")


def db_get_approval_log():
    if not SUPABASE_OK:
        return []
    try:
        return sb().table("approval_log").select("*").order("created_at", desc=True).execute().data
    except Exception:
        return []


# ═══════════════════════════════════════════════════
# DB FUNCTIONS — PARTNER FEEDBACK
# ═══════════════════════════════════════════════════
def db_get_partner_feedback():
    if not SUPABASE_OK:
        return st.session_state.get("local_feedback", [])
    try:
        return sb().table("partner_feedback").select("*").order("created_at", desc=True).execute().data
    except Exception:
        return []


def db_add_partner_feedback(p_country, org, section, feedback, priority, submitted_by):
    if not SUPABASE_OK:
        if "local_feedback" not in st.session_state:
            st.session_state["local_feedback"] = []
        st.session_state["local_feedback"].append({
            "id": len(st.session_state["local_feedback"]) + 1,
            "partner_country": p_country, "organisation": org,
            "section": section, "feedback": feedback,
            "priority": priority, "status": "Open",
            "submitted_by": submitted_by,
            "created_at": datetime.now().isoformat(),
        })
        return
    try:
        sb().table("partner_feedback").insert({
            "partner_country": p_country, "organisation": org,
            "section": section, "feedback": feedback,
            "priority": priority, "status": "Open",
            "submitted_by": submitted_by,
        }).execute()
    except Exception as e:
        st.error(f"DB Error: {e}")


def db_update_feedback_status(fb_id, new_status, response=None):
    if not SUPABASE_OK:
        return
    try:
        data = {"status": new_status}
        if response:
            data["response"] = response
        sb().table("partner_feedback").update(data).eq("id", fb_id).execute()
    except Exception as e:
        st.error(f"DB Error: {e}")


# ═══════════════════════════════════════════════════
# DB FUNCTIONS — PATIENT FEEDBACK
# ═══════════════════════════════════════════════════
def db_get_patient_feedback():
    if not SUPABASE_OK:
        return st.session_state.get("local_patient_fb", [])
    try:
        return sb().table("patient_feedback").select("*").order("created_at", desc=True).execute().data
    except Exception:
        return []


def db_add_patient_feedback(data):
    if not SUPABASE_OK:
        if "local_patient_fb" not in st.session_state:
            st.session_state["local_patient_fb"] = []
        data["id"] = len(st.session_state["local_patient_fb"]) + 1
        data["created_at"] = datetime.now().isoformat()
        st.session_state["local_patient_fb"].append(data)
        return
    try:
        sb().table("patient_feedback").insert(data).execute()
    except Exception as e:
        st.error(f"DB Error: {e}")


# ═══════════════════════════════════════════════════
# DB FUNCTIONS — ANNOUNCEMENTS
# ═══════════════════════════════════════════════════
def db_get_announcements():
    if not SUPABASE_OK:
        return st.session_state.get("local_announcements", [])
    try:
        return sb().table("announcements").select("*").order("created_at", desc=True).execute().data
    except Exception:
        return []


def db_add_announcement(title, content, author, priority):
    if not SUPABASE_OK:
        if "local_announcements" not in st.session_state:
            st.session_state["local_announcements"] = []
        st.session_state["local_announcements"].append({
            "id": len(st.session_state["local_announcements"]) + 1,
            "title": title, "content": content,
            "author": author, "priority": priority,
            "created_at": datetime.now().isoformat(),
        })
        return
    try:
        sb().table("announcements").insert({
            "title": title, "content": content,
            "author": author, "priority": priority,
        }).execute()
    except Exception as e:
        st.error(f"DB Error: {e}")


# ═══════════════════════════════════════════════════
# DB FUNCTIONS — AI / IMPROVEMENT LOG
# ═══════════════════════════════════════════════════
def db_log_improvement(feedback_id, section, original, updated, reasoning, action, created_by):
    if not SUPABASE_OK:
        if "local_improvement_log" not in st.session_state:
            st.session_state["local_improvement_log"] = []
        st.session_state["local_improvement_log"].append({
            "id": len(st.session_state["local_improvement_log"]) + 1,
            "feedback_id": feedback_id, "section": section,
            "original_text": original, "updated_text": updated,
            "ai_reasoning": reasoning, "action": action,
            "created_by": created_by,
            "created_at": datetime.now().isoformat(),
        })
        return
    try:
        sb().table("improvement_log").insert({
            "feedback_id": feedback_id, "section": section,
            "original_text": original, "updated_text": updated,
            "ai_reasoning": reasoning, "action": action,
            "created_by": created_by,
        }).execute()
    except Exception as e:
        st.error(f"Log error: {e}")


def db_get_improvement_log():
    if not SUPABASE_OK:
        return st.session_state.get("local_improvement_log", [])
    try:
        return sb().table("improvement_log").select("*").order("created_at", desc=True).execute().data
    except Exception:
        return []


def db_log_ai_decision(feedback_id, decision, confidence, reasoning, target_section):
    if not SUPABASE_OK:
        if "local_ai_decisions" not in st.session_state:
            st.session_state["local_ai_decisions"] = []
        st.session_state["local_ai_decisions"].append({
            "id": len(st.session_state["local_ai_decisions"]) + 1,
            "feedback_id": feedback_id, "decision": decision,
            "confidence": confidence, "reasoning": reasoning,
            "target_section": target_section,
            "created_at": datetime.now().isoformat(),
        })
        return
    try:
        sb().table("ai_decisions").insert({
            "feedback_id": feedback_id, "decision": decision,
            "confidence": confidence, "reasoning": reasoning,
            "target_section": target_section,
        }).execute()
    except Exception as e:
        st.error(f"AI log error: {e}")


def db_get_ai_decisions():
    if not SUPABASE_OK:
        return st.session_state.get("local_ai_decisions", [])
    try:
        return sb().table("ai_decisions").select("*").order("created_at", desc=True).execute().data
    except Exception:
        return []


# ═══════════════════════════════════════════════════
# AI ENGINE
# ═══════════════════════════════════════════════════
def ai_analyze_feedback(feedback_text, section):
    if not AI_ENABLED:
        return {
            "decision": "manual_review",
            "confidence": 0,
            "reasoning": "AI not configured. Manual review required.",
            "target_section": section,
            "suggested_action": "review",
            "priority": "medium",
        }
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an Erasmus+ KA210 proposal quality analyst for the OncoConnect project.
OncoConnect develops a structured peer mentorship system for cancer patients across Turkey, Poland, and Spain.

Analyze the partner/patient feedback and return a JSON response with:
- decision: "integrate" | "archive" | "route" | "reject"
  - integrate: feedback is relevant and should be incorporated into the proposal
  - archive: interesting but not relevant for current proposal, save for future
  - route: feedback belongs to a different section/WP
  - reject: feedback is off-topic or not actionable
- confidence: 0.0 to 1.0
- reasoning: brief explanation (1-2 sentences)
- target_section: which proposal section this feedback affects most
- suggested_action: specific action to take
- priority: "high" | "medium" | "low"
- affected_wp: which work package is most affected (WP1-WP5)

Project WPs:
WP1=Management & Coordination (Turkey)
WP2=Needs Analysis & Co-Creation (Poland)
WP3=Matching System & Training Development (Spain)
WP4=Pilot Implementation (Turkey)
WP5=Evaluation, Dissemination & Sustainability (Spain+Poland)"""
                },
                {
                    "role": "user",
                    "content": f"Section: {section}\nFeedback: {feedback_text}"
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=500,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "decision": "manual_review",
            "confidence": 0,
            "reasoning": f"AI error: {str(e)}",
            "target_section": section,
            "suggested_action": "review",
            "priority": "medium",
        }


def ai_suggest_update(section, feedback_text, current_text):
    if not AI_ENABLED:
        return "AI not configured. Please update manually."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert Erasmus+ KA210 proposal writer for the OncoConnect project.
Given the current section text and partner feedback, write an improved version of the section.
Keep academic tone. Be specific and actionable. Output only the improved text.
The project is about structured peer mentorship for cancer patients (Turkey, Poland, Spain)."""
                },
                {
                    "role": "user",
                    "content": f"SECTION: {section}\n\nCURRENT TEXT:\n{current_text}\n\nFEEDBACK TO INCORPORATE:\n{feedback_text}\n\nWrite the improved version:"
                }
            ],
            temperature=0.4,
            max_tokens=1500,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI error: {str(e)}"


def ai_generate_summary(feedback_list):
    if not AI_ENABLED or not feedback_list:
        return "AI not available or no feedback to summarize."
    try:
        fb_text = "\n".join([f"- [{f.get('section', '')}] {f.get('feedback', '')}" for f in feedback_list[:20]])
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the key themes and actionable insights from these partner feedback items for an Erasmus+ KA210 project. Be concise and structured."
                },
                {"role": "user", "content": fb_text}
            ],
            temperature=0.3,
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI error: {str(e)}"


# ═══════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════
@st.cache_data
def load_csv(path):
    return pd.read_csv(path)


def load_static():
    return load_csv("data/work_packages.csv"), load_csv("data/partners.csv")


# ═══════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════
def render_login():
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        "<div style='text-align:center;padding:3rem 0 1rem;'>"
        "<h1>🧬 OncoConnect</h1>"
        "<h3 style='color:#555;font-weight:400;'>Co-Creation Hub</h3>"
        "<p style='color:#777;'>Erasmus+ KA210 — AI-Driven Proposal Governance Platform</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login"):
            username = st.text_input("Username", placeholder="admin / turkey / poland / spain / patient")
            password = st.text_input("Password", type="password")
            go = st.form_submit_button("Login", use_container_width=True, type="primary")
            if go:
                u = USERS_DB.get(username)
                if u and u["password"] == password:
                    st.session_state.update(
                        authenticated=True, username=username,
                        user_name=u["name"], user_role=u["role"],
                        user_country=u["country"], user_org=u["org"],
                    )
                    st.rerun()
                else:
                    st.error("Invalid credentials")

        with st.expander("Demo Credentials"):
            st.markdown(
                "| User | Pass | Role |\n|---|---|---|\n"
                "| admin | admin123 | Admin |\n"
                "| turkey | tr2025 | Partner TR |\n"
                "| poland | pl2025 | Partner PL |\n"
                "| spain | es2025 | Partner ES |\n"
                "| patient | patient123 | Patient |"
            )
    return False


def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


def get_role():
    return st.session_state.get("user_role", "Patient")

def get_country():
    return st.session_state.get("user_country", "N/A")

def get_name():
    return st.session_state.get("user_name", "User")

def get_org():
    return st.session_state.get("user_org", "N/A")


# ═══════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════
def render_countdown():
    now = datetime.now()
    prep_total = (SUBMISSION_DEADLINE - PREPARATION_START).days
    prep_elapsed = (now - PREPARATION_START).days
    prep_progress = max(0.0, min(1.0, prep_elapsed / max(prep_total, 1)))
    rem = SUBMISSION_DEADLINE - now
    if rem.total_seconds() <= 0:
        st.error("SUBMISSION DEADLINE PASSED!")
        return
    days = rem.days
    hours, rem2 = divmod(rem.seconds, 3600)
    minutes, _ = divmod(rem2, 60)

    if days > 365:
        sub_color = "#17a2b8"
    elif days > 180:
        sub_color = "#28a745"
    elif days > 60:
        sub_color = "#ffc107"
    else:
        sub_color = "#dc3545"

    pct = int(prep_progress * 100)
    deg = int(prep_progress * 360)
    prep_color = "#a855f7" if prep_progress < 0.5 else "#f59e0b" if prep_progress < 0.8 else "#ef4444"

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#1a1a2e,#2d1b4e);"
            f"border-radius:16px;padding:1.5rem;text-align:center;color:white;min-height:280px;'>"
            f"<p style='margin:0;font-size:.75rem;opacity:.7;letter-spacing:2px;'>PREPARATION PHASE</p>"
            f"<p style='margin:.3rem 0 0;font-size:.85rem;opacity:.8;'>Co-creation and proposal development</p>"
            f"<div style='margin:1rem auto;width:120px;height:120px;border-radius:50%;"
            f"background:conic-gradient({prep_color} {deg}deg, #333 0deg);"
            f"display:flex;align-items:center;justify-content:center;'>"
            f"<div style='width:100px;height:100px;border-radius:50%;background:#1a1a2e;"
            f"display:flex;align-items:center;justify-content:center;flex-direction:column;'>"
            f"<span style='font-size:1.8rem;font-weight:bold;color:{prep_color};'>{pct}%</span>"
            f"<span style='font-size:.65rem;opacity:.6;'>COMPLETE</span></div></div>"
            f"<p style='margin:0;font-size:.8rem;opacity:.6;'>"
            f"Started: {PREPARATION_START.strftime('%d %b %Y')} | Elapsed: {prep_elapsed} days</p></div>",
            unsafe_allow_html=True,
        )
    with col_right:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);"
            f"border-radius:16px;padding:1.5rem;text-align:center;color:white;min-height:280px;'>"
            f"<p style='margin:0;font-size:.75rem;opacity:.7;letter-spacing:2px;'>SUBMISSION DEADLINE</p>"
            f"<p style='margin:.3rem 0 0;font-size:.85rem;opacity:.8;'>"
            f"{SUBMISSION_DEADLINE.strftime('%d %B %Y, %H:%M')}</p>"
            f"<div style='display:flex;justify-content:center;gap:1.5rem;margin:1.2rem 0;'>"
            f"<div><span style='font-size:2.8rem;font-weight:bold;color:{sub_color};'>{days}</span>"
            f"<br><span style='font-size:.75rem;opacity:.6;'>DAYS</span></div>"
            f"<div><span style='font-size:2.8rem;font-weight:bold;color:{sub_color};'>{hours:02d}</span>"
            f"<br><span style='font-size:.75rem;opacity:.6;'>HOURS</span></div>"
            f"<div><span style='font-size:2.8rem;font-weight:bold;color:{sub_color};'>{minutes:02d}</span>"
            f"<br><span style='font-size:.75rem;opacity:.6;'>MIN</span></div></div>"
            f"<p style='margin:0;font-size:.8rem;opacity:.6;'>Erasmus+ KA210 Expected Call 2027</p></div>",
            unsafe_allow_html=True,
        )
    sub_progress = max(0.0, min(1.0, 1 - days / max(prep_total, 1)))
    st.progress(sub_progress)


def ann_card(row):
    p = row.get("priority", "Low")
    icon = {"High": "🔴", "Medium": "🟡"}.get(p, "🟢")
    border = {"High": "#dc3545", "Medium": "#ffc107"}.get(p, "#28a745")
    date = str(row.get("created_at", ""))[:10]
    st.markdown(
        f"<div style='border-left:4px solid {border};padding:1rem;"
        f"margin-bottom:.7rem;background:#f8f9fa;border-radius:0 8px 8px 0;'>"
        f"<strong>{icon} {row['title']}</strong>"
        f"<span style='float:right;color:#666;font-size:.85rem;'>{date}</span>"
        f"<br><span style='color:#444;'>{row['content']}</span>"
        f"<br><span style='font-size:.8rem;color:#999;'>By: {row.get('author','')}</span></div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════
def page_dashboard(wp_df, partners_df):
    st.title("🧬 OncoConnect Co-Creation Hub")
    st.caption("Erasmus+ KA210 — AI-Driven Proposal Governance Platform")
    render_countdown()

    approvals = db_get_approvals()
    fb_count = len(db_get_partner_feedback())
    ai_count = len(db_get_ai_decisions())
    approved_n = sum(1 for v in approvals.values() if v)
    remaining_days = (SUBMISSION_DEADLINE - datetime.now()).days

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Work Packages", len(wp_df))
    c2.metric("Partners", len(partners_df))
    c3.metric("Feedback", fb_count)
    c4.metric("AI Decisions", ai_count)
    c5.metric("Approvals", f"{approved_n}/3")
    c6.metric("Days Left", remaining_days)

    # System status
    st.subheader("⚡ System Status")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        if SUPABASE_OK:
            st.success("🔗 Database: Connected")
        else:
            st.warning("🔗 Database: Local Mode")
    with sc2:
        if AI_ENABLED:
            st.success("🧠 AI Engine: Active")
        else:
            st.warning("🧠 AI Engine: Not Configured")
    with sc3:
        if approved_n == 3:
            st.success("🗳️ Approval: Complete")
        else:
            st.warning(f"🗳️ Approval: {approved_n}/3")

    # Approval mini
    st.subheader("🗳️ Partner Approval Status")
    ac1, ac2, ac3 = st.columns(3)
    for col, cname in zip([ac1, ac2, ac3], ["Turkey", "Poland", "Spain"]):
        ok = approvals.get(cname, False)
        org = PARTNER_MAP[cname]
        with col:
            if ok:
                st.success(f"{FLAGS[cname]} {org} — Approved")
            else:
                st.warning(f"{FLAGS[cname]} {org} — Pending")

    # Charts
    ch1, ch2 = st.columns(2)
    with ch1:
        st.subheader("💰 Budget")
        if "budget_eur" in wp_df.columns:
            fig = px.pie(wp_df, names="wp_id", values="budget_eur",
                         hover_data=["wp_name"],
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
    with ch2:
        st.subheader("📊 WP Status")
        sc = wp_df["status"].value_counts().reset_index()
        sc.columns = ["status", "count"]
        fig2 = px.bar(sc, x="status", y="count", color="status")
        fig2.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # WP Table
    st.subheader("📋 Work Packages")
    display_cols = [c for c in ["wp_id", "wp_name", "lead_country", "start_month", "end_month", "status", "budget_eur"] if c in wp_df.columns]
    st.dataframe(wp_df[display_cols], use_container_width=True, hide_index=True)

    # Announcements
    st.subheader("📢 Latest Announcements")
    for a in db_get_announcements()[:3]:
        ann_card(a)


# ═══════════════════════════════════════════════════
# PAGE: WORK PACKAGES
# ═══════════════════════════════════════════════════
def page_work_packages(wp_df):
    st.title("📦 Work Packages")
    sel = st.selectbox("Select", wp_df["wp_id"].tolist())
    wp = wp_df[wp_df["wp_id"] == sel].iloc[0]

    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader(f"{wp['wp_id']}: {wp['wp_name']}")
        st.write(f"**Lead:** {wp['lead_partner']} ({wp.get('lead_country', '')})")
        st.write(f"**Supporting:** {wp['supporting_partners']}")
        st.write(f"**Duration:** M{wp['start_month']}–M{wp['end_month']}")
        if "description" in wp.index:
            st.write(f"**Description:** {wp['description']}")
        if "deliverables" in wp.index:
            for d in str(wp["deliverables"]).split(";"):
                st.write(f"- {d.strip()}")
    with c2:
        st.metric("Status", wp["status"])
        if "budget_eur" in wp.index:
            st.metric("Budget", f"EUR {wp['budget_eur']:,.0f}")

    st.divider()
    st.dataframe(wp_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
# PAGE: GANTT (Interactive)
# ═══════════════════════════════════════════════════
def page_gantt(wp_df):
    st.title("📊 Interactive Gantt Chart — 18 Months")

    g = wp_df.copy()
    g["Start"] = g["start_month"].apply(lambda m: PROJECT_START + timedelta(days=(m - 1) * 30))
    g["Finish"] = g["end_month"].apply(lambda m: PROJECT_START + timedelta(days=m * 30))
    g["Task"] = g["wp_id"] + ": " + g["wp_name"]
    g["Duration (months)"] = g["end_month"] - g["start_month"]
    lc = "lead_country" if "lead_country" in g.columns else "lead_partner"

    # Filters
    st.subheader("🔍 Filters")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        countries = g[lc].unique().tolist()
        sel_countries = st.multiselect("Country", countries, default=countries)
    with fc2:
        statuses = g["status"].unique().tolist()
        sel_status = st.multiselect("Status", statuses, default=statuses)
    with fc3:
        view_mode = st.radio("View", ["Timeline", "Duration Bars", "Both"], horizontal=True)

    filtered = g[g[lc].isin(sel_countries) & g["status"].isin(sel_status)]
    if filtered.empty:
        st.warning("No work packages match filters.")
        return

    if view_mode in ("Timeline", "Both"):
        fig = px.timeline(filtered, x_start="Start", x_end="Finish", y="Task", color=lc,
                          hover_data=["lead_partner", "status", "Duration (months)"],
                          color_discrete_map={"Turkey": "#e74c3c", "Poland": "#3498db", "Spain": "#f39c12"})
        fig.update_yaxes(autorange="reversed")

        today = datetime.now()
        fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, yref="paper",
                      line=dict(color="red", width=2, dash="dash"))
        fig.add_annotation(x=today, y=1.06, yref="paper",
                          text=f"Today ({today.strftime('%d %b')})",
                          showarrow=False, font=dict(color="red", size=11))

        milestones = [
            {"month": 1, "label": "Kickoff", "color": "#28a745"},
            {"month": 6, "label": "Needs Report", "color": "#17a2b8"},
            {"month": 10, "label": "Protocol Ready", "color": "#f39c12"},
            {"month": 15, "label": "Pilot Complete", "color": "#e74c3c"},
            {"month": 18, "label": "Final Report", "color": "#6f42c1"},
        ]
        for ms in milestones:
            ms_date = PROJECT_START + timedelta(days=(ms["month"] - 1) * 30)
            fig.add_shape(type="line", x0=ms_date, x1=ms_date, y0=0, y1=1, yref="paper",
                          line=dict(color=ms["color"], width=1, dash="dot"))
            fig.add_annotation(x=ms_date, y=-0.08, yref="paper",
                              text=f"M{ms['month']}: {ms['label']}",
                              showarrow=False, font=dict(color=ms["color"], size=9), textangle=-45)

        fig.update_layout(height=500, margin=dict(b=100))
        fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.08)
        st.plotly_chart(fig, use_container_width=True)

    if view_mode in ("Duration Bars", "Both"):
        st.subheader("⏱️ Duration Comparison")
        fig2 = px.bar(filtered, x="Duration (months)", y="Task", color=lc, orientation="h",
                      text="Duration (months)",
                      color_discrete_map={"Turkey": "#e74c3c", "Poland": "#3498db", "Spain": "#f39c12"})
        fig2.update_traces(textposition="inside")
        fig2.update_layout(height=400, yaxis=dict(autorange="reversed"), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Summary
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("WPs", len(filtered))
    sc2.metric("Avg Duration", f"{filtered['Duration (months)'].mean():.1f} mo")
    if "budget_eur" in filtered.columns:
        sc3.metric("Total Budget", f"€{filtered['budget_eur'].sum():,.0f}")
        sc4.metric("Avg Budget", f"€{filtered['budget_eur'].mean():,.0f}")


# ═══════════════════════════════════════════════════
# PAGE: PARTNERS
# ═══════════════════════════════════════════════════
def page_partners(partners_df):
    st.title("🤝 OncoConnect Consortium")
    for _, p in partners_df.iterrows():
        flag = FLAGS.get(p["country"], "")
        clr = "#e74c3c" if p["role"] == "Coordinator" else "#3498db"
        st.markdown(
            f"<div style='border:1px solid #e0e0e0;border-radius:12px;padding:1.5rem;"
            f"margin-bottom:1rem;background:white;border-left:5px solid {clr};'>"
            f"<h3 style='margin:0 0 .5rem;'>{flag} {p['organisation']}</h3>"
            f"<p><strong>Country:</strong> {p['country']} | "
            f"<strong>Role:</strong> <span style='color:{clr};font-weight:600;'>{p['role']}</span> | "
            f"<strong>Type:</strong> {p.get('type', 'N/A')}</p>"
            f"<p style='color:#555;'>{p.get('description', '')}</p></div>",
            unsafe_allow_html=True,
        )
    st.subheader("🗺️ Partner Locations")
    st.map(pd.DataFrame({"lat": [39.93, 52.23, 41.39], "lon": [32.86, 21.01, 2.17]}), zoom=3)


# ═══════════════════════════════════════════════════
# PAGE: PARTNER FEEDBACK
# ═══════════════════════════════════════════════════
def page_partner_feedback():
    st.title("💬 Partner Feedback")
    r, c = get_role(), get_country()

    if r in ("Admin", "Partner"):
        with st.form("fb_form", clear_on_submit=True):
            if r == "Partner":
                fb_country = c
                fb_org = get_org()
                st.write(f"**Partner:** {FLAGS.get(c, '')} {fb_org}")
            else:
                fb_country = st.selectbox("Country", ["Turkey", "Poland", "Spain"])
                fb_org = PARTNER_MAP.get(fb_country, "")

            section = st.selectbox("Section", PROPOSAL_SECTIONS)
            text = st.text_area("Feedback", height=150)
            priority = st.select_slider("Priority", ["Low", "Medium", "High"], "Medium")
            go = st.form_submit_button("Submit", type="primary", use_container_width=True)
            if go and text.strip():
                db_add_partner_feedback(fb_country, fb_org, section, text, priority, get_name())
                st.success("Feedback saved!")
                st.rerun()

    st.divider()
    rows = db_get_partner_feedback()
    if rows:
        df = pd.DataFrame(rows)
        sections = sorted(df["section"].unique())
        filt = st.multiselect("Filter by Section", sections)
        if filt:
            df = df[df["section"].isin(filt)]
        st.dataframe(df, use_container_width=True, hide_index=True)

        if r == "Admin" and len(df) > 0:
            st.subheader("🔧 Update Status")
            fb_id = st.selectbox("Feedback ID", df["id"].tolist())
            new_status = st.selectbox("Status", ["Open", "Under Review", "Accepted", "Rejected"])
            resp = st.text_input("Response")
            if st.button("Update"):
                db_update_feedback_status(fb_id, new_status, resp if resp else None)
                st.rerun()

        if len(df) > 2:
            fc1, fc2 = st.columns(2)
            with fc1:
                st.plotly_chart(px.histogram(df, x="section", color="section", title="By Section").update_layout(showlegend=False, height=350), use_container_width=True)
            with fc2:
                st.plotly_chart(px.histogram(df, x="partner_country", color="partner_country", title="By Country").update_layout(showlegend=False, height=350), use_container_width=True)
    else:
        st.info("No feedback yet.")


# ═══════════════════════════════════════════════════
# PAGE: PATIENT FEEDBACK
# ═══════════════════════════════════════════════════
def page_patient_feedback():
    st.title("💚 Patient Feedback")
    st.write("Your voice matters.")

    with st.form("pf_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            age = st.selectbox("Age Group", ["18-30", "31-45", "46-60", "60+"])
            pf_country = st.selectbox("Country", ["Turkey", "Poland", "Spain", "Other"])
            cancer = st.selectbox("Cancer Type", ["Prefer not to say", "Breast", "Lung", "Colorectal", "Prostate", "Other"])
        with c2:
            support = st.selectbox("Needed Support", [
                "Peer support", "Psychological support", "Reliable information",
                "Treatment sharing", "Community belonging",
            ])
            digital = st.select_slider("Digital Comfort", ["Very Low", "Low", "Medium", "High", "Very High"], "Medium")
            language = st.multiselect("Language(s)", ["Turkish", "Polish", "Spanish", "English"])

        matching = st.text_area("What matters for matching?", height=100)
        privacy = st.text_area("Privacy expectations?", height=100)
        go = st.form_submit_button("Submit", type="primary", use_container_width=True)
        if go:
            db_add_patient_feedback({
                "age_group": age, "country": pf_country, "cancer_type": cancer,
                "support_need": support, "digital_literacy": digital,
                "languages": ", ".join(language),
                "matching_preference": matching, "privacy_expectation": privacy,
                "additional": "",
            })
            st.success("Thank you!")
            st.balloons()

    if get_role() == "Admin":
        rows = db_get_patient_feedback()
        if rows:
            st.divider()
            st.subheader("Patient Feedback Data")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
# PAGE: APPROVAL STATUS
# ═══════════════════════════════════════════════════
def page_approval():
    st.title("🗳️ Proposal Approval Status")
    approvals = db_get_approvals()
    r, c = get_role(), get_country()

    cols = st.columns(3)
    for col, cname in zip(cols, ["Turkey", "Poland", "Spain"]):
        ok = approvals.get(cname, False)
        org = PARTNER_MAP[cname]
        with col:
            if ok:
                st.success(f"{FLAGS[cname]} {org}\n\nAPPROVED")
            else:
                st.warning(f"{FLAGS[cname]} {org}\n\nPENDING")
            can_approve = (r == "Partner" and c == cname and not ok) or (r == "Admin" and not ok)
            if can_approve:
                if st.button(f"Approve {cname}", key=f"a_{cname}", use_container_width=True, type="primary"):
                    db_set_approval(cname, True, get_name(), r)
                    st.rerun()
            if r == "Admin" and ok:
                if st.button(f"Revoke {cname}", key=f"r_{cname}", use_container_width=True):
                    db_set_approval(cname, False, get_name(), r)
                    st.rerun()

    st.divider()
    n = sum(1 for v in approvals.values() if v)
    st.progress(n / 3)
    st.write(f"**{n}/3** approved")

    if n == 3:
        st.success("All partners approved!")
        if r == "Admin":
            try:
                with open("documents/proposal_draft.md", "r", encoding="utf-8") as f:
                    content = f.read()
                dc1, dc2 = st.columns(2)
                with dc1:
                    st.download_button("Download Proposal", content,
                                       "OncoConnect_Proposal.md", "text/markdown",
                                       use_container_width=True, type="primary")
                with dc2:
                    report = json.dumps({"project": "OncoConnect", "status": "Approved",
                                        "approvals": approvals, "exported": datetime.now().isoformat()}, indent=2)
                    st.download_button("Approval Report", report,
                                       "Approval_Report.json", "application/json", use_container_width=True)
            except FileNotFoundError:
                st.error("proposal_draft.md not found.")
        else:
            st.info("Only Admin can download.")
    else:
        waiting = [f"{FLAGS[w]} {w}" for w, v in approvals.items() if not v]
        st.warning(f"Waiting: {', '.join(waiting)}")

    if r == "Admin":
        log = db_get_approval_log()
        if log:
            st.subheader("Approval Log")
            st.dataframe(pd.DataFrame(log), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
# PAGE: ANNOUNCEMENTS
# ═══════════════════════════════════════════════════
def page_announcements():
    st.title("📢 Announcements")
    for a in db_get_announcements():
        ann_card(a)

    if get_role() in ("Admin", "Partner"):
        st.divider()
        with st.form("ann_form", clear_on_submit=True):
            title = st.text_input("Title")
            content = st.text_area("Content", height=120)
            priority = st.select_slider("Priority", ["Low", "Medium", "High"], "Medium")
            if st.form_submit_button("Publish", type="primary", use_container_width=True):
                if title.strip() and content.strip():
                    db_add_announcement(title, content, f"{get_name()} ({get_org()})", priority)
                    st.success("Published!")
                    st.rerun()


# ═══════════════════════════════════════════════════
# PAGE: DOCUMENTS
# ═══════════════════════════════════════════════════
def page_documents():
    st.title("📁 Project Documents")
    t1, t2, t3 = st.tabs(["Proposal", "Resources", "Budget"])

    with t1:
        try:
            with open("documents/proposal_draft.md", "r", encoding="utf-8") as f:
                text = f.read()
            st.markdown(text)
            if get_role() == "Admin":
                st.download_button("Download", text, "proposal_draft.md", "text/markdown", use_container_width=True)
        except FileNotFoundError:
            st.warning("File not found.")

    with t2:
        st.markdown("""
        **Planned:**
        - Partner Agreement
        - Ethics Templates
        - Meeting Minutes
        - Training Curriculum
        """)

    with t3:
        bd = pd.DataFrame({
            "WP": ["WP1", "WP2", "WP3", "WP4", "WP5"],
            "Name": ["Management", "Needs Analysis", "Development", "Pilot", "Evaluation"],
            "Budget": [12000, 7000, 15000, 12000, 14000],
            "Lead": ["Turkey", "Poland", "Spain", "Turkey", "Spain"],
        })
        st.dataframe(bd, hide_index=True, use_container_width=True)
        fig = px.bar(bd, x="WP", y="Budget", color="Lead", text="Budget")
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════
# PAGE: AI DECISION CENTER ← NEW
# ═══════════════════════════════════════════════════
def page_ai_center():
    st.title("🧠 AI Decision Center")

    if get_role() != "Admin":
        st.error("Access denied. Admin only.")
        return

    # Status banner
    if AI_ENABLED:
        st.success("🧠 AI Engine: **Active** (GPT-4o-mini)")
    else:
        st.warning("⚠️ AI Engine not configured. Add OpenAI key to Streamlit Secrets.")
        st.code('[openai]\napi_key = "sk-proj-..."', language="toml")
        st.info("Features will work in manual mode.")

    t1, t2, t3, t4 = st.tabs(["🔍 Analyze", "📜 Improvement Log", "🤖 AI Decisions", "📊 Insights"])

    # ── TAB 1: Analyze Feedback ──
    with t1:
        st.subheader("Analyze Pending Feedback")
        all_fb = db_get_partner_feedback()
        open_fb = [f for f in all_fb if f.get("status") == "Open"]

        if not open_fb:
            st.info("No open feedback to analyze.")
        else:
            st.write(f"**{len(open_fb)} open feedback items**")

            for fb in open_fb:
                with st.expander(f"#{fb['id']} — {fb['section']} ({fb.get('partner_country', '')}) — {fb.get('priority', 'N/A')}"):
                    st.write(f"**Feedback:** {fb['feedback']}")
                    st.write(f"**By:** {fb.get('submitted_by', 'Unknown')} | **Priority:** {fb.get('priority', '')}")

                    col_ai, col_manual = st.columns(2)

                    with col_ai:
                        if st.button(f"🧠 AI Analyze", key=f"ai_{fb['id']}"):
                            with st.spinner("AI analyzing..."):
                                result = ai_analyze_feedback(fb["feedback"], fb["section"])

                            st.session_state[f"ai_result_{fb['id']}"] = result

                    # Show result if exists
                    result_key = f"ai_result_{fb['id']}"
                    if result_key in st.session_state:
                        result = st.session_state[result_key]
                        decision = result.get("decision", "manual_review")
                        confidence = result.get("confidence", 0)
                        reasoning = result.get("reasoning", "")
                        suggested = result.get("suggested_action", "")
                        priority_ai = result.get("priority", "medium")
                        affected_wp = result.get("affected_wp", "")

                        st.divider()

                        # Decision badge
                        if decision == "integrate":
                            st.success(f"✅ **INTEGRATE** — Confidence: {confidence:.0%}")
                        elif decision == "archive":
                            st.info(f"📦 **ARCHIVE** — Confidence: {confidence:.0%}")
                        elif decision == "route":
                            st.warning(f"🔀 **ROUTE** — Confidence: {confidence:.0%}")
                        elif decision == "reject":
                            st.error(f"❌ **REJECT** — Confidence: {confidence:.0%}")
                        else:
                            st.warning(f"👁️ **MANUAL REVIEW** — Confidence: {confidence:.0%}")

                        st.write(f"**Reasoning:** {reasoning}")
                        if suggested:
                            st.write(f"**Suggested Action:** {suggested}")
                        if affected_wp:
                            st.write(f"**Affected WP:** {affected_wp}")
                        st.write(f"**AI Priority:** {priority_ai}")

                        # Action buttons
                        act1, act2, act3, act4 = st.columns(4)
                        with act1:
                            if st.button("✅ Accept", key=f"acc_{fb['id']}"):
                                db_update_feedback_status(fb["id"], "Accepted", f"AI: {reasoning}")
                                db_log_ai_decision(fb["id"], decision, confidence, reasoning,
                                                   result.get("target_section", fb["section"]))
                                db_log_improvement(fb["id"], fb["section"], "", "",
                                                   reasoning, decision, get_name())
                                st.rerun()
                        with act2:
                            if st.button("❌ Reject", key=f"rej_{fb['id']}"):
                                db_update_feedback_status(fb["id"], "Rejected", f"AI: {reasoning}")
                                db_log_ai_decision(fb["id"], "reject", confidence, reasoning, fb["section"])
                                st.rerun()
                        with act3:
                            if st.button("📦 Archive", key=f"arc_{fb['id']}"):
                                db_update_feedback_status(fb["id"], "Under Review", "Archived for future")
                                db_log_ai_decision(fb["id"], "archive", confidence, reasoning, fb["section"])
                                st.rerun()
                        with act4:
                            if st.button("⏳ Later", key=f"lat_{fb['id']}"):
                                db_update_feedback_status(fb["id"], "Under Review")
                                st.rerun()

                    with col_manual:
                        manual_status = st.selectbox("Manual Status", ["Open", "Under Review", "Accepted", "Rejected"],
                                                      key=f"ms_{fb['id']}")
                        manual_resp = st.text_input("Response", key=f"mr_{fb['id']}")
                        if st.button("Update", key=f"mu_{fb['id']}"):
                            db_update_feedback_status(fb["id"], manual_status, manual_resp if manual_resp else None)
                            st.rerun()

        # Bulk analyze
        st.divider()
        st.subheader("🔄 Bulk Actions")
        if open_fb and st.button("🧠 Analyze ALL Open Feedback", type="primary"):
            progress = st.progress(0)
            results = []
            for i, fb in enumerate(open_fb):
                with st.spinner(f"Analyzing #{fb['id']}..."):
                    result = ai_analyze_feedback(fb["feedback"], fb["section"])
                    results.append({"id": fb["id"], "section": fb["section"], **result})
                    db_log_ai_decision(fb["id"], result.get("decision", "manual_review"),
                                       result.get("confidence", 0),
                                       result.get("reasoning", ""),
                                       result.get("target_section", fb["section"]))
                progress.progress((i + 1) / len(open_fb))

            st.success(f"Analyzed {len(results)} items!")
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

    # ── TAB 2: Improvement Log ──
    with t2:
        st.subheader("📜 Improvement Log")
        st.markdown("Track all changes made to the proposal based on feedback.")

        log = db_get_improvement_log()
        if log:
            log_df = pd.DataFrame(log)
            st.dataframe(log_df, use_container_width=True, hide_index=True)

            st.subheader("Log Statistics")
            lc1, lc2 = st.columns(2)
            with lc1:
                if "action" in log_df.columns:
                    fig = px.pie(log_df, names="action", title="Actions Distribution")
                    st.plotly_chart(fig, use_container_width=True)
            with lc2:
                if "section" in log_df.columns:
                    fig2 = px.histogram(log_df, x="section", title="By Section")
                    fig2.update_layout(showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No improvements logged yet. Analyze feedback to generate logs.")

    # ── TAB 3: AI Decisions ──
    with t3:
        st.subheader("🤖 AI Decision History")
        decisions = db_get_ai_decisions()
        if decisions:
            dec_df = pd.DataFrame(decisions)
            st.dataframe(dec_df, use_container_width=True, hide_index=True)

            dc1, dc2, dc3 = st.columns(3)
            with dc1:
                if "decision" in dec_df.columns:
                    fig = px.pie(dec_df, names="decision", title="Decision Distribution",
                                 color_discrete_map={
                                     "integrate": "#28a745", "archive": "#17a2b8",
                                     "route": "#ffc107", "reject": "#dc3545",
                                     "manual_review": "#6c757d",
                                 })
                    st.plotly_chart(fig, use_container_width=True)
            with dc2:
                if "confidence" in dec_df.columns:
                    fig2 = px.histogram(dec_df, x="confidence", nbins=10,
                                        title="Confidence Distribution")
                    st.plotly_chart(fig2, use_container_width=True)
            with dc3:
                if "target_section" in dec_df.columns:
                    fig3 = px.histogram(dec_df, x="target_section", title="By Section")
                    fig3.update_layout(showlegend=False)
                    st.plotly_chart(fig3, use_container_width=True)

            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Total Decisions", len(dec_df))
            if "confidence" in dec_df.columns:
                sm2.metric("Avg Confidence", f"{dec_df['confidence'].mean():.0%}")
            if "decision" in dec_df.columns:
                sm3.metric("Integrated", len(dec_df[dec_df["decision"] == "integrate"]))
                sm4.metric("Rejected", len(dec_df[dec_df["decision"] == "reject"]))
        else:
            st.info("No AI decisions yet.")

            # Summary metrics
            st.subheader("Summary")
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Total Decisions", len(dec_df))
            if "confidence" in dec_df.columns:
                sm2.metric("Avg Confidence", f"{dec_df['confidence'].mean():.0%}")
            if "decision" in dec_df.columns:
                integrate_n = len(dec_df[dec_df["decision"] == "integrate"])
                sm3.metric("Integrated", integrate_n)
                reject_n = len(dec_df[dec_df["decision"] == "reject"])
                sm4.metric("Rejected", reject_n)
        else:
            st.info("No AI decisions yet.")
            
    # ── TAB 4: AI Insights ──
    with t4:
        st.subheader("📊 AI-Generated Insights")

        all_fb = db_get_partner_feedback()
        patient_fb = db_get_patient_feedback()

        if not all_fb and not patient_fb:
            st.info("No feedback data to analyze.")
        else:
            st.write(f"**{len(all_fb)}** partner feedback | **{len(patient_fb)}** patient feedback")

            if st.button("🧠 Generate Feedback Summary", type="primary"):
                with st.spinner("AI generating insights..."):
                    summary = ai_generate_summary(all_fb)
                st.markdown("### Partner Feedback Summary")
                st.markdown(summary)

                st.session_state["ai_summary"] = summary

            if "ai_summary" in st.session_state:
                st.markdown("### Latest Summary")
                st.markdown(st.session_state["ai_summary"])

            # Manual insights
            st.divider()
            st.subheader("📈 Data-Driven Insights")

            if all_fb:
                fb_df = pd.DataFrame(all_fb)

                ic1, ic2 = st.columns(2)
                with ic1:
                    if "section" in fb_df.columns:
                        section_counts = fb_df["section"].value_counts()
                        st.markdown("**Most Discussed Sections:**")
                        for sec, count in section_counts.head(5).items():
                            st.write(f"- {sec}: {count} feedback items")

                with ic2:
                    if "priority" in fb_df.columns:
                        priority_counts = fb_df["priority"].value_counts()
                        st.markdown("**Priority Distribution:**")
                        for pri, count in priority_counts.items():
                            icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(pri, "⚪")
                            st.write(f"- {icon} {pri}: {count}")

                if "status" in fb_df.columns:
                    st.subheader("Feedback Pipeline")
                    status_counts = fb_df["status"].value_counts()
                    fig = px.funnel(
                        x=status_counts.values,
                        y=status_counts.index,
                        title="Feedback Processing Pipeline",
                    )
                    st.plotly_chart(fig, use_container_width=True)

            if patient_fb:
                st.subheader("Patient Insights")
                pf_df = pd.DataFrame(patient_fb)
                pi1, pi2 = st.columns(2)
                with pi1:
                    if "support_need" in pf_df.columns:
                        fig = px.pie(pf_df, names="support_need", title="Patient Support Needs")
                        st.plotly_chart(fig, use_container_width=True)
                with pi2:
                    if "country" in pf_df.columns:
                        fig2 = px.histogram(pf_df, x="country", color="country", title="By Country")
                        fig2.update_layout(showlegend=False)
                        st.plotly_chart(fig2, use_container_width=True)


# ═══════════════════════════════════════════════════
# PAGE: ADMIN PANEL
# ═══════════════════════════════════════════════════
def page_admin():
    st.title("🛡️ Admin Panel")
    if get_role() != "Admin":
        st.error("Access denied.")
        return

    t1, t2, t3, t4 = st.tabs(["Overview", "Data", "Export", "System"])

    with t1:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Feedback", len(db_get_partner_feedback()))
        m2.metric("Patient FB", len(db_get_patient_feedback()))
        m3.metric("AI Decisions", len(db_get_ai_decisions()))
        m4.metric("Improvements", len(db_get_improvement_log()))
        approvals = db_get_approvals()
        m5.metric("Approvals", f"{sum(1 for v in approvals.values() if v)}/3")

        st.subheader("System Status")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            if SUPABASE_OK:
                st.success("Database: Connected")
            else:
                st.warning("Database: Local Mode")
        with sc2:
            if AI_ENABLED:
                st.success("AI Engine: Active")
            else:
                st.warning("AI Engine: Inactive")
        with sc3:
            st.info(f"Users: {len(USERS_DB)}")

    with t2:
        st.subheader("Partner Feedback")
        fb = db_get_partner_feedback()
        if fb:
            st.dataframe(pd.DataFrame(fb), use_container_width=True, hide_index=True)
        else:
            st.info("No data.")

        st.subheader("Patient Feedback")
        pf = db_get_patient_feedback()
        if pf:
            st.dataframe(pd.DataFrame(pf), use_container_width=True, hide_index=True)
        else:
            st.info("No data.")

        st.subheader("Improvement Log")
        il = db_get_improvement_log()
        if il:
            st.dataframe(pd.DataFrame(il), use_container_width=True, hide_index=True)
        else:
            st.info("No data.")

        st.subheader("AI Decisions")
        ad = db_get_ai_decisions()
        if ad:
            st.dataframe(pd.DataFrame(ad), use_container_width=True, hide_index=True)
        else:
            st.info("No data.")

    with t3:
        st.subheader("Full Data Export")
        export = {
            "project": "OncoConnect",
            "programme": "Erasmus+ KA210",
            "exported_at": datetime.now().isoformat(),
            "approvals": db_get_approvals(),
            "approval_log": db_get_approval_log(),
            "partner_feedback": db_get_partner_feedback(),
            "patient_feedback": db_get_patient_feedback(),
            "ai_decisions": db_get_ai_decisions(),
            "improvement_log": db_get_improvement_log(),
            "announcements": db_get_announcements(),
        }
        st.download_button("Export All (JSON)",
                           json.dumps(export, indent=2, ensure_ascii=False, default=str),
                           "oncoconnect_full_export.json", "application/json",
                           use_container_width=True, type="primary")

    with t4:
        st.subheader("Reset Actions")
        st.warning("These actions cannot be undone!")

        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("Reset Approvals"):
                for cname in ["Turkey", "Poland", "Spain"]:
                    db_set_approval(cname, False, "Admin", "Admin")
                st.success("Approvals reset.")
                st.rerun()
        with rc2:
            st.write("Database tables can be reset from Supabase Dashboard.")

        st.divider()
        st.subheader("Configuration")
        st.json({
            "supabase_connected": SUPABASE_OK,
            "ai_enabled": AI_ENABLED,
            "submission_deadline": SUBMISSION_DEADLINE.isoformat(),
            "preparation_start": PREPARATION_START.isoformat(),
            "total_budget": TOTAL_BUDGET,
            "project_duration": "18 months",
        })


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════
def main():
    if not render_login():
        return

    wp_df, partners_df = load_static()
    r = get_role()

    # Sidebar
    st.sidebar.markdown("### 🧬 OncoConnect")
    st.sidebar.caption("Erasmus+ KA210")
    st.sidebar.write(f"**{get_name()}** ({ROLE_BADGES.get(r, r)})")
    if r == "Partner":
        st.sidebar.write(f"{FLAGS.get(get_country(), '')} {get_org()}")
    st.sidebar.divider()

    if r == "Admin":
        pages = ["Dashboard", "Work Packages", "Gantt Chart", "Partners",
                 "Partner Feedback", "Patient Feedback", "Approval Status",
                 "Announcements", "Documents", "🧠 AI Center", "Admin Panel"]
    elif r == "Partner":
        pages = ["Dashboard", "Work Packages", "Gantt Chart", "Partners",
                 "Partner Feedback", "Patient Feedback", "Approval Status",
                 "Announcements", "Documents"]
    else:
        pages = ["Dashboard", "Patient Feedback", "Announcements", "Documents"]

    page = st.sidebar.radio("Navigation", pages)
    st.sidebar.divider()

    # Status indicators
    if SUPABASE_OK:
        st.sidebar.success("DB: Connected")
    else:
        st.sidebar.warning("DB: Local")

    if AI_ENABLED:
        st.sidebar.success("AI: Active")
    else:
        st.sidebar.info("AI: Inactive")

    if st.sidebar.button("Logout", use_container_width=True):
        logout()

    # Router
    if page == "Dashboard":
        page_dashboard(wp_df, partners_df)
    elif page == "Work Packages":
        page_work_packages(wp_df)
    elif page == "Gantt Chart":
        page_gantt(wp_df)
    elif page == "Partners":
        page_partners(partners_df)
    elif page == "Partner Feedback":
        page_partner_feedback()
    elif page == "Patient Feedback":
        page_patient_feedback()
    elif page == "Approval Status":
        page_approval()
    elif page == "Announcements":
        page_announcements()
    elif page == "Documents":
        page_documents()
    elif page == "🧠 AI Center":
        page_ai_center()
    elif page == "Admin Panel":
        page_admin()


if __name__ == "__main__":
    main()
