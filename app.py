"""
OncoConnect Co-Creation Hub
Erasmus+ KA210 Small-Scale Partnership
AI-Integrated Proposal Governance Platform
═══════════════════════════════════════════
v3.0 — Full Auth + Storage + AI Feedback Integration Engine
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import time
import io
from datetime import datetime, timedelta, date

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
except Exception:
    SUPABASE_OK = False


def sb():
    if SUPABASE_OK:
        return get_supabase()
    return None


# ═══════════════════════════════════════════════════
# AI ENGINE — OpenRouter / OpenAI Dual Support
# ═══════════════════════════════════════════════════
AI_ENABLED = False
USE_OPENROUTER = False
ai_client = None
ai_model = "gpt-4o-mini"

try:
    import openai

    openrouter_key = st.secrets.get("openrouter", {}).get("api_key", "")
    openai_key = st.secrets.get("openai", {}).get("api_key", "")

    if openrouter_key:
        ai_client = openai.OpenAI(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1"
        )
        ai_model = st.secrets.get("openrouter", {}).get("model", "openai/gpt-4o-mini")
        AI_ENABLED = True
        USE_OPENROUTER = True
    elif openai_key:
        ai_client = openai.OpenAI(api_key=openai_key)
        ai_model = "gpt-4o-mini"
        AI_ENABLED = True
        USE_OPENROUTER = False
except Exception:
    AI_ENABLED = False


# ═══════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════
SUBMISSION_DEADLINE = datetime(2027, 5, 15, 17, 0, 0)
PREPARATION_START = datetime(2025, 6, 5)
PROJECT_START = datetime(2025, 9, 1)
TOTAL_BUDGET = 60000
BUCKET = "oncoconnect-files"

PARTNER_MAP = {
    "Turkey": "Kanser Savaşçıları Derneği",
    "Poland": "Fundacja Onkologiczna Rakiety",
    "Spain": "Universitat de Barcelona",
}
FLAGS = {"Turkey": "🇹🇷", "Poland": "🇵🇱", "Spain": "🇪🇸"}
ROLE_BADGES = {"Admin": "🛡️ Admin", "Partner": "🤝 Partner", "Patient": "💚 Patient"}

PROPOSAL_SECTIONS = [
    "Project Summary",
    "Problem Analysis",
    "Objectives",
    "Methodology",
    "Work Packages",
    "Partnership",
    "Impact",
    "Evaluation",
    "Budget",
    "Dissemination",
    "Ethics / GDPR",
    "Sustainability",
]

PROPOSAL_SECTION_KEYS = [
    ("project_summary", "Project Summary"),
    ("problem_analysis", "Problem Analysis"),
    ("objectives", "Objectives"),
    ("methodology", "Methodology"),
    ("work_packages", "Work Packages"),
    ("partnership", "Partnership"),
    ("impact", "Impact"),
    ("evaluation", "Evaluation"),
    ("budget", "Budget"),
    ("dissemination", "Dissemination"),
    ("ethics_gdpr", "Ethics / GDPR"),
    ("sustainability", "Sustainability"),
]

USERS_DB = {
    "admin": {"password": "admin123", "name": "Project Admin", "role": "Admin", "country": "All", "org": "OncoConnect", "can_read_patient_fb": True},
    "turkey": {"password": "tr2025", "name": "KSD Coordinator", "role": "Partner", "country": "Turkey", "org": "Kanser Savaşçıları Derneği", "can_read_patient_fb": False},
    "poland": {"password": "pl2025", "name": "Rakiety Team", "role": "Partner", "country": "Poland", "org": "Fundacja Onkologiczna Rakiety", "can_read_patient_fb": False},
    "spain": {"password": "es2025", "name": "UB Research Team", "role": "Partner", "country": "Spain", "org": "Universitat de Barcelona", "can_read_patient_fb": False},
    "patient": {"password": "patient123", "name": "Patient Participant", "role": "Patient", "country": "N/A", "org": "N/A", "can_read_patient_fb": False},
}


# ═══════════════════════════════════════════════════
# WP → ÜLKE YETKİ MATRİSİ
# ═══════════════════════════════════════════════════
WP_COUNTRY_MAP = {
    "Turkey": {"lead": ["WP1", "WP4"], "support": ["WP2", "WP3", "WP5"]},
    "Poland": {"lead": ["WP2"], "support": ["WP3", "WP4", "WP5"]},
    "Spain": {"lead": ["WP3", "WP5"], "support": ["WP2", "WP4"]},
}


def get_user_wps(country):
    if country == "All":
        return ["WP1", "WP2", "WP3", "WP4", "WP5"]
    m = WP_COUNTRY_MAP.get(country, {})
    return m.get("lead", []) + m.get("support", [])


def get_wp_role(country, wp):
    m = WP_COUNTRY_MAP.get(country, {})
    if wp in m.get("lead", []):
        return "🟢 Lead"
    elif wp in m.get("support", []):
        return "🔵 Support"
    return "⚪ —"


# ═══════════════════════════════════════════════════
# SAYFA YETKİ MATRİSİ
# ═══════════════════════════════════════════════════
PAGE_PERMISSIONS = {
    "Dashboard": {"Admin": "full", "Partner": "read", "Patient": "read"},
    "Work Packages": {"Admin": "full", "Partner": "filtered", "Patient": "none"},
    "Gantt Chart": {"Admin": "full", "Partner": "filtered", "Patient": "none"},
    "Partners": {"Admin": "full", "Partner": "read", "Patient": "read"},
    "Partner Feedback": {"Admin": "full", "Partner": "write", "Patient": "none"},
    "Patient Feedback": {"Admin": "full", "Partner": "none", "Patient": "write"},
    "Approval Status": {"Admin": "full", "Partner": "own", "Patient": "none"},
    "Announcements": {"Admin": "full", "Partner": "write", "Patient": "read"},
    "Documents": {"Admin": "full", "Partner": "upload", "Patient": "read"},
    "🧠 AI Center": {"Admin": "full", "Partner": "none", "Patient": "none"},
    "Admin Panel": {"Admin": "full", "Partner": "none", "Patient": "none"},
    "User Management": {"Admin": "full", "Partner": "none", "Patient": "none"},
}


def check_access(page_name, role):
    return PAGE_PERMISSIONS.get(page_name, {}).get(role, "none") != "none"


def get_permission(page_name, role):
    return PAGE_PERMISSIONS.get(page_name, {}).get(role, "none")


# ═══════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════
def init_session():
    defaults = {
        "authenticated": False, "username": None, "user_name": None,
        "user_role": None, "user_country": None, "user_org": None,
        "can_read_patient_fb": False, "current_page": "Dashboard",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_login():
    if st.session_state.get("authenticated"):
        return True
    st.markdown(
        "<div style='text-align:center;padding:3rem 0 1rem;'>"
        "<h1>🧬 OncoConnect</h1>"
        "<h3 style='color:#555;font-weight:400;'>Co-Creation Hub</h3>"
        "<p style='color:#777;'>Erasmus+ KA210 — AI-Driven Proposal Governance Platform</p>"
        "</div>", unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login"):
            username = st.text_input("Username", placeholder="admin / turkey / poland / spain / patient")
            password = st.text_input("Password", type="password")
            go = st.form_submit_button("Login", use_container_width=True, type="primary")
            if go:
                user_data = None
                if SUPABASE_OK:
                    try:
                        res = sb().table("app_users").select("*").eq("username", username.strip().lower()).eq("is_active", True).execute()
                        if res.data:
                            u = res.data[0]
                            if u["password_hash"] == password:
                                user_data = {"name": u["display_name"], "role": u["role"],
                                             "country": u["country"], "org": u.get("organisation", "N/A"),
                                             "can_read_patient_fb": u.get("can_read_patient_fb", False)}
                    except Exception:
                        pass
                if not user_data:
                    u = USERS_DB.get(username)
                    if u and u["password"] == password:
                        user_data = {"name": u["name"], "role": u["role"], "country": u["country"],
                                     "org": u["org"], "can_read_patient_fb": u.get("can_read_patient_fb", False)}
                if user_data:
                    st.session_state.update(
                        authenticated=True, username=username.strip().lower(),
                        user_name=user_data["name"], user_role=user_data["role"],
                        user_country=user_data["country"], user_org=user_data["org"],
                        can_read_patient_fb=user_data["can_read_patient_fb"],
                    )
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        with st.expander("Demo Credentials"):
            st.markdown(
                "| User | Pass | Role |\n|---|---|---|\n"
                "| admin | admin123 | Admin |\n| turkey | tr2025 | Partner TR |\n"
                "| poland | pl2025 | Partner PL |\n| spain | es2025 | Partner ES |\n"
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
# SUPABASE STORAGE
# ═══════════════════════════════════════════════════
def upload_to_storage(file_bytes, storage_path, content_type="application/octet-stream"):
    if not SUPABASE_OK:
        return False
    try:
        sb().storage.from_(BUCKET).upload(path=storage_path, file=file_bytes,
                                           file_options={"content-type": content_type, "upsert": "true"})
        return True
    except Exception as e:
        st.error(f"Upload error: {e}")
        return False


def download_from_storage(storage_path):
    if not SUPABASE_OK:
        return None
    try:
        return sb().storage.from_(BUCKET).download(storage_path)
    except Exception as e:
        st.error(f"Download error: {e}")
        return None


def delete_from_storage(storage_path):
    if not SUPABASE_OK:
        return False
    try:
        sb().storage.from_(BUCKET).remove([storage_path])
        return True
    except:
        return False


def save_document_metadata(file_name, file_type, file_size, category, description, uploaded_by, country, storage_path, version=1):
    if not SUPABASE_OK:
        return
    try:
        sb().table("documents").insert({
            "file_name": file_name, "file_type": file_type, "file_size": file_size,
            "category": category, "description": description, "uploaded_by": uploaded_by,
            "country": country, "storage_path": storage_path, "version": version, "is_active": True,
        }).execute()
    except Exception as e:
        st.error(f"Metadata error: {e}")


# ═══════════════════════════════════════════════════
# DB — APPROVALS
# ═══════════════════════════════════════════════════
def db_get_approvals():
    default = {"Turkey": False, "Poland": False, "Spain": False}
    if not SUPABASE_OK:
        return st.session_state.get("local_approvals", default)
    try:
        res = sb().table("approvals").select("country, approved").execute()
        result = {r["country"]: r.get("approved", False) for r in (res.data or [])}
        for c in ["Turkey", "Poland", "Spain"]:
            if c not in result:
                result[c] = False
        return result
    except:
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
            "approved": approved, "status": "Approved" if approved else "Pending",
            "approved_by": performed_by if approved else None,
            "approved_at": now_str if approved else None, "updated_at": now_str,
        }).eq("country", country_name).execute()
        sb().table("approval_log").insert({
            "action": "approved" if approved else "revoked",
            "country": country_name, "performed_by": performed_by, "role": user_role,
        }).execute()
    except Exception as e:
        st.error(f"DB Error: {e}")


def db_reset_all_approvals(performed_by):
    for c in ["Turkey", "Poland", "Spain"]:
        db_set_approval(c, False, performed_by, "Admin")


def db_get_approval_log():
    if not SUPABASE_OK:
        return []
    try:
        return sb().table("approval_log").select("*").order("created_at", desc=True).execute().data or []
    except:
        return []


# ═══════════════════════════════════════════════════
# DB — PARTNER FEEDBACK
# ═══════════════════════════════════════════════════
def db_get_partner_feedback():
    if not SUPABASE_OK:
        return st.session_state.get("local_feedback", [])
    try:
        return sb().table("partner_feedback").select("*").order("created_at", desc=True).execute().data or []
    except:
        return []


def db_add_partner_feedback(p_country, org, section, feedback, priority, submitted_by):
    if not SUPABASE_OK:
        if "local_feedback" not in st.session_state:
            st.session_state["local_feedback"] = []
        st.session_state["local_feedback"].append({
            "id": len(st.session_state["local_feedback"]) + 1,
            "partner_country": p_country, "organisation": org, "section": section,
            "feedback": feedback, "content": feedback, "priority": priority,
            "status": "Open", "submitted_by": submitted_by, "country": p_country,
            "created_at": datetime.now().isoformat(),
        })
        return
    try:
        sb().table("partner_feedback").insert({
            "partner_country": p_country, "organisation": org, "section": section,
            "feedback": feedback, "content": feedback, "priority": priority,
            "status": "Open", "submitted_by": submitted_by, "country": p_country,
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
# DB — PATIENT FEEDBACK
# ═══════════════════════════════════════════════════
def db_get_patient_feedback():
    if not SUPABASE_OK:
        return st.session_state.get("local_patient_fb", [])
    try:
        return sb().table("patient_feedback").select("*").order("created_at", desc=True).execute().data or []
    except:
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
# DB — ANNOUNCEMENTS
# ═══════════════════════════════════════════════════
def db_get_announcements():
    if not SUPABASE_OK:
        return st.session_state.get("local_announcements", [])
    try:
        return sb().table("announcements").select("*").order("created_at", desc=True).execute().data or []
    except:
        return []


def db_add_announcement(title, content, author, priority):
    if not SUPABASE_OK:
        if "local_announcements" not in st.session_state:
            st.session_state["local_announcements"] = []
        st.session_state["local_announcements"].append({
            "id": len(st.session_state["local_announcements"]) + 1,
            "title": title, "content": content, "author": author,
            "priority": priority, "created_at": datetime.now().isoformat(),
        })
        return
    try:
        sb().table("announcements").insert({
            "title": title, "content": content, "author": author, "priority": priority,
        }).execute()
    except Exception as e:
        st.error(f"DB Error: {e}")


# ═══════════════════════════════════════════════════
# DB — AI / IMPROVEMENT LOG
# ═══════════════════════════════════════════════════
def db_log_improvement(feedback_id, section, original, updated, reasoning, action, created_by):
    if not SUPABASE_OK:
        if "local_improvement_log" not in st.session_state:
            st.session_state["local_improvement_log"] = []
        st.session_state["local_improvement_log"].append({
            "id": len(st.session_state["local_improvement_log"]) + 1,
            "feedback_id": feedback_id, "section": section, "original_text": original,
            "updated_text": updated, "ai_reasoning": reasoning, "action": action,
            "created_by": created_by, "created_at": datetime.now().isoformat(),
        })
        return
    try:
        sb().table("improvement_log").insert({
            "feedback_id": feedback_id, "section": section, "original_text": original,
            "updated_text": updated, "ai_reasoning": reasoning, "action": action, "created_by": created_by,
        }).execute()
    except Exception as e:
        st.error(f"Log error: {e}")


def db_get_improvement_log():
    if not SUPABASE_OK:
        return st.session_state.get("local_improvement_log", [])
    try:
        return sb().table("improvement_log").select("*").order("created_at", desc=True).execute().data or []
    except:
        return []


def db_log_ai_decision(feedback_id, decision, confidence, reasoning, target_section):
    if not SUPABASE_OK:
        if "local_ai_decisions" not in st.session_state:
            st.session_state["local_ai_decisions"] = []
        st.session_state["local_ai_decisions"].append({
            "id": len(st.session_state["local_ai_decisions"]) + 1,
            "feedback_id": feedback_id, "decision": decision, "confidence": confidence,
            "reasoning": reasoning, "target_section": target_section,
            "created_at": datetime.now().isoformat(),
        })
        return
    try:
        sb().table("ai_decisions").insert({
            "feedback_id": feedback_id, "decision": decision, "confidence": confidence,
            "reasoning": reasoning, "target_section": target_section,
        }).execute()
    except Exception as e:
        st.error(f"AI log error: {e}")


def db_get_ai_decisions():
    if not SUPABASE_OK:
        return st.session_state.get("local_ai_decisions", [])
    try:
        return sb().table("ai_decisions").select("*").order("created_at", desc=True).execute().data or []
    except:
        return []


# ═══════════════════════════════════════════════════
# DB — PROPOSAL SECTIONS
# ═══════════════════════════════════════════════════
def db_get_proposal_sections():
    if not SUPABASE_OK:
        return st.session_state.get("local_sections", [])
    try:
        return sb().table("proposal_sections").select("*").eq("is_active", True).order("section_order").execute().data or []
    except:
        return []


def db_get_section_by_key(key):
    if not SUPABASE_OK:
        sections = st.session_state.get("local_sections", [])
        return next((s for s in sections if s.get("section_key") == key), None)
    try:
        res = sb().table("proposal_sections").select("*").eq("section_key", key).eq("is_active", True).execute()
        return res.data[0] if res.data else None
    except:
        return None


def db_update_section_content(section_key, new_content, updated_by, feedback_id=None):
    if not SUPABASE_OK:
        return 1
    try:
        current = db_get_section_by_key(section_key)
        new_version = (current.get("version", 1) + 1) if current else 1
        sb().table("proposal_sections").update({
            "content": new_content, "version": new_version,
            "last_updated_by": updated_by, "last_feedback_id": feedback_id,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("section_key", section_key).eq("is_active", True).execute()
        return new_version
    except Exception as e:
        st.error(f"Section update error: {e}")
        return None


def _find_section_for_feedback(fb_section):
    """Feedback section adından proposal section bul"""
    section_key = fb_section.lower().replace(" ", "_").replace("/", "_").replace(" ", "")
    section_data = db_get_section_by_key(section_key)
    if section_data:
        return section_data
    sections = db_get_proposal_sections()
    for s in sections:
        if s["section_title"].lower() == fb_section.lower():
            return s
        if fb_section.lower() in s["section_title"].lower():
            return s
    return None


# ═══════════════════════════════════════════════════
# AI ENGINE
# ═══════════════════════════════════════════════════
def ai_analyze_feedback_v2(feedback_text, section_key, section_content):
    if not AI_ENABLED or not ai_client:
        return {
            "decision": "manual_review", "confidence": 0,
            "reasoning": "AI not configured.", "target_section": section_key,
            "suggested_action": "review", "suggested_text": "",
            "priority": "medium", "affected_wp": "", "erasmus_criteria": {},
        }
    try:
        response = ai_client.chat.completions.create(
            model=ai_model,
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert Erasmus+ KA210 Small-Scale Partnership proposal analyst for the OncoConnect project.

PROJECT: OncoConnect — Structured peer mentorship for cancer patients (Turkey, Poland, Spain).
PROGRAMME: Erasmus+ KA210 Adult Education | BUDGET: €60,000 | DURATION: 18 months

WPs: WP1=Management(TR), WP2=Needs Analysis(PL), WP3=Matching System(ES), WP4=Pilot(TR), WP5=Evaluation(ES+PL)

ERASMUS+ KA210 CRITERIA:
1. Relevance to adult education 2. Quality of design 3. Partnership quality
4. Impact & dissemination 5. Inclusion & diversity 6. Digital dimension 7. Sustainability

Return JSON:
{
    "decision": "integrate"|"revise"|"route"|"archive"|"reject"|"ethical_risk",
    "confidence": 0.0-1.0,
    "reasoning": "2-3 sentences",
    "target_section": "section_key if routing",
    "suggested_action": "specific action",
    "suggested_text": "If integrate/revise: revised text in academic English",
    "priority": "critical"|"high"|"medium"|"low",
    "affected_wp": "WP1-WP5",
    "erasmus_criteria": {"relevance":bool,"methodology":bool,"partnership":bool,"impact":bool,"inclusion":bool,"digital":bool,"sustainability":bool}
}

DECISIONS: integrate=relevant+high quality, revise=good idea needs rewording, route=wrong section, archive=future value, reject=off-topic, ethical_risk=privacy concern"""
                },
                {
                    "role": "user",
                    "content": f"SECTION: {section_key}\n\nCURRENT CONTENT:\n{section_content if section_content else '[Empty]'}\n\nFEEDBACK:\n{feedback_text}"
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3, max_tokens=1500,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "decision": "manual_review", "confidence": 0,
            "reasoning": f"AI error: {str(e)}", "target_section": section_key,
            "suggested_action": "review", "suggested_text": "",
            "priority": "medium", "affected_wp": "", "erasmus_criteria": {},
        }


def ai_generate_section_revision(section_key, section_content, feedback_text):
    if not AI_ENABLED or not ai_client:
        return "AI not configured."
    try:
        response = ai_client.chat.completions.create(
            model=ai_model,
            messages=[
                {"role": "system", "content": "You are an expert Erasmus+ KA210 proposal writer. Write in formal academic English. Be specific and measurable. Output ONLY the revised section text."},
                {"role": "user", "content": f"SECTION: {section_key}\n\nCURRENT:\n{section_content or '[Empty]'}\n\nFEEDBACK:\n{feedback_text}\n\nWrite improved version:"}
            ],
            temperature=0.4, max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI error: {str(e)}"


def ai_generate_summary(feedback_list):
    if not AI_ENABLED or not ai_client or not feedback_list:
        return "AI not available."
    try:
        fb_text = "\n".join([f"- [{f.get('section', '')}] {f.get('feedback', f.get('content', ''))}" for f in feedback_list[:20]])
        response = ai_client.chat.completions.create(
            model=ai_model,
            messages=[
                {"role": "system", "content": "Summarize key themes from these Erasmus+ KA210 partner feedback items. Be concise."},
                {"role": "user", "content": fb_text}
            ],
            temperature=0.3, max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI error: {str(e)}"


# ═══════════════════════════════════════════════════
# PROPOSAL MD PARSER
# ═══════════════════════════════════════════════════
def parse_proposal_md(md_text):
    mapping = {
        "project summary": "project_summary", "problem analysis": "problem_analysis",
        "needs analysis": "problem_analysis", "objectives": "objectives",
        "methodology": "methodology", "work packages": "work_packages",
        "partnership": "partnership", "consortium": "partnership",
        "impact": "impact", "evaluation": "evaluation", "budget": "budget",
        "dissemination": "dissemination", "ethics": "ethics_gdpr",
        "gdpr": "ethics_gdpr", "data protection": "ethics_gdpr",
        "sustainability": "sustainability",
    }
    result = {}
    current_key = None
    current_lines = []
    for line in md_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("# "):
            if current_key and current_lines:
                result[current_key] = "\n".join(current_lines).strip()
            title = stripped.lstrip("# ").strip().lower()
            current_key = None
            for keyword, sec_key in mapping.items():
                if keyword in title:
                    current_key = sec_key
                    break
            current_lines = []
        else:
            if current_key:
                current_lines.append(line)
    if current_key and current_lines:
        result[current_key] = "\n".join(current_lines).strip()
    return result


# ═══════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════
@st.cache_data
def load_csv(path):
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return pd.DataFrame()


def load_static():
    return load_csv("data/work_packages.csv"), load_csv("data/partners.csv")


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
    sub_color = "#17a2b8" if days > 365 else "#28a745" if days > 180 else "#ffc107" if days > 60 else "#dc3545"
    pct = int(prep_progress * 100)
    deg = int(prep_progress * 360)
    prep_color = "#a855f7" if prep_progress < 0.5 else "#f59e0b" if prep_progress < 0.8 else "#ef4444"

    cl, cr = st.columns(2)
    with cl:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#1a1a2e,#2d1b4e);border-radius:16px;padding:1.5rem;text-align:center;color:white;min-height:280px;'>"
            f"<p style='margin:0;font-size:.75rem;opacity:.7;letter-spacing:2px;'>PREPARATION PHASE</p>"
            f"<div style='margin:1rem auto;width:120px;height:120px;border-radius:50%;background:conic-gradient({prep_color} {deg}deg, #333 0deg);display:flex;align-items:center;justify-content:center;'>"
            f"<div style='width:100px;height:100px;border-radius:50%;background:#1a1a2e;display:flex;align-items:center;justify-content:center;flex-direction:column;'>"
            f"<span style='font-size:1.8rem;font-weight:bold;color:{prep_color};'>{pct}%</span>"
            f"<span style='font-size:.65rem;opacity:.6;'>COMPLETE</span></div></div>"
            f"<p style='margin:0;font-size:.8rem;opacity:.6;'>Started: {PREPARATION_START.strftime('%d %b %Y')} | Elapsed: {prep_elapsed} days</p></div>",
            unsafe_allow_html=True,
        )
    with cr:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);border-radius:16px;padding:1.5rem;text-align:center;color:white;min-height:280px;'>"
            f"<p style='margin:0;font-size:.75rem;opacity:.7;letter-spacing:2px;'>SUBMISSION DEADLINE</p>"
            f"<p style='margin:.3rem 0 0;font-size:.85rem;opacity:.8;'>{SUBMISSION_DEADLINE.strftime('%d %B %Y, %H:%M')}</p>"
            f"<div style='display:flex;justify-content:center;gap:1.5rem;margin:1.2rem 0;'>"
            f"<div><span style='font-size:2.8rem;font-weight:bold;color:{sub_color};'>{days}</span><br><span style='font-size:.75rem;opacity:.6;'>DAYS</span></div>"
            f"<div><span style='font-size:2.8rem;font-weight:bold;color:{sub_color};'>{hours:02d}</span><br><span style='font-size:.75rem;opacity:.6;'>HOURS</span></div>"
            f"<div><span style='font-size:2.8rem;font-weight:bold;color:{sub_color};'>{minutes:02d}</span><br><span style='font-size:.75rem;opacity:.6;'>MIN</span></div></div>"
            f"<p style='margin:0;font-size:.8rem;opacity:.6;'>Erasmus+ KA210 Expected Call 2027</p></div>",
            unsafe_allow_html=True,
        )
    st.progress(max(0.0, min(1.0, 1 - days / max(prep_total, 1))))


def ann_card(row):
    p = row.get("priority", "Low")
    icon = {"High": "🔴", "Medium": "🟡"}.get(p, "🟢")
    border = {"High": "#dc3545", "Medium": "#ffc107"}.get(p, "#28a745")
    st.markdown(
        f"<div style='border-left:4px solid {border};padding:1rem;margin-bottom:.7rem;background:#f8f9fa;border-radius:0 8px 8px 0;'>"
        f"<strong>{icon} {row.get('title', '')}</strong>"
        f"<span style='float:right;color:#666;font-size:.85rem;'>{str(row.get('created_at', ''))[:10]}</span>"
        f"<br><span style='color:#444;'>{row.get('content', '')}</span>"
        f"<br><span style='font-size:.8rem;color:#999;'>By: {row.get('author', '')}</span></div>",
        unsafe_allow_html=True,
    )


def show_access_denied():
    st.markdown(
        "<div style='background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);"
        "border-radius:12px;padding:2rem;text-align:center;margin:2rem 0;'>"
        "<h2>🔒 Access Denied</h2><p>You don't have permission to view this page.</p></div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════
def page_dashboard(wp_df, partners_df):
    role, country = get_role(), get_country()
    st.title("🧬 OncoConnect Co-Creation Hub")
    st.caption("Erasmus+ KA210 — AI-Driven Proposal Governance Platform")
    render_countdown()

    approvals = db_get_approvals()
    fb_count = len(db_get_partner_feedback())
    ai_count = len(db_get_ai_decisions())
    approved_n = sum(1 for v in approvals.values() if v)
    try:
        doc_count = len(sb().table("documents").select("id").eq("is_active", True).execute().data or []) if SUPABASE_OK else 0
    except:
        doc_count = 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Work Packages", len(wp_df) if len(wp_df) > 0 else 5)
    c2.metric("Partners", len(partners_df) if len(partners_df) > 0 else 3)
    c3.metric("Feedback", fb_count)
    c4.metric("AI Decisions", ai_count)
    c5.metric("Approvals", f"{approved_n}/3")
    c6.metric("Documents", doc_count)

    st.subheader("⚡ System Status")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        (st.success if SUPABASE_OK else st.warning)(f"🔗 Database: {'Connected' if SUPABASE_OK else 'Local'}")
    with sc2:
        (st.success if AI_ENABLED else st.warning)(f"🧠 AI: {'Active (' + ai_model + ')' if AI_ENABLED else 'Inactive'}")
    with sc3:
        (st.success if approved_n == 3 else st.warning)(f"🗳️ Approvals: {approved_n}/3")

    if role == "Partner" and country in WP_COUNTRY_MAP:
        user_wps = get_user_wps(country)
        leads = WP_COUNTRY_MAP[country]["lead"]
        st.info(f"🔒 **{country}** — WPs: {', '.join(user_wps)} | Lead: {', '.join(leads)}")

    st.subheader("🗳️ Partner Approval")
    ac1, ac2, ac3 = st.columns(3)
    for col, cn in zip([ac1, ac2, ac3], ["Turkey", "Poland", "Spain"]):
        ok = approvals.get(cn, False)
        with col:
            (st.success if ok else st.warning)(f"{FLAGS[cn]} {PARTNER_MAP[cn]} — {'Approved' if ok else 'Pending'}")

    if len(wp_df) > 0:
        ch1, ch2 = st.columns(2)
        with ch1:
            st.subheader("💰 Budget")
            if "budget_eur" in wp_df.columns:
                fig = px.pie(wp_df, names="wp_id", values="budget_eur", color_discrete_sequence=px.colors.qualitative.Set2)
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

        st.subheader("📋 Work Packages")
        if role == "Partner" and country in WP_COUNTRY_MAP:
            filtered_wp = wp_df[wp_df["wp_id"].isin(get_user_wps(country))]
        else:
            filtered_wp = wp_df
        cols = [c for c in ["wp_id", "wp_name", "lead_country", "start_month", "end_month", "status", "budget_eur"] if c in filtered_wp.columns]
        st.dataframe(filtered_wp[cols], use_container_width=True, hide_index=True)

    st.subheader("📢 Latest Announcements")
    for a in db_get_announcements()[:3]:
        ann_card(a)


# ═══════════════════════════════════════════════════
# PAGE: WORK PACKAGES
# ═══════════════════════════════════════════════════
def page_work_packages(wp_df):
    st.title("📦 Work Packages")
    role, country = get_role(), get_country()
    if len(wp_df) == 0:
        st.warning("work_packages.csv not found.")
        return
    if role == "Partner" and country in WP_COUNTRY_MAP:
        user_wps = get_user_wps(country)
        filtered = wp_df[wp_df["wp_id"].isin(user_wps)]
        st.info(f"🔒 **{country}** — visible WPs: {', '.join(user_wps)}")
    else:
        filtered = wp_df
    sel = st.selectbox("Select WP", filtered["wp_id"].tolist())
    wp = filtered[filtered["wp_id"] == sel].iloc[0]
    rl = get_wp_role(country, sel) if role == "Partner" else ""
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader(f"{wp['wp_id']}: {wp['wp_name']} {rl}")
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
            st.metric("Budget", f"€{wp['budget_eur']:,.0f}")
    st.divider()
    st.dataframe(filtered, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
# PAGE: GANTT
# ═══════════════════════════════════════════════════
def page_gantt(wp_df):
    st.title("📊 Interactive Gantt Chart")
    role, country = get_role(), get_country()
    if len(wp_df) == 0:
        st.warning("work_packages.csv not found.")
        return
    g = wp_df.copy()
    if role == "Partner" and country in WP_COUNTRY_MAP:
        user_wps = get_user_wps(country)
        g = g[g["wp_id"].isin(user_wps)]
        st.info(f"🔒 Filtered: {', '.join(user_wps)}")

    g["Start"] = g["start_month"].apply(lambda m: PROJECT_START + timedelta(days=(m - 1) * 30))
    g["Finish"] = g["end_month"].apply(lambda m: PROJECT_START + timedelta(days=m * 30))
    g["Task"] = g["wp_id"] + ": " + g["wp_name"]
    g["Duration (months)"] = g["end_month"] - g["start_month"]
    lc = "lead_country" if "lead_country" in g.columns else "lead_partner"

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        sel_c = st.multiselect("Country", g[lc].unique().tolist(), default=g[lc].unique().tolist())
    with fc2:
        sel_s = st.multiselect("Status", g["status"].unique().tolist(), default=g["status"].unique().tolist())
    with fc3:
        view = st.radio("View", ["Timeline", "Duration", "Both"], horizontal=True)

    filt = g[g[lc].isin(sel_c) & g["status"].isin(sel_s)]
    if filt.empty:
        st.warning("No WPs match.")
        return

    if view in ("Timeline", "Both"):
        fig = px.timeline(filt, x_start="Start", x_end="Finish", y="Task", color=lc,
                          color_discrete_map={"Turkey": "#e74c3c", "Poland": "#3498db", "Spain": "#f39c12"})
        fig.update_yaxes(autorange="reversed")
        today = datetime.now()
        fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, yref="paper",
                      line=dict(color="red", width=2, dash="dash"))
        milestones = [
            {"month": 1, "label": "Kickoff", "color": "#28a745"},
            {"month": 6, "label": "Needs Report", "color": "#17a2b8"},
            {"month": 10, "label": "Protocol", "color": "#f39c12"},
            {"month": 15, "label": "Pilot Done", "color": "#e74c3c"},
            {"month": 18, "label": "Final", "color": "#6f42c1"},
        ]
        for ms in milestones:
            md = PROJECT_START + timedelta(days=(ms["month"] - 1) * 30)
            fig.add_shape(type="line", x0=md, x1=md, y0=0, y1=1, yref="paper",
                          line=dict(color=ms["color"], width=1, dash="dot"))
        fig.update_layout(height=500, margin=dict(b=100))
        fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.08)
        st.plotly_chart(fig, use_container_width=True)

    if view in ("Duration", "Both"):
        fig2 = px.bar(filt, x="Duration (months)", y="Task", color=lc, orientation="h", text="Duration (months)",
                      color_discrete_map={"Turkey": "#e74c3c", "Poland": "#3498db", "Spain": "#f39c12"})
        fig2.update_traces(textposition="inside")
        fig2.update_layout(height=400, yaxis=dict(autorange="reversed"), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("WPs", len(filt))
    s2.metric("Avg Duration", f"{filt['Duration (months)'].mean():.1f} mo")
    if "budget_eur" in filt.columns:
        s3.metric("Total Budget", f"€{filt['budget_eur'].sum():,.0f}")
        s4.metric("Avg Budget", f"€{filt['budget_eur'].mean():,.0f}")


# ═══════════════════════════════════════════════════
# PAGE: PARTNERS
# ═══════════════════════════════════════════════════
def page_partners(partners_df):
    st.title("🤝 OncoConnect Consortium")
    if len(partners_df) > 0:
        for _, p in partners_df.iterrows():
            flag = FLAGS.get(p["country"], "")
            clr = "#e74c3c" if p["role"] == "Coordinator" else "#3498db"
            cn = p["country"]
            wps = get_user_wps(cn)
            leads = WP_COUNTRY_MAP.get(cn, {}).get("lead", [])
            st.markdown(
                f"<div style='border:1px solid #e0e0e0;border-radius:12px;padding:1.5rem;margin-bottom:1rem;background:white;border-left:5px solid {clr};'>"
                f"<h3 style='margin:0 0 .5rem;'>{flag} {p['organisation']}</h3>"
                f"<p><strong>Country:</strong> {cn} | <strong>Role:</strong> <span style='color:{clr};font-weight:600;'>{p['role']}</span> | <strong>Type:</strong> {p.get('type', 'N/A')}</p>"
                f"<p><strong>WPs:</strong> {', '.join(wps)} | <strong>Lead:</strong> {', '.join(leads)}</p>"
                f"<p style='color:#555;'>{p.get('description', '')}</p></div>",
                unsafe_allow_html=True,
            )
    else:
        for cn, org in PARTNER_MAP.items():
            wps = get_user_wps(cn)
            leads = WP_COUNTRY_MAP.get(cn, {}).get("lead", [])
            st.markdown(f"### {FLAGS[cn]} {org}")
            st.write(f"**WPs:** {', '.join(wps)} | **Lead:** {', '.join(leads)}")
    st.subheader("🗺️ Partner Locations")
    st.map(pd.DataFrame({"lat": [39.93, 52.23, 41.39], "lon": [32.86, 21.01, 2.17]}), zoom=3)


# ═══════════════════════════════════════════════════
# PAGE: PARTNER FEEDBACK (section-linked)
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

            section = st.selectbox("Proposal Section", PROPOSAL_SECTIONS)

            # Bölüm içeriğini göster
            section_data = _find_section_for_feedback(section)
            if section_data and section_data.get("content"):
                st.markdown("**📄 Current section content:**")
                st.markdown(
                    f"<div style='background:#f0f0f0;padding:1rem;border-radius:8px;max-height:200px;overflow-y:auto;font-size:0.9rem;color:#333;'>"
                    f"{section_data['content'][:800]}{'...' if len(section_data.get('content', '')) > 800 else ''}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("ℹ️ This section has no content yet.")

            text = st.text_area("Your Feedback", height=150, placeholder="Write your feedback about this section...")
            priority = st.select_slider("Priority", ["Low", "Medium", "High"], "Medium")
            go = st.form_submit_button("Submit Feedback", type="primary", use_container_width=True)
            if go and text.strip():
                db_add_partner_feedback(fb_country, fb_org, section, text, priority, get_name())
                st.success("✅ Feedback saved!")
                st.rerun()

    st.divider()
    rows = db_get_partner_feedback()
    if rows:
        df = pd.DataFrame(rows)
        if "section" in df.columns:
            filt = st.multiselect("Filter by Section", sorted(df["section"].unique()))
            if filt:
                df = df[df["section"].isin(filt)]
        st.dataframe(df, use_container_width=True, hide_index=True)

        if r == "Admin" and len(df) > 0:
            st.subheader("🔧 Update Status")
            fb_id = st.selectbox("Feedback ID", df["id"].tolist())
            new_st = st.selectbox("Status", ["Open", "Under Review", "Accepted", "Rejected", "Archived", "Routed"])
            resp = st.text_input("Response")
            if st.button("Update"):
                db_update_feedback_status(fb_id, new_st, resp if resp else None)
                st.rerun()

        if len(df) > 2:
            fc1, fc2 = st.columns(2)
            with fc1:
                if "section" in df.columns:
                    st.plotly_chart(px.histogram(df, x="section", color="section", title="By Section").update_layout(showlegend=False, height=350), use_container_width=True)
            with fc2:
                cc = "partner_country" if "partner_country" in df.columns else "country"
                if cc in df.columns:
                    st.plotly_chart(px.histogram(df, x=cc, color=cc, title="By Country").update_layout(showlegend=False, height=350), use_container_width=True)
    else:
        st.info("No feedback yet.")


# ═══════════════════════════════════════════════════
# PAGE: PATIENT FEEDBACK
# ═══════════════════════════════════════════════════
def page_patient_feedback():
    st.title("💚 Patient Feedback")
    r = get_role()

    if r == "Patient":
        st.write("Your voice matters.")
        with st.form("pf_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                age = st.selectbox("Age Group", ["18-30", "31-45", "46-60", "60+"])
                pf_country = st.selectbox("Country", ["Turkey", "Poland", "Spain", "Other"])
                cancer = st.selectbox("Cancer Type", ["Prefer not to say", "Breast", "Lung", "Colorectal", "Prostate", "Other"])
            with c2:
                support = st.selectbox("Needed Support", ["Peer support", "Psychological support", "Reliable information", "Treatment sharing", "Community belonging"])
                digital = st.select_slider("Digital Comfort", ["Very Low", "Low", "Medium", "High", "Very High"], "Medium")
                language = st.multiselect("Language(s)", ["Turkish", "Polish", "Spanish", "English"])
            matching = st.text_area("What matters for matching?", height=100)
            privacy = st.text_area("Privacy expectations?", height=100)
            go = st.form_submit_button("Submit", type="primary", use_container_width=True)
            if go:
                db_add_patient_feedback({
                    "age_group": age, "country": pf_country, "cancer_type": cancer,
                    "support_need": support, "digital_literacy": digital,
                    "languages": ", ".join(language), "matching_preference": matching,
                    "privacy_expectation": privacy, "content": f"{matching} | {privacy}",
                    "category": support, "rating": 0, "submitted_by": "anonymous",
                    "is_anonymous": True, "status": "New",
                })
                st.success("Thank you!")
                st.balloons()

        if r == "Admin" or st.session_state.get("can_read_patient_fb", False):
        rows = db_get_patient_feedback()
        if rows:
            st.divider()
            st.subheader("📋 Patient Feedback Data")
            if r != "Admin":
                st.warning("🔒 Read-only access (board member permission).")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            if r == "Admin" and len(rows) > 2:
                pf_df = pd.DataFrame(rows)
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
        else:
            st.info("No patient feedback yet.")
    elif r == "Partner":
        st.markdown(
            "<div style='background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);"
            "border-radius:12px;padding:2rem;text-align:center;margin:2rem 0;'>"
            "<h3>🔒 Patient Feedback is Confidential</h3>"
            "<p>Only Admin and authorized board members can view this data.</p></div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════
# PAGE: APPROVAL STATUS
# ═══════════════════════════════════════════════════
def page_approval():
    st.title("🗳️ Proposal Approval Status")
    approvals = db_get_approvals()
    r, c = get_role(), get_country()

    # Current proposal version
    current_version = 0
    latest_proposal = None
    try:
        if SUPABASE_OK:
            latest = sb().table("documents").select("*").eq("category", "proposal").eq("is_active", True).order("version", desc=True).limit(1).execute()
            if latest.data:
                current_version = latest.data[0].get("version", 0)
                latest_proposal = latest.data[0]
    except:
        pass

    # Proposal sections completeness
    sections = db_get_proposal_sections()
    filled = sum(1 for s in sections if len(s.get("content", "") or "") > 50)
    total_sec = len(sections) if sections else 12

    st.info(f"📄 Proposal Version: **v{current_version}** | Sections: **{filled}/{total_sec}** filled")

    cols = st.columns(3)
    for col, cname in zip(cols, ["Turkey", "Poland", "Spain"]):
        ok = approvals.get(cname, False)
        org = PARTNER_MAP[cname]
        with col:
            (st.success if ok else st.warning)(f"{FLAGS[cname]} {org}\n\n{'✅ APPROVED' if ok else '⏳ PENDING'}")
            can_approve = (r == "Partner" and c == cname and not ok) or (r == "Admin" and not ok)
            if can_approve:
                if st.button(f"✅ Approve {cname}", key=f"a_{cname}", use_container_width=True, type="primary"):
                    db_set_approval(cname, True, get_name(), r)
                    st.rerun()
            if r == "Admin" and ok:
                if st.button(f"↩️ Revoke {cname}", key=f"r_{cname}", use_container_width=True):
                    db_set_approval(cname, False, get_name(), r)
                    st.rerun()

    st.divider()
    n = sum(1 for v in approvals.values() if v)
    st.progress(n / 3)
    st.write(f"**{n}/3** approved")

    if n == 3:
        st.success("🎉 All partners approved! Proposal is final.")
        if r == "Admin":
            dc1, dc2, dc3 = st.columns(3)
            with dc1:
                if latest_proposal and SUPABASE_OK:
                    if st.button("📥 Download Final (Storage)", type="primary", use_container_width=True):
                        data = download_from_storage(latest_proposal["storage_path"])
                        if data:
                            st.download_button("⬇️ Save", data, latest_proposal["file_name"],
                                               "application/octet-stream", key="dl_final")
            with dc2:
                # Export proposal sections as MD
                if sections:
                    md_content = "# OncoConnect Proposal\n\n"
                    for s in sections:
                        md_content += f"## {s['section_title']}\n\n{s.get('content', '')}\n\n"
                    st.download_button("📥 Download Sections (.md)", md_content,
                                       "OncoConnect_Proposal_Sections.md", "text/markdown",
                                       use_container_width=True)
            with dc3:
                report = json.dumps({
                    "project": "OncoConnect", "programme": "Erasmus+ KA210",
                    "status": "Approved", "version": current_version,
                    "approvals": {k: v for k, v in approvals.items()},
                    "sections_filled": f"{filled}/{total_sec}",
                    "exported": datetime.now().isoformat(),
                }, indent=2)
                st.download_button("📊 Approval Report", report, "Approval_Report.json",
                                   "application/json", use_container_width=True)
        else:
            st.info("Only Admin can download.")
    else:
        waiting = [f"{FLAGS[w]} {w}" for w, v in approvals.items() if not v]
        st.warning(f"Waiting: {', '.join(waiting)}")

    if r == "Admin":
        st.divider()
        st.subheader("⚙️ Admin Controls")
        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("🔄 Reset All Approvals", use_container_width=True):
                db_reset_all_approvals(get_name())
                st.success("Approvals reset!")
                st.rerun()
        with ac2:
            st.caption("Auto-reset when new proposal version is uploaded.")

        log = db_get_approval_log()
        if log:
            st.subheader("📜 Approval Log")
            st.dataframe(pd.DataFrame(log), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
# PAGE: ANNOUNCEMENTS
# ═══════════════════════════════════════════════════
def page_announcements():
    st.title("📢 Announcements")
    r = get_role()
    for a in db_get_announcements():
        ann_card(a)
        if r == "Admin":
            if st.button("🗑️ Delete", key=f"del_ann_{a.get('id', '')}"):
                if SUPABASE_OK:
                    try:
                        sb().table("announcements").delete().eq("id", a["id"]).execute()
                        st.rerun()
                    except:
                        pass

    if r in ("Admin", "Partner"):
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
    r, c = get_role(), get_country()
    perm = get_permission("Documents", r)

    t1, t2, t3, t4 = st.tabs(["📄 Files", "📤 Upload", "📜 Proposal", "💰 Budget"])

    with t1:
        if not SUPABASE_OK:
            st.warning("Supabase not connected.")
        else:
            fcat = st.selectbox("Category", ["All", "proposal", "partner-doc", "deliverable", "meeting-notes", "financial", "ethics", "other"])
            try:
                q = sb().table("documents").select("*").eq("is_active", True).order("created_at", desc=True)
                if fcat != "All":
                    q = q.eq("category", fcat)
                docs = q.execute()
                if docs.data:
                    for doc in docs.data:
                        ci = {"proposal": "📜", "partner-doc": "📋", "deliverable": "📎", "meeting-notes": "📝", "financial": "💰", "ethics": "⚖️"}.get(doc.get("category", ""), "📁")
                        mb = (doc.get("file_size", 0) or 0) / (1024 * 1024)
                        co1, co2, co3 = st.columns([4, 1, 1])
                        with co1:
                            st.markdown(f"{ci} **{doc.get('file_name', '')}** · `{doc.get('category', '')}` · v{doc.get('version', 1)}")
                            st.caption(f"{doc.get('description', '-')} · {mb:.1f}MB · By {doc.get('uploaded_by', '')} · {str(doc.get('created_at', ''))[:10]}")
                        with co2:
                            if st.button("📥", key=f"dl_{doc['id']}"):
                                data = download_from_storage(doc["storage_path"])
                                if data:
                                    st.download_button("⬇️", data, doc["file_name"], doc.get("file_type", "application/octet-stream"), key=f"dlb_{doc['id']}")
                        with co3:
                            if r == "Admin":
                                if st.button("🗑️", key=f"dd_{doc['id']}"):
                                    delete_from_storage(doc["storage_path"])
                                    sb().table("documents").update({"is_active": False}).eq("id", doc["id"]).execute()
                                    st.rerun()
                        st.markdown("---")
                else:
                    st.info("No files uploaded yet.")
            except Exception as e:
                st.error(f"Error: {e}")

    with t2:
        if perm in ["full", "upload"]:
            with st.form("upload_form"):
                st.subheader("📤 Upload File")
                cat = st.selectbox("Category", ["proposal", "partner-doc", "deliverable", "meeting-notes", "financial", "ethics", "other"])
                desc = st.text_input("Description")
                ver = st.number_input("Version", min_value=1, value=1) if cat == "proposal" else 1
                uf = st.file_uploader("Select File", type=["pdf", "docx", "xlsx", "pptx", "md", "txt", "png", "jpg"])
                if st.form_submit_button("📤 Upload", type="primary") and uf:
                    fb = uf.read()
                    fs = len(fb)
                    if cat == "proposal":
                        sp = f"proposals/{uf.name}"
                    elif cat == "partner-doc":
                        folder = c.lower() if c not in ["All", "N/A"] else "admin"
                        sp = f"partner-docs/{folder}/{uf.name}"
                    else:
                        sp = f"{cat}/{uf.name}"
                    with st.spinner("Uploading..."):
                        ok = upload_to_storage(fb, sp, uf.type or "application/octet-stream")
                        if ok:
                            if cat == "proposal":
                                try:
                                    old = sb().table("documents").select("id").eq("category", "proposal").eq("is_active", True).execute()
                                    for o in (old.data or []):
                                        sb().table("documents").update({"is_active": False}).eq("id", o["id"]).execute()
                                except:
                                    pass
                                db_reset_all_approvals(get_name())
                                st.warning("⚠️ New proposal version — all approvals reset!")
                            save_document_metadata(uf.name, uf.type or "unknown", fs, cat, desc,
                                                   st.session_state.get("username", "unknown"),
                                                   c if c not in ["All", "N/A"] else "Admin", sp,
                                                   ver if cat == "proposal" else 1)
                            st.success(f"✅ '{uf.name}' uploaded!")
                            st.rerun()
        else:
            st.info("📖 Read-only access.")

    with t3:
        try:
            with open("documents/proposal_draft.md", "r", encoding="utf-8") as f:
                st.markdown(f.read())
                if r == "Admin":
                    f.seek(0)
                    st.download_button("Download", f.read(), "proposal_draft.md", "text/markdown", use_container_width=True)
        except FileNotFoundError:
            st.info("No local proposal file. Use Storage or Proposal Sections.")

    with t4:
        bd = pd.DataFrame({
            "WP": ["WP1", "WP2", "WP3", "WP4", "WP5"],
            "Name": ["Management", "Needs Analysis", "Development", "Pilot", "Evaluation"],
            "Budget (€)": [12000, 7000, 15000, 12000, 14000],
            "Lead": ["Turkey", "Poland", "Spain", "Turkey", "Spain"],
        })
        st.dataframe(bd, hide_index=True, use_container_width=True)
        fig = px.bar(bd, x="WP", y="Budget (€)", color="Lead", text="Budget (€)",
                     color_discrete_map={"Turkey": "#e74c3c", "Poland": "#3498db", "Spain": "#f39c12"})
        fig.update_traces(texttemplate="€%{text:,.0f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
        st.metric("Total Budget", f"€{TOTAL_BUDGET:,.0f}")


# ═══════════════════════════════════════════════════
# PAGE: AI FEEDBACK INTEGRATION CENTER
# ═══════════════════════════════════════════════════
def page_ai_center():
    st.title("🧠 AI Feedback Integration Center")
    if get_role() != "Admin":
        show_access_denied()
        return

    if AI_ENABLED:
        provider = "OpenRouter" if USE_OPENROUTER else "OpenAI"
        st.success(f"🧠 AI Engine: **Active** — {provider} ({ai_model})")
    else:
        st.warning("⚠️ AI not configured. Manual mode.")
        st.code('[openrouter]\napi_key = "sk-or-..."\nmodel = "openai/gpt-4o-mini"', language="toml")

    tabs = st.tabs(["📄 Sections", "🔍 Analyze", "📝 Revision", "📜 Log", "🤖 Decisions", "📊 Insights"])

    # ── TAB 1: Proposal Sections ──
    with tabs[0]:
        st.subheader("📄 Proposal Sections")
        sections = db_get_proposal_sections()

        if not sections:
            st.warning("No sections found.")
            if st.button("🔄 Create Sections"):
                if SUPABASE_OK:
                    for i, (key, title) in enumerate(PROPOSAL_SECTION_KEYS):
                        try:
                            sb().table("proposal_sections").insert({
                                "section_key": key, "section_title": title,
                                "section_order": i + 1, "content": "", "version": 1, "is_active": True,
                            }).execute()
                        except:
                            pass
                    st.success("Sections created!")
                    st.rerun()
            return

        sec_opts = {s["section_key"]: f"{s['section_order']}. {s['section_title']}" for s in sections}
        sel_key = st.selectbox("Select Section", list(sec_opts.keys()), format_func=lambda x: sec_opts[x])
        cur = db_get_section_by_key(sel_key)

        if cur:
            st.markdown(f"**Version:** v{cur.get('version', 1)} | **Updated:** {str(cur.get('updated_at', ''))[:10]} | **By:** {cur.get('last_updated_by', '-')}")
            content = cur.get("content", "")
            if content:
                st.markdown("#### Current Content:")
                st.markdown(content)
            else:
                st.info("Section is empty.")

            with st.expander("✏️ Edit"):
                new_c = st.text_area("Content", value=content, height=300, key=f"edit_{sel_key}")
                if st.button("💾 Save", key=f"save_{sel_key}"):
                    nv = db_update_section_content(sel_key, new_c, get_name())
                    if nv:
                        db_log_improvement(None, sel_key, content, new_c, "Manual edit", "manual_edit", get_name())
                        st.success(f"✅ Updated → v{nv}")
                        st.rerun()

            with st.expander("📤 Upload .md File"):
                st.markdown("Use `## Section Title` headers in your .md file.")
                umd = st.file_uploader("Upload .md", type=["md", "txt"], key="md_up")
                if umd and st.button("📥 Parse & Load"):
                    parsed = parse_proposal_md(umd.read().decode("utf-8"))
                    if parsed:
                        for sk, sc in parsed.items():
                            db_update_section_content(sk, sc, get_name())
                        st.success(f"✅ {len(parsed)} sections updated!")
                        st.rerun()

        st.markdown("---")
        st.markdown("#### 📊 Overview")
        overview = []
        for s in sections:
            cl = len(s.get("content", "") or "")
            overview.append({
                "#": s["section_order"], "Section": s["section_title"],
                "Chars": cl, "Status": "✅" if cl > 50 else ("⚠️" if cl > 0 else "❌"),
                "Ver": f"v{s.get('version', 1)}",
            })
        st.dataframe(pd.DataFrame(overview), use_container_width=True, hide_index=True)

    # ── TAB 2: Feedback Analysis ──
    with tabs[1]:
        st.subheader("🔍 Feedback Analysis — AI Workflow")
        all_fb = db_get_partner_feedback()
        open_fb = [f for f in all_fb if f.get("status") == "Open"]

        if not open_fb:
            st.success("✅ All feedback processed.")
        else:
            st.write(f"**{len(open_fb)} open feedback items**")
            for fb in open_fb:
                fb_text = fb.get("feedback", fb.get("content", ""))
                fb_section = fb.get("section", "General")
                fb_country = fb.get("partner_country", fb.get("country", ""))
                fb_pri = fb.get("priority", "Medium")
                pri_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(fb_pri, "⚪")

                with st.expander(f"{pri_icon} #{fb['id']} — {fb_section} — {FLAGS.get(fb_country, '')} {fb_country}"):
                    st.markdown(f"**Feedback:** {fb_text}")
                    st.caption(f"By: {fb.get('submitted_by', '')} | Priority: {fb_pri}")

                    sec_data = _find_section_for_feedback(fb_section)
                    if sec_data and sec_data.get("content"):
                        st.markdown("**📄 Section Content:**")
                        st.markdown(f"<div style='background:#f8f9fa;padding:1rem;border-radius:8px;max-height:200px;overflow-y:auto;font-size:0.9rem;'>{sec_data['content'][:500]}{'...' if len(sec_data.get('content','')) > 500 else ''}</div>", unsafe_allow_html=True)

                    st.markdown("---")
                    col_ai, col_man = st.columns([2, 1])

                    with col_ai:
                        if st.button("🧠 AI Analyze", key=f"ai_{fb['id']}", type="primary"):
                            sc = sec_data.get("content", "") if sec_data else ""
                            sk = sec_data.get("section_key", fb_section) if sec_data else fb_section
                            with st.spinner("Analyzing..."):
                                result = ai_analyze_feedback_v2(fb_text, sk, sc)
                            st.session_state[f"air_{fb['id']}"] = result

                    rk = f"air_{fb['id']}"
                    if rk in st.session_state:
                        res = st.session_state[rk]
                        dec = res.get("decision", "manual_review")
                        conf = res.get("confidence", 0)
                        reas = res.get("reasoning", "")
                        sugg = res.get("suggested_text", "")
                        tgt = res.get("target_section", "")
                        pri_ai = res.get("priority", "medium")
                        awp = res.get("affected_wp", "")
                        eras = res.get("erasmus_criteria", {})

                        st.markdown("### 🤖 AI Result")
                        bmap = {
                            "integrate": ("✅ INTEGRATE", "success"), "revise": ("📝 REVISE", "info"),
                            "route": ("🔀 ROUTE", "warning"), "archive": ("📦 ARCHIVE", "info"),
                            "reject": ("❌ REJECT", "error"), "ethical_risk": ("⚠️ ETHICAL RISK", "error"),
                        }
                        lbl, bt = bmap.get(dec, ("👁️ MANUAL REVIEW", "warning"))
                        getattr(st, bt)(f"**{lbl}** — Confidence: {conf:.0%}")
                        st.write(f"**Reasoning:** {reas}")
                        if awp:
                            st.write(f"**Affected WP:** {awp}")
                        if dec == "route" and tgt:
                            st.warning(f"🔀 Should route to **{tgt}**")

                        # Erasmus criteria
                        if eras:
                            st.markdown("**Erasmus+ Criteria:**")
                            cr_labels = {"relevance": "📋", "methodology": "🔬", "partnership": "🤝",
                                        "impact": "💥", "inclusion": "♿", "digital": "💻", "sustainability": "🌱"}
                            cr_cols = st.columns(7)
                            for i, (ck, ci) in enumerate(cr_labels.items()):
                                with cr_cols[i]:
                                    st.write(f"{'✅' if eras.get(ck) else '❌'}")
                                    st.caption(ck[:6])

                        # Suggested text
                        if sugg and dec in ("integrate", "revise"):
                            st.markdown("### 📝 AI Suggestion")
                            if sec_data and sec_data.get("content"):
                                d1, d2 = st.columns(2)
                                with d1:
                                    st.markdown("**Current:**")
                                    st.text_area("", sec_data["content"][:1000], height=200, disabled=True, key=f"old_{fb['id']}")
                                with d2:
                                    st.markdown("**AI Suggestion:**")
                                    st.text_area("", sugg, height=200, disabled=True, key=f"new_{fb['id']}")
                            else:
                                st.text_area("**AI Suggestion:**", sugg, height=200, disabled=True, key=f"new_{fb['id']}")

                        # Action buttons
                        st.markdown("### ⚡ Decision")
                        a1, a2, a3, a4, a5 = st.columns(5)
                        with a1:
                            if dec in ("integrate", "revise") and sugg:
                                if st.button("✅ Accept & Update", key=f"acc_{fb['id']}", type="primary"):
                                    sk2 = sec_data["section_key"] if sec_data else fb_section
                                    old_c = sec_data.get("content", "") if sec_data else ""
                                    new_c = (old_c + "\n\n" + sugg) if (dec == "integrate" and old_c) else sugg
                                    nv = db_update_section_content(sk2, new_c, get_name(), fb["id"])
                                    db_update_feedback_status(fb["id"], "Accepted", f"AI {dec}: {reas}")
                                    db_log_ai_decision(fb["id"], dec, conf, reas, tgt or sk2)
                                    db_log_improvement(fb["id"], sk2, old_c, new_c, reas, dec, get_name())
                                    db_reset_all_approvals(get_name())
                                    st.success(f"✅ Updated → v{nv} | Approvals reset!")
                                    st.rerun()
                        with a2:
                            if st.button("📝 Edit & Accept", key=f"ea_{fb['id']}"):
                                st.session_state[f"em_{fb['id']}"] = True
                        with a3:
                            if st.button("🔀 Route", key=f"rt_{fb['id']}"):
                                if SUPABASE_OK:
                                    sb().table("partner_feedback").update({
                                        "routed_to_section": tgt or fb_section, "status": "Routed",
                                        "ai_decision": "route", "ai_confidence": conf,
                                    }).eq("id", fb["id"]).execute()
                                db_log_ai_decision(fb["id"], "route", conf, reas, tgt or fb_section)
                                st.success(f"🔀 Routed to {tgt or fb_section}")
                                st.rerun()
                        with a4:
                            if st.button("📦 Archive", key=f"ar_{fb['id']}"):
                                db_update_feedback_status(fb["id"], "Archived", f"AI: {reas}")
                                db_log_ai_decision(fb["id"], "archive", conf, reas, tgt or fb_section)
                                st.rerun()
                        with a5:
                            if st.button("❌ Reject", key=f"rj_{fb['id']}"):
                                db_update_feedback_status(fb["id"], "Rejected", f"AI: {reas}")
                                db_log_ai_decision(fb["id"], "reject", conf, reas, fb_section)
                                st.rerun()

                        # Edit mode
                        if st.session_state.get(f"em_{fb['id']}", False):
                            st.markdown("### ✏️ Edit & Apply")
                            edited = st.text_area("Edit AI suggestion:", value=sugg or "", height=200, key=f"ed_{fb['id']}")
                            if st.button("💾 Save & Apply", key=f"se_{fb['id']}"):
                                sk2 = sec_data["section_key"] if sec_data else fb_section
                                old_c = sec_data.get("content", "") if sec_data else ""
                                new_c = (old_c + "\n\n" + edited) if old_c else edited
                                nv = db_update_section_content(sk2, new_c, get_name(), fb["id"])
                                db_update_feedback_status(fb["id"], "Accepted", f"Edited: {reas}")
                                db_log_ai_decision(fb["id"], "integrate", conf, reas, tgt or sk2)
                                db_log_improvement(fb["id"], sk2, old_c, new_c, f"Edited. AI: {reas}", "manual_integrate", get_name())
                                db_reset_all_approvals(get_name())
                                st.session_state[f"em_{fb['id']}"] = False
                                st.success(f"✅ Updated → v{nv}")
                                st.rerun()

                    with col_man:
                        st.markdown("**Manual:**")
                        ms = st.selectbox("Status", ["Open", "Under Review", "Accepted", "Rejected", "Archived", "Routed"], key=f"ms_{fb['id']}")
                        mr = st.text_input("Response", key=f"mr_{fb['id']}")
                        if st.button("Update", key=f"mu_{fb['id']}"):
                            db_update_feedback_status(fb["id"], ms, mr if mr else None)
                            st.rerun()

            st.markdown("---")
            if st.button("🧠 Bulk Analyze All", type="primary"):
                prog = st.progress(0)
                results = []
                for i, fb in enumerate(open_fb):
                    ft = fb.get("feedback", fb.get("content", ""))
                    fs = fb.get("section", "General")
                    sd = _find_section_for_feedback(fs)
                    sc = sd.get("content", "") if sd else ""
                    sk = sd.get("section_key", fs) if sd else fs
                    with st.spinner(f"#{fb['id']}..."):
                        r2 = ai_analyze_feedback_v2(ft, sk, sc)
                        results.append({"id": fb["id"], "section": fs, **r2})
                        db_log_ai_decision(fb["id"], r2.get("decision", "manual_review"),
                                           r2.get("confidence", 0), r2.get("reasoning", ""),
                                           r2.get("target_section", sk))
                    prog.progress((i + 1) / len(open_fb))
                st.success(f"✅ {len(results)} analyzed!")
                if results:
                    rdf = pd.DataFrame(results)
                    dcols = [c for c in ["id", "section", "decision", "confidence", "priority", "reasoning"] if c in rdf.columns]
                    st.dataframe(rdf[dcols], use_container_width=True, hide_index=True)

    # ── TAB 3: Revision Engine ──
    with tabs[2]:
        st.subheader("📝 AI Revision Engine")
        sections = db_get_proposal_sections()
        if sections:
            smap = {s["section_key"]: s for s in sections}
            sopts = {s["section_key"]: f"{s['section_order']}. {s['section_title']}" for s in sections}
            rs = st.selectbox("Section", list(sopts.keys()), format_func=lambda x: sopts[x], key="rev_sec")
            cur = smap.get(rs, {})
            cc = cur.get("content", "")
            if cc:
                st.text_area("Current:", cc, height=200, disabled=True, key="rc")
            else:
                st.info("Empty section.")
            instr = st.text_area("Revision instruction / feedback", height=100, placeholder="E.g. 'Add patient experience metrics'")
            if st.button("🧠 AI Revise", type="primary"):
                if instr:
                    with st.spinner("Revising..."):
                        revised = ai_generate_section_revision(rs, cc, instr)
                    st.session_state["rev_result"] = {"key": rs, "old": cc, "new": revised, "instr": instr}
                else:
                    st.warning("Enter instruction.")

            if "rev_result" in st.session_state and st.session_state["rev_result"]["key"] == rs:
                rv = st.session_state["rev_result"]
                st.markdown("---")
                rc1, rc2 = st.columns(2)
                with rc1:
                    st.markdown("**🔴 OLD:**")
                    st.text_area("", rv["old"] or "[Empty]", height=300, disabled=True, key="ro")
                with rc2:
                    st.markdown("**🟢 NEW:**")
                    edited_rev = st.text_area("", rv["new"], height=300, key="rn")
                br1, br2 = st.columns(2)
                with br1:
                    if st.button("✅ Accept & Save", type="primary", key="ra"):
                        nv = db_update_section_content(rs, edited_rev, get_name())
                        db_log_improvement(None, rs, rv["old"], edited_rev, f"AI revision: {rv['instr']}", "ai_revision", get_name())
                        db_reset_all_approvals(get_name())
                        del st.session_state["rev_result"]
                        st.success(f"✅ Updated → v{nv} | Approvals reset!")
                        st.rerun()
                with br2:
                    if st.button("❌ Cancel", key="rx"):
                        del st.session_state["rev_result"]
                        st.rerun()

    # ── TAB 4: Improvement Log ──
    with tabs[3]:
        st.subheader("📜 Improvement Log")
        log = db_get_improvement_log()
        if log:
            ldf = pd.DataFrame(log)
            st.dataframe(ldf, use_container_width=True, hide_index=True)
            l1, l2 = st.columns(2)
            with l1:
                if "action" in ldf.columns:
                    st.plotly_chart(px.pie(ldf, names="action", title="Actions"), use_container_width=True)
            with l2:
                if "section" in ldf.columns:
                    st.plotly_chart(px.histogram(ldf, x="section", title="By Section").update_layout(showlegend=False), use_container_width=True)
        else:
            st.info("No logs yet.")

    # ── TAB 5: AI Decisions ──
    with tabs[4]:
        st.subheader("🤖 AI Decision History")
        decs = db_get_ai_decisions()
        if decs:
            ddf = pd.DataFrame(decs)
            st.dataframe(ddf, use_container_width=True, hide_index=True)
            d1, d2, d3 = st.columns(3)
            with d1:
                if "decision" in ddf.columns:
                    st.plotly_chart(px.pie(ddf, names="decision", title="Decisions",
                                          color_discrete_map={"integrate": "#28a745", "revise": "#17a2b8", "archive": "#6c757d",
                                                              "route": "#ffc107", "reject": "#dc3545", "ethical_risk": "#ff6b6b"}), use_container_width=True)
            with d2:
                if "confidence" in ddf.columns:
                    st.plotly_chart(px.histogram(ddf, x="confidence", nbins=10, title="Confidence"), use_container_width=True)
            with d3:
                if "target_section" in ddf.columns:
                    st.plotly_chart(px.histogram(ddf, x="target_section", title="By Section").update_layout(showlegend=False), use_container_width=True)
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total", len(ddf))
            if "confidence" in ddf.columns:
                s2.metric("Avg Conf", f"{ddf['confidence'].mean():.0%}")
            if "decision" in ddf.columns:
                s3.metric("Integrated", len(ddf[ddf["decision"].isin(["integrate", "revise"])]))
                s4.metric("Rejected", len(ddf[ddf["decision"] == "reject"]))
        else:
            st.info("No AI decisions yet.")

    # ── TAB 6: Insights ──
    with tabs[5]:
        st.subheader("📊 Insights")
        afb = db_get_partner_feedback()
        pfb = db_get_patient_feedback()
        if not afb and not pfb:
            st.info("No data.")
        else:
            st.write(f"**{len(afb)}** partner | **{len(pfb)}** patient feedback")
            if st.button("🧠 Generate Summary", type="primary"):
                with st.spinner("Summarizing..."):
                    st.session_state["ai_summary"] = ai_generate_summary(afb)
            if "ai_summary" in st.session_state:
                st.markdown("### Summary")
                st.markdown(st.session_state["ai_summary"])
            if afb:
                fdf = pd.DataFrame(afb)
                i1, i2 = st.columns(2)
                with i1:
                    if "section" in fdf.columns:
                        st.markdown("**Top Sections:**")
                        for s, n in fdf["section"].value_counts().head(5).items():
                            st.write(f"- {s}: {n}")
                with i2:
                    if "priority" in fdf.columns:
                        for p, n in fdf["priority"].value_counts().items():
                            st.write(f"- {'🔴' if p == 'High' else '🟡' if p == 'Medium' else '🟢'} {p}: {n}")
                if "status" in fdf.columns:
                    sc = fdf["status"].value_counts()
                    st.plotly_chart(px.funnel(x=sc.values, y=sc.index, title="Pipeline"), use_container_width=True)


# ═══════════════════════════════════════════════════
# PAGE: ADMIN PANEL
# ═══════════════════════════════════════════════════
def page_admin():
    st.title("🛡️ Admin Panel")
    if get_role() != "Admin":
        show_access_denied()
        return

    t1, t2, t3, t4 = st.tabs(["📊 Overview", "🗃️ Data", "📤 Export", "🛠️ System"])

    with t1:
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Feedback", len(db_get_partner_feedback()))
        m2.metric("Patient FB", len(db_get_patient_feedback()))
        m3.metric("AI Decisions", len(db_get_ai_decisions()))
        m4.metric("Improvements", len(db_get_improvement_log()))
        ap = db_get_approvals()
        m5.metric("Approvals", f"{sum(1 for v in ap.values() if v)}/3")
        try:
            dc = len(sb().table("documents").select("id").eq("is_active", True).execute().data or []) if SUPABASE_OK else 0
        except:
            dc = 0
        m6.metric("Documents", dc)

        st.subheader("⚡ System")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            (st.success if SUPABASE_OK else st.warning)(f"DB: {'Connected' if SUPABASE_OK else 'Local'}")
        with s2:
            prov = f"{'OpenRouter' if USE_OPENROUTER else 'OpenAI'} ({ai_model})" if AI_ENABLED else "Inactive"
            (st.success if AI_ENABLED else st.warning)(f"AI: {prov}")
        with s3:
            try:
                uc = len(sb().table("app_users").select("id").eq("is_active", True).execute().data or []) if SUPABASE_OK else len(USERS_DB)
            except:
                uc = len(USERS_DB)
            st.info(f"Users: {uc}")
        with s4:
            secs = db_get_proposal_sections()
            filled = sum(1 for s in secs if len(s.get("content", "") or "") > 50)
            st.info(f"Sections: {filled}/{len(secs)}")

        # Permission matrix
        st.subheader("🔒 Permission Matrix")
        mx = []
        for pg, roles in PAGE_PERMISSIONS.items():
            row = {"Page": pg}
            for rn in ["Admin", "Partner", "Patient"]:
                pm = roles.get(rn, "none")
                row[rn] = {"full": "✅", "read": "👁️", "write": "✍️", "filtered": "🔒", "own": "🔒", "upload": "📤", "none": "❌"}.get(pm, pm)
            mx.append(row)
        st.dataframe(pd.DataFrame(mx), use_container_width=True, hide_index=True)

        st.subheader("📋 WP Access Matrix")
        wm = []
        for wp in ["WP1", "WP2", "WP3", "WP4", "WP5"]:
            row = {"WP": wp}
            for cn in ["Turkey", "Poland", "Spain"]:
                row[f"{FLAGS[cn]} {cn}"] = get_wp_role(cn, wp)
            wm.append(row)
        st.dataframe(pd.DataFrame(wm), use_container_width=True, hide_index=True)

    with t2:
        if SUPABASE_OK:
            tables = ["app_users", "documents", "partner_feedback", "patient_feedback", "approvals",
                       "approval_log", "announcements", "improvement_log", "ai_decisions", "proposal_sections"]
            sel = st.selectbox("Table", tables)
            if st.button("📋 Load"):
                try:
                    res = sb().table(sel).select("*").order("created_at", desc=True).limit(50).execute()
                    if res.data:
                        df = pd.DataFrame(res.data)
                        if "password_hash" in df.columns:
                            df["password_hash"] = "****"
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info("Empty.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with t3:
        export = {
            "project": "OncoConnect", "programme": "Erasmus+ KA210",
            "exported_at": datetime.now().isoformat(),
            "system": {"supabase": SUPABASE_OK, "ai": AI_ENABLED, "model": ai_model},
            "approvals": db_get_approvals(), "approval_log": db_get_approval_log(),
            "partner_feedback": db_get_partner_feedback(), "patient_feedback": db_get_patient_feedback(),
            "ai_decisions": db_get_ai_decisions(), "improvement_log": db_get_improvement_log(),
            "announcements": db_get_announcements(),
        }
        st.download_button("📥 Export All (JSON)",
                           json.dumps(export, indent=2, ensure_ascii=False, default=str),
                           "oncoconnect_export.json", "application/json",
                           use_container_width=True, type="primary")

    with t4:
        st.warning("⚠️ Irreversible actions!")
        r1, r2, r3 = st.columns(3)
        with r1:
            if st.button("🔄 Reset Approvals", use_container_width=True):
                db_reset_all_approvals(get_name())
                st.success("Reset!")
                st.rerun()
        with r2:
            if st.button("🗑️ Archive Resolved", use_container_width=True):
                if SUPABASE_OK:
                    try:
                        rv = sb().table("partner_feedback").select("id").eq("status", "Resolved").execute()
                        for ri in (rv.data or []):
                            sb().table("partner_feedback").update({"status": "Archived"}).eq("id", ri["id"]).execute()
                        st.success(f"{len(rv.data or [])} archived.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        with r3:
            st.json({
                "supabase": SUPABASE_OK, "ai": AI_ENABLED,
                "provider": "OpenRouter" if USE_OPENROUTER else "OpenAI" if AI_ENABLED else "None",
                "model": ai_model, "deadline": SUBMISSION_DEADLINE.isoformat(),
                "budget": TOTAL_BUDGET, "bucket": BUCKET,
            })


# ═══════════════════════════════════════════════════
# PAGE: USER MANAGEMENT
# ═══════════════════════════════════════════════════
def page_user_management():
    st.title("👥 User Management")
    if get_role() != "Admin":
        show_access_denied()
        return
    if not SUPABASE_OK:
        st.warning("Requires Supabase.")
        for un, ud in USERS_DB.items():
            st.write(f"**{un}** — {ud['name']} ({ud['role']}) — {ud['country']}")
        return

    t1, t2 = st.tabs(["📋 Users", "➕ New User"])

    with t1:
        try:
            users = sb().table("app_users").select("*").order("created_at", desc=True).execute()
            if users.data:
                for u in users.data:
                    ai = "🟢" if u["is_active"] else "🔴"
                    ri = {"Admin": "🛡️", "Partner": "🤝", "Patient": "💚"}.get(u["role"], "👤")
                    fl = FLAGS.get(u.get("country", ""), "")
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    with c1:
                        st.markdown(f"{ai} **{u['display_name']}** (`{u['username']}`) {fl} {u.get('organisation', '')}")
                    with c2:
                        st.write(f"{ri} {u['role']}")
                    with c3:
                        st.caption(f"PFB: {'✅' if u.get('can_read_patient_fb') else '❌'}")
                    with c4:
                        if u["username"] != "admin":
                            ns = not u["is_active"]
                            if st.button("🔴" if u["is_active"] else "🟢", key=f"tg_{u['id']}"):
                                sb().table("app_users").update({"is_active": ns}).eq("id", u["id"]).execute()
                                st.rerun()

                    with st.expander(f"✏️ Edit: {u['username']}"):
                        with st.form(f"ed_{u['id']}"):
                            nd = st.text_input("Name", value=u["display_name"], key=f"dn_{u['id']}")
                            nr = st.selectbox("Role", ["Admin", "Partner", "Patient"],
                                              index=["Admin", "Partner", "Patient"].index(u["role"]), key=f"rl_{u['id']}")
                            nc = st.selectbox("Country", ["All", "Turkey", "Poland", "Spain", "N/A"],
                                              index=["All", "Turkey", "Poland", "Spain", "N/A"].index(u.get("country", "N/A")), key=f"ct_{u['id']}")
                            no = st.text_input("Org", value=u.get("organisation", ""), key=f"og_{u['id']}")
                            np = st.checkbox("Patient FB Read", value=u.get("can_read_patient_fb", False), key=f"pf_{u['id']}")
                            nw = st.text_input("New Password (blank=unchanged)", type="password", key=f"pw_{u['id']}")
                            if st.form_submit_button("💾 Save"):
                                upd = {"display_name": nd, "role": nr, "country": nc, "organisation": no, "can_read_patient_fb": np}
                                if nw:
                                    upd["password_hash"] = nw
                                sb().table("app_users").update(upd).eq("id", u["id"]).execute()
                                st.success(f"✅ {u['username']} updated!")
                                st.rerun()
                    st.markdown("---")
        except Exception as e:
            st.error(f"Error: {e}")

    with t2:
        with st.form("new_user"):
            un = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            dn = st.text_input("Display Name")
            rl = st.selectbox("Role", ["Partner", "Patient", "Admin"])
            ct = st.selectbox("Country", ["Turkey", "Poland", "Spain", "N/A", "All"])
            og = st.text_input("Organisation")
            pf = st.checkbox("Patient FB Read", False)
            if st.form_submit_button("➕ Add", type="primary"):
                if not un or not pw or not dn:
                    st.error("Username, password, and name required!")
                else:
                    try:
                        ex = sb().table("app_users").select("id").eq("username", un.strip().lower()).execute()
                        if ex.data:
                            st.error("Username exists!")
                        else:
                            sb().table("app_users").insert({
                                "username": un.strip().lower(), "password_hash": pw,
                                "display_name": dn, "role": rl, "country": ct,
                                "organisation": og, "is_active": True,
                                "can_read_patient_fb": pf, "created_by": st.session_state.get("username", "admin"),
                            }).execute()
                            st.success(f"✅ '{un}' created!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════
def main():
    init_session()
    if not render_login():
        return

    wp_df, partners_df = load_static()
    r = get_role()
    c = get_country()

    # Sidebar
    st.sidebar.markdown("### 🧬 OncoConnect")
    st.sidebar.caption("Erasmus+ KA210")
    st.sidebar.write(f"**{get_name()}** ({ROLE_BADGES.get(r, r)})")
    if r == "Partner":
        st.sidebar.write(f"{FLAGS.get(c, '')} {get_org()}")
        wps = get_user_wps(c)
        leads = WP_COUNTRY_MAP.get(c, {}).get("lead", [])
        st.sidebar.caption(f"WPs: {', '.join(wps)} | Lead: {', '.join(leads)}")
    st.sidebar.divider()

    if r == "Admin":
        pages = ["Dashboard", "Work Packages", "Gantt Chart", "Partners",
                 "Partner Feedback", "Patient Feedback", "Approval Status",
                 "Announcements", "Documents", "🧠 AI Center", "Admin Panel", "User Management"]
    elif r == "Partner":
        pages = ["Dashboard", "Work Packages", "Gantt Chart", "Partners",
                 "Partner Feedback", "Patient Feedback", "Approval Status",
                 "Announcements", "Documents"]
    else:
        pages = ["Dashboard", "Partners", "Patient Feedback", "Announcements", "Documents"]

    page = st.sidebar.radio("Navigation", pages)
    st.sidebar.divider()
    (st.sidebar.success if SUPABASE_OK else st.sidebar.warning)(f"DB: {'Connected' if SUPABASE_OK else 'Local'}")
    if AI_ENABLED:
        st.sidebar.success(f"AI: {'OpenRouter' if USE_OPENROUTER else 'OpenAI'}")
    else:
        st.sidebar.info("AI: Inactive")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()

    if not check_access(page, r):
        show_access_denied()
        return

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
    elif page == "User Management":
        page_user_management()


if __name__ == "__main__":
    main()
