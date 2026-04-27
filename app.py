"""
OncoConnect Co-Creation Hub v4.0
Erasmus+ KA210 — AI-Driven Proposal Governance Platform
Full Auth + Storage + AI Engine + Meetings + Export
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json, time, io
from datetime import datetime, timedelta, date, time as dt_time
from io import BytesIO

# ═══════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════
st.set_page_config(page_title="OncoConnect Co-Creation Hub", page_icon="🧬", layout="wide", initial_sidebar_state="expanded")

# ═══════════════════════════════════════
# SUPABASE
# ═══════════════════════════════════════
SUPABASE_OK = False
try:
    from supabase import create_client, Client
    @st.cache_resource
    def get_supabase() -> Client:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    _client = get_supabase()
    SUPABASE_OK = True
except Exception:
    SUPABASE_OK = False

def sb():
    return get_supabase() if SUPABASE_OK else None

# ═══════════════════════════════════════
# AI ENGINE — OpenRouter / OpenAI
# ═══════════════════════════════════════
AI_ENABLED = False
USE_OPENROUTER = False
ai_client = None
ai_model = "gpt-4o-mini"
try:
    import openai
    ork = st.secrets.get("openrouter", {}).get("api_key", "")
    oak = st.secrets.get("openai", {}).get("api_key", "")
    if ork:
        ai_client = openai.OpenAI(api_key=ork, base_url="https://openrouter.ai/api/v1")
        ai_model = st.secrets.get("openrouter", {}).get("model", "openai/gpt-4o-mini")
        AI_ENABLED = True; USE_OPENROUTER = True
    elif oak:
        ai_client = openai.OpenAI(api_key=oak)
        AI_ENABLED = True
except Exception:
    pass

# ═══════════════════════════════════════
# PDF / EXCEL
# ═══════════════════════════════════════
try:
    from fpdf import FPDF
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    EXPORT_OK = True
except ImportError:
    EXPORT_OK = False

# ═══════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════
SUBMISSION_DEADLINE = datetime(2027, 5, 15, 17, 0, 0)
PREPARATION_START = datetime(2025, 6, 5)
PROJECT_START = datetime(2025, 9, 1)
TOTAL_BUDGET = 60000
BUCKET = "oncoconnect-files"

PARTNER_MAP = {"Turkey": "Kanser Savaşçıları Derneği", "Poland": "Fundacja Onkologiczna Rakiety", "Spain": "Universitat de Barcelona"}
FLAGS = {"Turkey": "🇹🇷", "Poland": "🇵🇱", "Spain": "🇪🇸"}
ROLE_BADGES = {"Admin": "🛡️ Admin", "Partner": "🤝 Partner", "Patient": "💚 Patient"}
PROPOSAL_SECTIONS = ["Project Summary", "Problem Analysis", "Objectives", "Methodology", "Work Packages", "Partnership", "Impact", "Evaluation", "Budget", "Dissemination", "Ethics / GDPR", "Sustainability"]
PROPOSAL_SECTION_KEYS = [(s.lower().replace(" ", "_").replace("/", "").replace("  ", "_").strip("_"), s) for s in PROPOSAL_SECTIONS]
# Fix keys
PROPOSAL_SECTION_KEYS = [
    ("project_summary", "Project Summary"), ("problem_analysis", "Problem Analysis"),
    ("objectives", "Objectives"), ("methodology", "Methodology"),
    ("work_packages", "Work Packages"), ("partnership", "Partnership"),
    ("impact", "Impact"), ("evaluation", "Evaluation"), ("budget", "Budget"),
    ("dissemination", "Dissemination"), ("ethics_gdpr", "Ethics / GDPR"),
    ("sustainability", "Sustainability"),
]

USERS_DB = {
    "admin": {"password": "admin123", "name": "Project Admin", "role": "Admin", "country": "All", "org": "OncoConnect", "can_read_patient_fb": True},
    "turkey": {"password": "tr2025", "name": "KSD Coordinator", "role": "Partner", "country": "Turkey", "org": "Kanser Savaşçıları Derneği", "can_read_patient_fb": False},
    "poland": {"password": "pl2025", "name": "Rakiety Team", "role": "Partner", "country": "Poland", "org": "Fundacja Onkologiczna Rakiety", "can_read_patient_fb": False},
    "spain": {"password": "es2025", "name": "UB Research Team", "role": "Partner", "country": "Spain", "org": "Universitat de Barcelona", "can_read_patient_fb": False},
    "patient": {"password": "patient123", "name": "Patient Participant", "role": "Patient", "country": "N/A", "org": "N/A", "can_read_patient_fb": False},
}

WP_COUNTRY_MAP = {
    "Turkey": {"lead": ["WP1", "WP4"], "support": ["WP2", "WP3", "WP5"]},
    "Poland": {"lead": ["WP2"], "support": ["WP3", "WP4", "WP5"]},
    "Spain": {"lead": ["WP3", "WP5"], "support": ["WP2", "WP4"]},
}

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
    "Meetings": {"Admin": "full", "Partner": "read", "Patient": "read"},
    "🧠 AI Center": {"Admin": "full", "Partner": "none", "Patient": "none"},
    "Admin Panel": {"Admin": "full", "Partner": "none", "Patient": "none"},
    "User Management": {"Admin": "full", "Partner": "none", "Patient": "none"},
}

def get_user_wps(country):
    if country == "All": return ["WP1","WP2","WP3","WP4","WP5"]
    m = WP_COUNTRY_MAP.get(country, {})
    return m.get("lead", []) + m.get("support", [])

def get_wp_role(country, wp):
    m = WP_COUNTRY_MAP.get(country, {})
    if wp in m.get("lead", []): return "🟢 Lead"
    if wp in m.get("support", []): return "🔵 Support"
    return "⚪ —"

def check_access(page, role): return PAGE_PERMISSIONS.get(page, {}).get(role, "none") != "none"
def get_permission(page, role): return PAGE_PERMISSIONS.get(page, {}).get(role, "none")

# ═══════════════════════════════════════
# PROFESSIONAL CSS
# ═══════════════════════════════════════
def inject_pro_css():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Global */
    .stApp { font-family: 'Inter', sans-serif; }
    
    /* Header */
    .pro-header {
        background: linear-gradient(135deg, #1B3A5C 0%, #2d5a8e 50%, #2ABFBF 100%);
        padding: 2rem 2.5rem; border-radius: 20px; margin-bottom: 2rem;
        color: white; position: relative; overflow: hidden;
        box-shadow: 0 10px 40px rgba(27,58,92,0.3);
    }
    .pro-header::before {
        content: ''; position: absolute; top: -50%; right: -20%;
        width: 300px; height: 300px; border-radius: 50%;
        background: rgba(255,255,255,0.05);
    }
    .pro-header h1 { margin: 0; font-size: 2rem; font-weight: 800; letter-spacing: -0.5px; }
    .pro-header p { margin: 0.3rem 0 0; opacity: 0.85; font-size: 0.95rem; font-weight: 300; }
    
    /* Metric Cards */
    .metric-card {
        background: linear-gradient(145deg, #ffffff, #f8f9fc);
        border: 1px solid #e8ecf1; border-radius: 16px;
        padding: 1.5rem; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        transition: transform 0.2s, box-shadow 0.2s;
        border-top: 4px solid #2ABFBF;
    }
    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
    .metric-card .value { font-size: 2.2rem; font-weight: 800; color: #1B3A5C; }
    .metric-card .label { font-size: 0.8rem; color: #8896a6; margin-top: 0.3rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Meeting Cards */
    .meeting-card {
        background: white; border: 1px solid #e8ecf1;
        border-radius: 16px; padding: 1.5rem;
        margin-bottom: 1rem; border-left: 5px solid #2ABFBF;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        transition: all 0.2s;
    }
    .meeting-card:hover { box-shadow: 0 5px 20px rgba(0,0,0,0.08); transform: translateY(-1px); }
    .meeting-card.past { border-left-color: #94a3b8; opacity: 0.7; }
    .meeting-card.today { border-left-color: #10B981; background: linear-gradient(135deg, #f0fdf4, #ffffff); }
    
    .meeting-date { font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .meeting-title { font-size: 1.2rem; font-weight: 700; color: #1B3A5C; margin: 0.3rem 0; }
    .meeting-time { font-size: 1rem; color: #2ABFBF; font-weight: 600; }
    .meeting-meta { font-size: 0.85rem; color: #64748b; margin-top: 0.5rem; }
    
    .zoom-btn {
        display: inline-block; background: linear-gradient(135deg, #2D8CFF, #2681F2);
        color: white !important; padding: 8px 20px; border-radius: 10px;
        font-weight: 600; font-size: 0.85rem; text-decoration: none;
        box-shadow: 0 3px 10px rgba(45,140,255,0.3); transition: all 0.2s;
        margin-top: 0.5rem;
    }
    .zoom-btn:hover { transform: translateY(-1px); box-shadow: 0 5px 15px rgba(45,140,255,0.4); }
    
    /* Status badges */
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .badge-success { background: #dcfce7; color: #16a34a; }
    .badge-warning { background: #fef9c3; color: #ca8a04; }
    .badge-danger { background: #fee2e2; color: #dc2626; }
    .badge-info { background: #dbeafe; color: #2563eb; }
    .badge-purple { background: #f3e8ff; color: #9333ea; }
    
    /* Feedback card */
    .fb-card {
        background: white; border: 1px solid #e8ecf1;
        border-radius: 12px; padding: 1.2rem; margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    
    /* Countdown */
    .countdown-box {
        border-radius: 16px; padding: 1.5rem; text-align: center;
        color: white; min-height: 280px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    /* Sidebar */
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0a1628 0%, #1B3A5C 100%); }
    div[data-testid="stSidebar"] .stMarkdown { color: #cbd5e1; }
    
    /* Buttons */
    .stButton > button { border-radius: 10px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.3px; }
    .stButton > button:hover { transform: translateY(-1px); }
    
    /* Announcements */
    .ann-card {
        border-left: 4px solid; padding: 1rem 1.2rem; margin-bottom: 0.7rem;
        background: white; border-radius: 0 12px 12px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    /* Access denied */
    .access-denied {
        background: linear-gradient(135deg, #fef2f2, #fff1f2);
        border: 1px solid #fecaca; border-radius: 16px;
        padding: 3rem; text-align: center; margin: 2rem 0;
    }
    
    /* Tables */
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    </style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# AUTH
# ═══════════════════════════════════════
def init_session():
    for k, v in {"authenticated": False, "username": None, "user_name": None, "user_role": None,
                  "user_country": None, "user_org": None, "can_read_patient_fb": False}.items():
        if k not in st.session_state: st.session_state[k] = v

def render_login():
    if st.session_state.get("authenticated"): return True
    inject_pro_css()
    st.markdown("<div style='text-align:center;padding:3rem 0 1rem;'><h1 style='font-size:3rem;'>🧬 OncoConnect</h1><h3 style='color:#64748b;font-weight:400;'>Co-Creation Hub</h3><p style='color:#94a3b8;'>Erasmus+ KA210 — AI-Driven Proposal Governance</p></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login"):
            username = st.text_input("Username", placeholder="admin / turkey / poland / spain / patient")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True, type="primary"):
                ud = None
                if SUPABASE_OK:
                    try:
                        res = sb().table("app_users").select("*").eq("username", username.strip().lower()).eq("is_active", True).execute()
                        if res.data:
                            u = res.data[0]
                            if u["password_hash"] == password:
                                ud = {"name": u["display_name"], "role": u["role"], "country": u["country"],
                                      "org": u.get("organisation", "N/A"), "can_read_patient_fb": u.get("can_read_patient_fb", False)}
                    except: pass
                if not ud:
                    u = USERS_DB.get(username)
                    if u and u["password"] == password:
                        ud = {"name": u["name"], "role": u["role"], "country": u["country"], "org": u["org"], "can_read_patient_fb": u.get("can_read_patient_fb", False)}
                if ud:
                    st.session_state.update(authenticated=True, username=username.strip().lower(), user_name=ud["name"], user_role=ud["role"], user_country=ud["country"], user_org=ud["org"], can_read_patient_fb=ud["can_read_patient_fb"])
                    st.rerun()
                else: st.error("Invalid credentials")
        with st.expander("Demo Credentials"):
            st.markdown("| User | Pass | Role |\n|---|---|---|\n| admin | admin123 | Admin |\n| turkey | tr2025 | Partner TR |\n| poland | pl2025 | Partner PL |\n| spain | es2025 | Partner ES |\n| patient | patient123 | Patient |")
    return False

def logout():
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

def get_role(): return st.session_state.get("user_role", "Patient")
def get_country(): return st.session_state.get("user_country", "N/A")
def get_name(): return st.session_state.get("user_name", "User")
def get_org(): return st.session_state.get("user_org", "N/A")

# ═══════════════════════════════════════
# STORAGE
# ═══════════════════════════════════════
def upload_to_storage(fb, path, ct="application/octet-stream"):
    if not SUPABASE_OK: return False
    try: sb().storage.from_(BUCKET).upload(path=path, file=fb, file_options={"content-type": ct, "upsert": "true"}); return True
    except Exception as e: st.error(f"Upload error: {e}"); return False

def download_from_storage(path):
    if not SUPABASE_OK: return None
    try: return sb().storage.from_(BUCKET).download(path)
    except: return None

def delete_from_storage(path):
    if not SUPABASE_OK: return False
    try: sb().storage.from_(BUCKET).remove([path]); return True
    except: return False

def save_document_metadata(fn, ft, fs, cat, desc, ub, co, sp, ver=1):
    if not SUPABASE_OK: return
    try: sb().table("documents").insert({"file_name": fn, "file_type": ft, "file_size": fs, "category": cat, "description": desc, "uploaded_by": ub, "country": co, "storage_path": sp, "version": ver, "is_active": True}).execute()
    except Exception as e: st.error(f"Error: {e}")

# ═══════════════════════════════════════
# DB — ALL FUNCTIONS
# ═══════════════════════════════════════
def db_get_approvals():
    d = {"Turkey": False, "Poland": False, "Spain": False}
    if not SUPABASE_OK: return st.session_state.get("local_approvals", d)
    try:
        r = sb().table("approvals").select("country, approved").execute()
        res = {x["country"]: x.get("approved", False) for x in (r.data or [])}
        for c in d: res.setdefault(c, False)
        return res
    except: return d

def db_set_approval(cn, approved, by, role):
    now = datetime.utcnow().isoformat()
    if not SUPABASE_OK:
        st.session_state.setdefault("local_approvals", {"Turkey": False, "Poland": False, "Spain": False})[cn] = approved; return
    try:
        sb().table("approvals").update({"approved": approved, "status": "Approved" if approved else "Pending", "approved_by": by if approved else None, "approved_at": now if approved else None, "updated_at": now}).eq("country", cn).execute()
        sb().table("approval_log").insert({"action": "approved" if approved else "revoked", "country": cn, "performed_by": by, "role": role}).execute()
    except Exception as e: st.error(f"Error: {e}")

def db_reset_all_approvals(by):
    for c in ["Turkey", "Poland", "Spain"]: db_set_approval(c, False, by, "Admin")

def db_get_approval_log():
    if not SUPABASE_OK: return []
    try: return sb().table("approval_log").select("*").order("created_at", desc=True).execute().data or []
    except: return []

def db_get_partner_feedback():
    if not SUPABASE_OK: return st.session_state.get("local_feedback", [])
    try: return sb().table("partner_feedback").select("*").order("created_at", desc=True).execute().data or []
    except: return []

def db_add_partner_feedback(pc, org, sec, fb, pri, by):
    if not SUPABASE_OK:
        st.session_state.setdefault("local_feedback", []).append({"id": len(st.session_state.get("local_feedback", [])) + 1, "partner_country": pc, "organisation": org, "section": sec, "feedback": fb, "content": fb, "priority": pri, "status": "Open", "submitted_by": by, "country": pc, "created_at": datetime.now().isoformat()}); return
    try: sb().table("partner_feedback").insert({"partner_country": pc, "organisation": org, "section": sec, "feedback": fb, "content": fb, "priority": pri, "status": "Open", "submitted_by": by, "country": pc}).execute()
    except Exception as e: st.error(f"Error: {e}")

def db_update_feedback_status(fid, st2, resp=None):
    if not SUPABASE_OK: return
    try:
        d = {"status": st2}
        if resp: d["response"] = resp
        sb().table("partner_feedback").update(d).eq("id", fid).execute()
    except Exception as e: st.error(f"Error: {e}")

def db_get_patient_feedback():
    if not SUPABASE_OK: return st.session_state.get("local_patient_fb", [])
    try: return sb().table("patient_feedback").select("*").order("created_at", desc=True).execute().data or []
    except: return []

def db_add_patient_feedback(data):
    if not SUPABASE_OK:
        data["id"] = len(st.session_state.get("local_patient_fb", [])) + 1; data["created_at"] = datetime.now().isoformat()
        st.session_state.setdefault("local_patient_fb", []).append(data); return
    try: sb().table("patient_feedback").insert(data).execute()
    except Exception as e: st.error(f"Error: {e}")

def db_get_announcements():
    if not SUPABASE_OK: return st.session_state.get("local_ann", [])
    try: return sb().table("announcements").select("*").order("created_at", desc=True).execute().data or []
    except: return []

def db_add_announcement(title, content, author, priority):
    if not SUPABASE_OK:
        st.session_state.setdefault("local_ann", []).append({"id": len(st.session_state.get("local_ann", [])) + 1, "title": title, "content": content, "author": author, "priority": priority, "created_at": datetime.now().isoformat()}); return
    try: sb().table("announcements").insert({"title": title, "content": content, "author": author, "priority": priority}).execute()
    except Exception as e: st.error(f"Error: {e}")

def db_log_improvement(fid, sec, old, new, reason, action, by):
    if not SUPABASE_OK:
        st.session_state.setdefault("local_imp", []).append({"id": len(st.session_state.get("local_imp", [])) + 1, "feedback_id": fid, "section": sec, "original_text": old, "updated_text": new, "ai_reasoning": reason, "action": action, "created_by": by, "created_at": datetime.now().isoformat()}); return
    try: sb().table("improvement_log").insert({"feedback_id": fid, "section": sec, "original_text": old, "updated_text": new, "ai_reasoning": reason, "action": action, "created_by": by}).execute()
    except: pass

def db_get_improvement_log():
    if not SUPABASE_OK: return st.session_state.get("local_imp", [])
    try: return sb().table("improvement_log").select("*").order("created_at", desc=True).execute().data or []
    except: return []

def db_log_ai_decision(fid, dec, conf, reason, target):
    if not SUPABASE_OK:
        st.session_state.setdefault("local_ai", []).append({"id": len(st.session_state.get("local_ai", [])) + 1, "feedback_id": fid, "decision": dec, "confidence": conf, "reasoning": reason, "target_section": target, "created_at": datetime.now().isoformat()}); return
    try: sb().table("ai_decisions").insert({"feedback_id": fid, "decision": dec, "confidence": conf, "reasoning": reason, "target_section": target}).execute()
    except: pass

def db_get_ai_decisions():
    if not SUPABASE_OK: return st.session_state.get("local_ai", [])
    try: return sb().table("ai_decisions").select("*").order("created_at", desc=True).execute().data or []
    except: return []

def db_get_proposal_sections():
    if not SUPABASE_OK: return st.session_state.get("local_sec", [])
    try: return sb().table("proposal_sections").select("*").eq("is_active", True).order("section_order").execute().data or []
    except: return []

def db_get_section_by_key(key):
    if not SUPABASE_OK: return next((s for s in st.session_state.get("local_sec", []) if s.get("section_key") == key), None)
    try:
        r = sb().table("proposal_sections").select("*").eq("section_key", key).eq("is_active", True).execute()
        return r.data[0] if r.data else None
    except: return None

def db_update_section_content(sk, content, by, fid=None):
    if not SUPABASE_OK: return 1
    try:
        cur = db_get_section_by_key(sk)
        nv = (cur.get("version", 1) + 1) if cur else 1
        sb().table("proposal_sections").update({"content": content, "version": nv, "last_updated_by": by, "last_feedback_id": fid, "updated_at": datetime.utcnow().isoformat()}).eq("section_key", sk).eq("is_active", True).execute()
        return nv
    except Exception as e: st.error(f"Error: {e}"); return None

def _find_section_for_feedback(sec):
    sk = sec.lower().replace(" ", "_").replace("/", "_").replace("__", "_").strip("_")
    sd = db_get_section_by_key(sk)
    if sd: return sd
    for s in db_get_proposal_sections():
        if s["section_title"].lower() == sec.lower() or sec.lower() in s["section_title"].lower(): return s
    return None

# ─── MEETINGS DB ───
def db_get_meetings():
    if not SUPABASE_OK: return st.session_state.get("local_meetings", [])
    try: return sb().table("meetings").select("*").order("meeting_date", desc=False).execute().data or []
    except: return []

def db_add_meeting(data):
    if not SUPABASE_OK:
        data["id"] = len(st.session_state.get("local_meetings", [])) + 1
        data["created_at"] = datetime.now().isoformat()
        st.session_state.setdefault("local_meetings", []).append(data); return
    try: sb().table("meetings").insert(data).execute()
    except Exception as e: st.error(f"Error: {e}")

def db_update_meeting(mid, data):
    if not SUPABASE_OK: return
    try: sb().table("meetings").update(data).eq("id", mid).execute()
    except Exception as e: st.error(f"Error: {e}")

def db_delete_meeting(mid):
    if not SUPABASE_OK: return
    try: sb().table("meetings").delete().eq("id", mid).execute()
    except Exception as e: st.error(f"Error: {e}")

    # ═══════════════════════════════════════
# AI ENGINE
# ═══════════════════════════════════════
def ai_analyze_feedback_v2(ft, sk, sc):
    if not AI_ENABLED or not ai_client:
        return {"decision": "manual_review", "confidence": 0, "reasoning": "AI not configured.", "target_section": sk, "suggested_action": "review", "suggested_text": "", "priority": "medium", "affected_wp": "", "erasmus_criteria": {}}
    try:
        r = ai_client.chat.completions.create(model=ai_model, messages=[
            {"role": "system", "content": """You are an Erasmus+ KA210 proposal analyst for OncoConnect (peer mentorship for cancer patients: Turkey, Poland, Spain). Return JSON: {"decision":"integrate|revise|route|archive|reject|ethical_risk","confidence":0.0-1.0,"reasoning":"2-3 sentences","target_section":"section_key","suggested_action":"action","suggested_text":"revised text in academic English","priority":"critical|high|medium|low","affected_wp":"WP1-WP5","erasmus_criteria":{"relevance":bool,"methodology":bool,"partnership":bool,"impact":bool,"inclusion":bool,"digital":bool,"sustainability":bool}}"""},
            {"role": "user", "content": f"SECTION: {sk}\nCONTENT:\n{sc or '[Empty]'}\nFEEDBACK:\n{ft}"}
        ], response_format={"type": "json_object"}, temperature=0.3, max_tokens=1500)
        return json.loads(r.choices[0].message.content)
    except Exception as e:
        return {"decision": "manual_review", "confidence": 0, "reasoning": f"AI error: {e}", "target_section": sk, "suggested_action": "review", "suggested_text": "", "priority": "medium", "affected_wp": "", "erasmus_criteria": {}}

def ai_generate_section_revision(sk, sc, fb):
    if not AI_ENABLED or not ai_client: return "AI not configured."
    try:
        r = ai_client.chat.completions.create(model=ai_model, messages=[
            {"role": "system", "content": "Expert Erasmus+ KA210 proposal writer. Formal academic English. Output ONLY revised text."},
            {"role": "user", "content": f"SECTION: {sk}\nCURRENT:\n{sc or '[Empty]'}\nFEEDBACK:\n{fb}\nWrite improved version:"}
        ], temperature=0.4, max_tokens=2000)
        return r.choices[0].message.content
    except Exception as e: return f"AI error: {e}"

def ai_generate_summary(fbl):
    if not AI_ENABLED or not ai_client or not fbl: return "AI not available."
    try:
        ft = "\n".join([f"- [{f.get('section','')}] {f.get('feedback', f.get('content',''))}" for f in fbl[:20]])
        r = ai_client.chat.completions.create(model=ai_model, messages=[
            {"role": "system", "content": "Summarize key themes from Erasmus+ KA210 feedback. Be concise."},
            {"role": "user", "content": ft}
        ], temperature=0.3, max_tokens=800)
        return r.choices[0].message.content
    except Exception as e: return f"AI error: {e}"

# ═══════════════════════════════════════
# PROPOSAL MD PARSER
# ═══════════════════════════════════════
def parse_proposal_md(md):
    mapping = {"project summary": "project_summary", "problem analysis": "problem_analysis", "needs analysis": "problem_analysis", "objectives": "objectives", "methodology": "methodology", "work packages": "work_packages", "partnership": "partnership", "consortium": "partnership", "impact": "impact", "evaluation": "evaluation", "budget": "budget", "dissemination": "dissemination", "ethics": "ethics_gdpr", "gdpr": "ethics_gdpr", "sustainability": "sustainability"}
    result, ck, cl = {}, None, []
    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("## ") or s.startswith("# "):
            if ck and cl: result[ck] = "\n".join(cl).strip()
            t = s.lstrip("# ").strip().lower(); ck = None
            for kw, sk in mapping.items():
                if kw in t: ck = sk; break
            cl = []
        elif ck: cl.append(line)
    if ck and cl: result[ck] = "\n".join(cl).strip()
    return result

# ═══════════════════════════════════════
# EXPORT ENGINE
# ═══════════════════════════════════════
def generate_feedback_excel():
    if not EXPORT_OK: return None
    wb = Workbook()
    hf = Font(bold=True, color="FFFFFF", size=11)
    hfl = PatternFill(start_color="1B3A5C", end_color="1B3A5C", fill_type="solid")
    bd = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    wa = Alignment(wrap_text=True, vertical="top")
    pfb = db_get_partner_feedback()
    patfb = db_get_patient_feedback()
    
    # Summary
    ws = wb.active; ws.title = "Summary"; ws.sheet_properties.tabColor = "1B3A5C"
    ws["A1"] = "OncoConnect — Feedback Export Report"; ws["A1"].font = Font(bold=True, size=16, color="1B3A5C")
    ws["A2"] = f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}"; ws["A2"].font = Font(italic=True, color="666666")
    stats = [("Total Partner Feedback", len(pfb)), ("Total Patient Feedback", len(patfb)),
             ("Open", len([f for f in pfb if f.get("status") == "Open"])),
             ("Accepted", len([f for f in pfb if f.get("status") == "Accepted"])),
             ("Rejected", len([f for f in pfb if f.get("status") == "Rejected"]))]
    for i, (l, v) in enumerate(stats, 5): ws[f"A{i}"] = l; ws[f"A{i}"].font = Font(bold=True); ws[f"B{i}"] = v
    ws.column_dimensions["A"].width = 35; ws.column_dimensions["B"].width = 15
    
    # All feedback
    ws2 = wb.create_sheet("All Partner Feedback"); ws2.sheet_properties.tabColor = "2ABFBF"
    headers = ["ID", "Date", "Country", "Organisation", "Section", "Priority", "Status", "Feedback", "Response"]
    for c, h in enumerate(headers, 1):
        cell = ws2.cell(row=1, column=c, value=h); cell.font = hf; cell.fill = hfl; cell.border = bd
    for i, fb in enumerate(pfb, 2):
        vals = [fb.get("id",""), str(fb.get("created_at",""))[:10], fb.get("partner_country", fb.get("country","")),
                fb.get("organisation",""), fb.get("section",""), fb.get("priority",""), fb.get("status",""),
                fb.get("feedback", fb.get("content","")), fb.get("response","")]
        for c, v in enumerate(vals, 1):
            cell = ws2.cell(row=i, column=c, value=str(v) if v else ""); cell.border = bd; cell.alignment = wa
    for i, w in enumerate([8,12,12,30,20,10,12,60,40], 1): ws2.column_dimensions[get_column_letter(i)].width = w
    ws2.auto_filter.ref = f"A1:I{len(pfb)+1}"
    
    # Section sheets
    secs = sorted(set(f.get("section", "General") for f in pfb))
    for sn in secs:
        safe = sn[:28].replace("/", "-")
        wss = wb.create_sheet(safe); wss.sheet_properties.tabColor = "F39C12"
        wss["A1"] = sn; wss["A1"].font = Font(bold=True, size=14, color="1B3A5C")
        sd = _find_section_for_feedback(sn)
        sr = 4
        if sd and sd.get("content"):
            wss["A3"] = "PROPOSAL CONTENT:"; wss["A3"].font = Font(bold=True, color="2ABFBF")
            wss["A4"] = sd["content"][:2000]; wss["A4"].alignment = wa; sr = 7
        fh = ["ID", "Date", "Country", "Priority", "Status", "Feedback", "Response"]
        for c, h in enumerate(fh, 1):
            cell = wss.cell(row=sr, column=c, value=h); cell.font = hf; cell.fill = hfl; cell.border = bd
        for i, fb in enumerate([f for f in pfb if f.get("section") == sn], sr + 1):
            vals = [fb.get("id",""), str(fb.get("created_at",""))[:10], fb.get("partner_country", fb.get("country","")),
                    fb.get("priority",""), fb.get("status",""), fb.get("feedback", fb.get("content","")), fb.get("response","")]
            for c, v in enumerate(vals, 1):
                cell = wss.cell(row=i, column=c, value=str(v) if v else ""); cell.border = bd; cell.alignment = wa
        for i, w in enumerate([8,12,15,10,12,60,40], 1): wss.column_dimensions[get_column_letter(i)].width = w
    
    # Patient
    if patfb:
        wsp = wb.create_sheet("Patient Feedback"); wsp.sheet_properties.tabColor = "A855F7"
        ph = ["ID", "Date", "Country", "Age", "Cancer", "Support Need", "Digital", "Matching", "Privacy"]
        for c, h in enumerate(ph, 1):
            cell = wsp.cell(row=1, column=c, value=h); cell.font = hf; cell.fill = PatternFill(start_color="6F42C1", end_color="6F42C1", fill_type="solid"); cell.border = bd
        for i, p in enumerate(patfb, 2):
            vals = [p.get("id",""), str(p.get("created_at",""))[:10], p.get("country",""), p.get("age_group",""),
                    p.get("cancer_type",""), p.get("support_need",""), p.get("digital_literacy",""),
                    p.get("matching_preference",""), p.get("privacy_expectation","")]
            for c, v in enumerate(vals, 1):
                cell = wsp.cell(row=i, column=c, value=str(v) if v else ""); cell.border = bd; cell.alignment = wa
    
    out = BytesIO(); wb.save(out); out.seek(0); return out.getvalue()


def generate_feedback_pdf():
    if not EXPORT_OK: return None
    class P(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 10); self.set_text_color(27,58,92)
            self.cell(0, 8, "OncoConnect - Feedback Report", align="L")
            self.cell(0, 8, datetime.now().strftime("%d %B %Y"), align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(42,191,191); self.line(10, self.get_y(), 200, self.get_y()); self.ln(5)
        def footer(self):
            self.set_y(-15); self.set_font("Helvetica", "I", 8); self.set_text_color(128,128,128)
            self.cell(0, 10, f"OncoConnect | Erasmus+ KA210 | Page {self.page_no()}/{{nb}}", align="C")
        def stitle(self, t):
            self.set_font("Helvetica", "B", 14); self.set_text_color(27,58,92); self.set_fill_color(240,242,246)
            self.cell(0, 10, t, fill=True, new_x="LMARGIN", new_y="NEXT"); self.ln(3)
        def body(self, t):
            self.set_font("Helvetica", "", 9); self.set_text_color(51,51,51)
            self.multi_cell(0, 5, t.encode("latin-1", "replace").decode("latin-1") if t else ""); self.ln(2)
    
    pdf = P(); pdf.alias_nb_pages(); pdf.set_auto_page_break(auto=True, margin=20)
    pfb = db_get_partner_feedback(); patfb = db_get_patient_feedback(); ap = db_get_approvals()
    
    # Cover
    pdf.add_page(); pdf.ln(30); pdf.set_font("Helvetica", "B", 28); pdf.set_text_color(27,58,92)
    pdf.cell(0, 15, "OncoConnect", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14); pdf.set_text_color(42,191,191)
    pdf.cell(0, 10, "Feedback & AI Analysis Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5); pdf.set_font("Helvetica", "", 11); pdf.set_text_color(128,128,128)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10); pdf.set_font("Helvetica", "", 10); pdf.set_text_color(51,51,51)
    for l in [f"Partner Feedback: {len(pfb)}", f"Patient Feedback: {len(patfb)}", f"Approvals: {sum(1 for v in ap.values() if v)}/3"]:
        pdf.cell(0, 7, l, align="C", new_x="LMARGIN", new_y="NEXT")
    
    # Sections
    secs = sorted(set(f.get("section", "General") for f in pfb))
    for sn in secs:
        pdf.add_page(); pdf.stitle(f"Section: {sn}")
        sd = _find_section_for_feedback(sn)
        if sd and sd.get("content"):
            pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(42,191,191)
            pdf.cell(0, 8, "Proposal Content:", new_x="LMARGIN", new_y="NEXT")
            pdf.body(sd["content"][:1000])
        sfbs = [f for f in pfb if f.get("section") == sn]
        pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(27,58,92)
        pdf.cell(0, 8, f"Feedback ({len(sfbs)} items):", new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)
        for fb in sfbs:
            fc = fb.get("partner_country", fb.get("country", ""))
            fl = {"Turkey": "[TR]", "Poland": "[PL]", "Spain": "[ES]"}.get(fc, f"[{fc}]")
            pdf.set_font("Helvetica", "B", 9)
            pc = {"High": (220,53,69), "Medium": (255,193,7), "Low": (40,167,69)}.get(fb.get("priority",""), (128,128,128))
            pdf.set_text_color(*pc)
            pdf.cell(0, 6, f"#{fb.get('id','')} | {fl} | {fb.get('priority','')} | {fb.get('status','')}", new_x="LMARGIN", new_y="NEXT")
            pdf.body(fb.get("feedback", fb.get("content", "")))
            if pdf.get_y() > 260: pdf.add_page()
    
    return bytes(pdf.output())

# ═══════════════════════════════════════
# DATA + UI HELPERS
# ═══════════════════════════════════════
@st.cache_data
def load_csv(p):
    try: return pd.read_csv(p)
    except: return pd.DataFrame()

def load_static(): return load_csv("data/work_packages.csv"), load_csv("data/partners.csv")

def render_countdown():
    now = datetime.now()
    pt = (SUBMISSION_DEADLINE - PREPARATION_START).days; pe = (now - PREPARATION_START).days
    pp = max(0, min(1, pe / max(pt, 1))); rem = SUBMISSION_DEADLINE - now
    if rem.total_seconds() <= 0: st.error("DEADLINE PASSED!"); return
    d = rem.days; h, r2 = divmod(rem.seconds, 3600); m, _ = divmod(r2, 60)
    sc = "#17a2b8" if d > 365 else "#28a745" if d > 180 else "#ffc107" if d > 60 else "#dc3545"
    pct = int(pp * 100); deg = int(pp * 360)
    pc = "#a855f7" if pp < 0.5 else "#f59e0b" if pp < 0.8 else "#ef4444"
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='countdown-box' style='background:linear-gradient(135deg,#1a1a2e,#2d1b4e);'><p style='margin:0;font-size:.75rem;opacity:.7;letter-spacing:2px;'>PREPARATION PHASE</p><div style='margin:1rem auto;width:120px;height:120px;border-radius:50%;background:conic-gradient({pc} {deg}deg,#333 0deg);display:flex;align-items:center;justify-content:center;'><div style='width:100px;height:100px;border-radius:50%;background:#1a1a2e;display:flex;align-items:center;justify-content:center;flex-direction:column;'><span style='font-size:1.8rem;font-weight:bold;color:{pc};'>{pct}%</span><span style='font-size:.65rem;opacity:.6;'>COMPLETE</span></div></div><p style='margin:0;font-size:.8rem;opacity:.6;'>Elapsed: {pe} days</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='countdown-box' style='background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);'><p style='margin:0;font-size:.75rem;opacity:.7;letter-spacing:2px;'>SUBMISSION DEADLINE</p><p style='margin:.3rem 0 0;font-size:.85rem;opacity:.8;'>{SUBMISSION_DEADLINE.strftime('%d %B %Y')}</p><div style='display:flex;justify-content:center;gap:1.5rem;margin:1.2rem 0;'><div><span style='font-size:2.8rem;font-weight:bold;color:{sc};'>{d}</span><br><span style='font-size:.75rem;opacity:.6;'>DAYS</span></div><div><span style='font-size:2.8rem;font-weight:bold;color:{sc};'>{h:02d}</span><br><span style='font-size:.75rem;opacity:.6;'>HOURS</span></div><div><span style='font-size:2.8rem;font-weight:bold;color:{sc};'>{m:02d}</span><br><span style='font-size:.75rem;opacity:.6;'>MIN</span></div></div></div>", unsafe_allow_html=True)
    st.progress(max(0, min(1, 1 - d / max(pt, 1))))

def ann_card(row):
    p = row.get("priority", "Low")
    border = {"High": "#dc3545", "Medium": "#ffc107"}.get(p, "#28a745")
    icon = {"High": "🔴", "Medium": "🟡"}.get(p, "🟢")
    st.markdown(f"<div class='ann-card' style='border-left-color:{border};'><strong>{icon} {row.get('title','')}</strong><span style='float:right;color:#666;font-size:.85rem;'>{str(row.get('created_at',''))[:10]}</span><br><span style='color:#444;'>{row.get('content','')}</span><br><span style='font-size:.8rem;color:#999;'>By: {row.get('author','')}</span></div>", unsafe_allow_html=True)

def show_access_denied():
    st.markdown("<div class='access-denied'><h2>🔒 Access Denied</h2><p>You don't have permission.</p></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════
# PAGE: MEETINGS (NEW)
# ═══════════════════════════════════════
def page_meetings():
    r = get_role()
    st.markdown("<div class='pro-header'><h1>📅 Meetings & Zoom Sessions</h1><p>Project coordination meetings, partner calls, and training sessions</p></div>", unsafe_allow_html=True)
    
    meetings = db_get_meetings()
    today = date.today()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Upcoming", "📋 All Meetings", "➕ Schedule" if r == "Admin" else "📊 Stats", "📊 Calendar View"])
    
    # ─── TAB 1: UPCOMING ───
    with tab1:
        upcoming = [m for m in meetings if str(m.get("meeting_date", "")) >= str(today)]
        upcoming.sort(key=lambda x: (str(x.get("meeting_date", "")), str(x.get("start_time", ""))))
        
        if not upcoming:
            st.markdown("""
            <div style='text-align:center;padding:3rem;background:linear-gradient(135deg,#f0f9ff,#e0f2fe);
            border-radius:16px;border:1px solid #bae6fd;'>
                <h2>📭 No Upcoming Meetings</h2>
                <p style='color:#64748b;'>All meetings have been completed or none scheduled yet.</p>
            </div>""", unsafe_allow_html=True)
        else:
            for m in upcoming:
                md = str(m.get("meeting_date", ""))
                is_today = md == str(today)
                card_class = "meeting-card today" if is_today else "meeting-card"
                today_badge = "<span class='badge badge-success' style='margin-left:8px;'>TODAY</span>" if is_today else ""
                
                zoom_link = m.get("zoom_link", "")
                zoom_btn = f"<a href='{zoom_link}' target='_blank' class='zoom-btn'>🎥 Join Zoom Meeting</a>" if zoom_link else "<span style='color:#94a3b8;font-size:0.85rem;'>No Zoom link yet</span>"
                
                zoom_id = m.get("zoom_id", "")
                zoom_pass = m.get("zoom_passcode", "")
                zoom_info = ""
                if zoom_id:
                    zoom_info += f"<br><span style='font-size:0.8rem;color:#64748b;'>Meeting ID: <code>{zoom_id}</code></span>"
                if zoom_pass:
                    zoom_info += f"<span style='font-size:0.8rem;color:#64748b;margin-left:1rem;'>Passcode: <code>{zoom_pass}</code></span>"
                
                participants = m.get("participants", '["All"]')
                if isinstance(participants, str):
                    try: participants = json.loads(participants)
                    except: participants = [participants]
                part_str = ", ".join(participants) if participants else "All"
                
                mt = m.get("meeting_type", "General")
                type_colors = {"General": "#3b82f6", "Partner Call": "#10b981", "Training": "#f59e0b", 
                              "Workshop": "#8b5cf6", "Review": "#ef4444", "Dissemination": "#ec4899"}
                tc = type_colors.get(mt, "#64748b")
                
                st.markdown(f"""
                <div class='{card_class}'>
                    <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                        <div style='flex:1;'>
                            <div class='meeting-date'>
                                📅 {md}{today_badge}
                                <span class='badge' style='background:{tc}20;color:{tc};margin-left:8px;'>{mt}</span>
                            </div>
                            <div class='meeting-title'>{m.get("title", "Untitled Meeting")}</div>
                            <div class='meeting-time'>🕐 {str(m.get("start_time",""))[:5]} — {str(m.get("end_time",""))[:5]} ({m.get("timezone","CET")})</div>
                            <div class='meeting-meta'>
                                👥 Participants: {part_str}
                            </div>
                            {f"<div style='margin-top:0.5rem;font-size:0.9rem;color:#475569;'>{m.get('description','')}</div>" if m.get("description") else ""}
                            {f"<div style='margin-top:0.5rem;'><strong style='font-size:0.85rem;color:#1B3A5C;'>📋 Agenda:</strong><br><span style='font-size:0.85rem;color:#475569;white-space:pre-line;'>{m.get('agenda','')}</span></div>" if m.get("agenda") else ""}
                            {zoom_info}
                        </div>
                        <div style='text-align:right;min-width:180px;'>
                            {zoom_btn}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"<p style='text-align:center;color:#94a3b8;margin-top:1rem;'>Showing {len(upcoming)} upcoming meeting(s)</p>", unsafe_allow_html=True)
    
    # ─── TAB 2: ALL MEETINGS ───
    with tab2:
        if not meetings:
            st.info("No meetings recorded yet.")
        else:
            st.markdown("### 📋 Complete Meeting History")
            
            # Filters
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                mt_filter = st.multiselect("Meeting Type", ["General", "Partner Call", "Training", "Workshop", "Review", "Dissemination"], default=[])
            with fc2:
                status_filter = st.selectbox("Status", ["All", "Scheduled", "Completed", "Cancelled"])
            with fc3:
                date_range = st.selectbox("Period", ["All", "This Week", "This Month", "Past", "Future"])
            
            filtered = meetings.copy()
            if mt_filter:
                filtered = [m for m in filtered if m.get("meeting_type", "General") in mt_filter]
            if status_filter != "All":
                filtered = [m for m in filtered if m.get("status", "Scheduled") == status_filter]
            if date_range == "Past":
                filtered = [m for m in filtered if str(m.get("meeting_date", "")) < str(today)]
            elif date_range == "Future":
                filtered = [m for m in filtered if str(m.get("meeting_date", "")) >= str(today)]
            elif date_range == "This Week":
                week_end = today + timedelta(days=7)
                filtered = [m for m in filtered if str(today) <= str(m.get("meeting_date", "")) <= str(week_end)]
            elif date_range == "This Month":
                month_end = today.replace(day=28) + timedelta(days=4)
                filtered = [m for m in filtered if str(today) <= str(m.get("meeting_date", "")) <= str(month_end)]
            
            if filtered:
                df_data = []
                for m in filtered:
                    is_past = str(m.get("meeting_date", "")) < str(today)
                    status_icon = "✅" if m.get("status") == "Completed" else ("⏳" if not is_past else "🔘")
                    df_data.append({
                        "Status": status_icon,
                        "Date": str(m.get("meeting_date", ""))[:10],
                        "Time": f"{str(m.get('start_time',''))[:5]}–{str(m.get('end_time',''))[:5]}",
                        "Title": m.get("title", ""),
                        "Type": m.get("meeting_type", "General"),
                        "Zoom": "🔗" if m.get("zoom_link") else "—",
                        "ID": m.get("id", "")
                    })
                st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
                
                # Admin: Mark as completed / delete
                if r == "Admin":
                    st.markdown("---")
                    st.markdown("#### ⚙️ Manage Meetings")
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        mid_complete = st.selectbox("Mark as Completed", [f"#{m.get('id')} — {m.get('title','')}" for m in filtered if m.get("status") != "Completed"], key="complete_sel")
                        if st.button("✅ Mark Completed", key="btn_complete"):
                            if mid_complete:
                                mid = int(mid_complete.split("#")[1].split(" ")[0])
                                db_update_meeting(mid, {"status": "Completed"})
                                st.success("Meeting marked as completed!"); st.rerun()
                    with mc2:
                        mid_del = st.selectbox("Delete Meeting", [f"#{m.get('id')} — {m.get('title','')}" for m in filtered], key="del_sel")
                        if st.button("🗑️ Delete", type="secondary", key="btn_del"):
                            if mid_del:
                                mid = int(mid_del.split("#")[1].split(" ")[0])
                                db_delete_meeting(mid)
                                st.success("Meeting deleted!"); st.rerun()
                    
                    # Add notes/recording
                    st.markdown("#### 📝 Meeting Notes & Recordings")
                    past_meetings = [m for m in filtered if str(m.get("meeting_date", "")) < str(today) or m.get("status") == "Completed"]
                    if past_meetings:
                        sel_note = st.selectbox("Select Meeting", [f"#{m.get('id')} — {m.get('title','')}" for m in past_meetings], key="note_sel")
                        if sel_note:
                            mid = int(sel_note.split("#")[1].split(" ")[0])
                            cur_m = next((m for m in past_meetings if m.get("id") == mid), {})
                            notes = st.text_area("Meeting Notes", value=cur_m.get("notes", "") or "", height=120, key="meeting_notes_input")
                            rec_link = st.text_input("Recording Link", value=cur_m.get("recording_link", "") or "", key="rec_link_input")
                            if st.button("💾 Save Notes", key="btn_save_notes"):
                                db_update_meeting(mid, {"notes": notes, "recording_link": rec_link})
                                st.success("Notes saved!"); st.rerun()
            else:
                st.info("No meetings match the selected filters.")
    
    # ─── TAB 3: SCHEDULE NEW (Admin) / STATS (Others) ───
    with tab3:
        if r == "Admin":
            st.markdown("### ➕ Schedule New Meeting")
            with st.form("new_meeting"):
                m_title = st.text_input("Meeting Title *", placeholder="e.g. Monthly Partner Coordination Call")
                m_desc = st.text_area("Description", placeholder="Brief description of the meeting purpose", height=80)
                
                dc1, dc2, dc3 = st.columns(3)
                with dc1:
                    m_date = st.date_input("Date *", value=date.today() + timedelta(days=7), min_value=date.today())
                with dc2:
                    m_start = st.time_input("Start Time *", value=dt_time(14, 0))
                with dc3:
                    m_end = st.time_input("End Time *", value=dt_time(15, 0))
                
                zc1, zc2, zc3 = st.columns(3)
                with zc1:
                    m_zoom = st.text_input("Zoom Link", placeholder="https://zoom.us/j/...")
                with zc2:
                    m_zoom_id = st.text_input("Meeting ID", placeholder="123 456 7890")
                with zc3:
                    m_zoom_pass = st.text_input("Passcode", placeholder="abc123")
                
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    m_type = st.selectbox("Meeting Type", ["General", "Partner Call", "Training", "Workshop", "Review", "Dissemination"])
                with tc2:
                    m_tz = st.selectbox("Timezone", ["CET", "EET", "GMT", "UTC"])
                with tc3:
                    m_parts = st.multiselect("Participants", ["All", "Turkey", "Poland", "Spain", "Patients", "External"], default=["All"])
                
                m_agenda = st.text_area("Agenda", placeholder="1. Welcome & updates\n2. Progress review\n3. Next steps\n4. Q&A", height=120)
                
                if st.form_submit_button("📅 Schedule Meeting", type="primary", use_container_width=True):
                    if m_title and m_date:
                        db_add_meeting({
                            "title": m_title,
                            "description": m_desc,
                            "meeting_date": str(m_date),
                            "start_time": str(m_start),
                            "end_time": str(m_end),
                            "timezone": m_tz,
                            "zoom_link": m_zoom,
                            "zoom_id": m_zoom_id,
                            "zoom_passcode": m_zoom_pass,
                            "meeting_type": m_type,
                            "participants": json.dumps(m_parts),
                            "agenda": m_agenda,
                            "created_by": get_name(),
                            "status": "Scheduled"
                        })
                        st.success(f"✅ Meeting '{m_title}' scheduled for {m_date}!")
                        st.rerun()
                    else:
                        st.error("Title and date are required.")
            
            # Quick schedule templates
            st.markdown("---")
            st.markdown("### 🎯 Quick Templates")
            qt1, qt2, qt3 = st.columns(3)
            with qt1:
                if st.button("📞 Weekly Partner Call", use_container_width=True):
                    next_monday = today + timedelta(days=(7 - today.weekday()))
                    db_add_meeting({
                        "title": "Weekly Partner Coordination Call",
                        "description": "Regular weekly sync meeting with all partners.",
                        "meeting_date": str(next_monday),
                        "start_time": "14:00", "end_time": "15:00",
                        "timezone": "CET", "meeting_type": "Partner Call",
                        "participants": json.dumps(["All"]),
                        "agenda": "1. Status updates from each partner\n2. Blockers & issues\n3. Next week planning\n4. AOB",
                        "created_by": get_name(), "status": "Scheduled"
                    })
                    st.success("Weekly call scheduled!"); st.rerun()
            with qt2:
                if st.button("🎓 Training Session", use_container_width=True):
                    next_wed = today + timedelta(days=(2 - today.weekday()) % 7 + 7)
                    db_add_meeting({
                        "title": "AI Tools Training Session",
                        "description": "Hands-on training on AI-powered peer mentorship tools.",
                        "meeting_date": str(next_wed),
                        "start_time": "10:00", "end_time": "12:00",
                        "timezone": "CET", "meeting_type": "Training",
                        "participants": json.dumps(["All", "Patients"]),
                        "agenda": "1. Platform overview\n2. AI features demo\n3. Hands-on practice\n4. Q&A",
                        "created_by": get_name(), "status": "Scheduled"
                    })
                    st.success("Training session scheduled!"); st.rerun()
            with qt3:
                if st.button("📊 Monthly Review", use_container_width=True):
                    first_of_next = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
                    db_add_meeting({
                        "title": "Monthly Progress Review",
                        "description": "Monthly review of project progress, deliverables, and budget.",
                        "meeting_date": str(first_of_next),
                        "start_time": "14:00", "end_time": "16:00",
                        "timezone": "CET", "meeting_type": "Review",
                        "participants": json.dumps(["All"]),
                        "agenda": "1. Progress report per WP\n2. Budget review\n3. Deliverables status\n4. Risk assessment\n5. Next month plan",
                        "created_by": get_name(), "status": "Scheduled"
                    })
                    st.success("Monthly review scheduled!"); st.rerun()
        else:
            # Stats for non-admin
            st.markdown("### 📊 Meeting Statistics")
            total = len(meetings)
            completed = len([m for m in meetings if m.get("status") == "Completed"])
            upcoming_count = len([m for m in meetings if str(m.get("meeting_date", "")) >= str(today)])
            
            sc1, sc2, sc3 = st.columns(3)
            with sc1: st.markdown(f"<div class='metric-card'><div class='value'>{total}</div><div class='label'>Total Meetings</div></div>", unsafe_allow_html=True)
            with sc2: st.markdown(f"<div class='metric-card'><div class='value'>{completed}</div><div class='label'>Completed</div></div>", unsafe_allow_html=True)
            with sc3: st.markdown(f"<div class='metric-card'><div class='value'>{upcoming_count}</div><div class='label'>Upcoming</div></div>", unsafe_allow_html=True)
            
            if meetings:
                types = {}
                for m in meetings:
                    t = m.get("meeting_type", "General")
                    types[t] = types.get(t, 0) + 1
                fig = px.pie(values=list(types.values()), names=list(types.keys()), color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=350, title="Meetings by Type")
                st.plotly_chart(fig, use_container_width=True)
    
    # ─── TAB 4: CALENDAR VIEW ───
    with tab4:
        st.markdown("### 🗓️ Calendar Overview")
        if meetings:
            cal_data = []
            for m in meetings:
                md = str(m.get("meeting_date", ""))
                try:
                    d_obj = datetime.strptime(md[:10], "%Y-%m-%d")
                except:
                    continue
                cal_data.append({
                    "Date": d_obj,
                    "Title": m.get("title", ""),
                    "Type": m.get("meeting_type", "General"),
                    "Time": f"{str(m.get('start_time',''))[:5]}",
                    "Status": m.get("status", "Scheduled")
                })
            
            if cal_data:
                df_cal = pd.DataFrame(cal_data)
                df_cal["Week"] = df_cal["Date"].dt.isocalendar().week
                df_cal["DayOfWeek"] = df_cal["Date"].dt.day_name()
                df_cal["Month"] = df_cal["Date"].dt.strftime("%Y-%m")
                
                # Timeline chart
                fig = px.scatter(df_cal, x="Date", y="Type", color="Type", size_max=15,
                                hover_data=["Title", "Time", "Status"],
                                color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_traces(marker=dict(size=14, symbol="diamond"))
                fig.update_layout(height=400, title="Meeting Timeline", yaxis_title="", xaxis_title="")
                # Add today line
                fig.add_vline(x=datetime.now(), line_dash="dash", line_color="red", annotation_text="Today")
                st.plotly_chart(fig, use_container_width=True)
                
                # Monthly breakdown
                monthly = df_cal.groupby("Month").size().reset_index(name="Count")
                fig2 = px.bar(monthly, x="Month", y="Count", color_discrete_sequence=["#2ABFBF"])
                fig2.update_layout(height=300, title="Meetings per Month")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No meetings to display on calendar.")


# ═══════════════════════════════════════
# PAGE: WORK PACKAGES
# ═══════════════════════════════════════
def page_work_packages(wp_df):
    r, c = get_role(), get_country()
    st.markdown("<div class='pro-header'><h1>📦 Work Packages</h1><p>Project structure and task allocation</p></div>", unsafe_allow_html=True)
    if len(wp_df) == 0:
        st.info("No WP data loaded. Create data/work_packages.csv"); return
    if r == "Partner" and c != "All":
        wps = get_user_wps(c)
        wp_df = wp_df[wp_df["wp_id"].isin(wps)]
        st.info(f"Showing WPs for {FLAGS.get(c,'')} {c}: {', '.join(wps)}")
    for _, row in wp_df.iterrows():
        wpid = row.get("wp_id", "")
        with st.expander(f"📦 {wpid}: {row.get('title', '')}", expanded=False):
            mc1, mc2, mc3 = st.columns(3)
            with mc1: st.metric("Budget", f"€{row.get('budget_eur', 0):,.0f}")
            with mc2: st.metric("Status", row.get("status", "Planned"))
            with mc3: st.metric("Lead", row.get("lead_country", "TBD"))
            if r != "Patient":
                rc = st.columns(3)
                for col2, cn in zip(rc, ["Turkey", "Poland", "Spain"]):
                    with col2: st.markdown(f"{FLAGS[cn]} **{cn}**: {get_wp_role(cn, wpid)}")
            st.markdown(f"**Description:** {row.get('description', 'N/A')}")


# ═══════════════════════════════════════
# PAGE: GANTT
# ═══════════════════════════════════════
def page_gantt(wp_df):
    r, c = get_role(), get_country()
    st.markdown("<div class='pro-header'><h1>📅 Gantt Chart</h1><p>Project timeline visualization</p></div>", unsafe_allow_html=True)
    if len(wp_df) == 0 or "start_date" not in wp_df.columns: st.info("No timeline data."); return
    df = wp_df.copy()
    if r == "Partner" and c != "All": df = df[df["wp_id"].isin(get_user_wps(c))]
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    df = df.dropna(subset=["start_date", "end_date"])
    if df.empty: st.warning("No valid dates."); return
    fig = px.timeline(df, x_start="start_date", x_end="end_date", y="wp_id", color="status",
                      color_discrete_map={"Completed": "#10B981", "In Progress": "#3B82F6", "Planned": "#94A3B8"})
    fig.update_yaxes(autorange="reversed"); fig.update_layout(height=400)
    fig.add_vline(x=datetime.now(), line_dash="dash", line_color="red", annotation_text="Today")
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════
# PAGE: PARTNERS
# ═══════════════════════════════════════
def page_partners(pf):
    st.markdown("<div class='pro-header'><h1>🤝 Partner Organisations</h1><p>Consortium members and responsibilities</p></div>", unsafe_allow_html=True)
    for cn, org in PARTNER_MAP.items():
        with st.expander(f"{FLAGS[cn]} {org} — {cn}", expanded=True):
            st.markdown(f"**Country:** {cn}")
            st.markdown(f"**Organisation:** {org}")
            wpm = WP_COUNTRY_MAP.get(cn, {})
            st.markdown(f"**Lead WPs:** {', '.join(wpm.get('lead', []))}")
            st.markdown(f"**Support WPs:** {', '.join(wpm.get('support', []))}")


# ═══════════════════════════════════════
# PAGE: PARTNER FEEDBACK
# ═══════════════════════════════════════
def page_partner_feedback():
    r, c = get_role(), get_country()
    st.markdown("<div class='pro-header'><h1>💬 Partner Feedback</h1><p>Submit and manage proposal feedback</p></div>", unsafe_allow_html=True)
    
    perm = get_permission("Partner Feedback", r)
    if perm in ("write", "full"):
        with st.expander("➕ Submit New Feedback", expanded=False):
            with st.form("pfb_form"):
                sec = st.selectbox("Section", PROPOSAL_SECTIONS)
                fb = st.text_area("Feedback", height=120, placeholder="Your suggestions or comments...")
                pri = st.select_slider("Priority", ["Low", "Medium", "High"], value="Medium")
                if st.form_submit_button("📤 Submit", type="primary", use_container_width=True):
                    if fb.strip():
                        cn = c if r == "Partner" else "Admin"
                        org = get_org()
                        db_add_partner_feedback(cn, org, sec, fb.strip(), pri, get_name())
                        st.success("✅ Feedback submitted!"); st.rerun()
                    else: st.warning("Please write feedback.")
    
    fbl = db_get_partner_feedback()
    if r == "Partner" and c != "All":
        fbl = [f for f in fbl if f.get("partner_country", f.get("country", "")) == c or f.get("partner_country", f.get("country", "")) == "Admin"]
    
    if not fbl: st.info("No feedback yet."); return
    
    # Export buttons
    if EXPORT_OK and r == "Admin":
        ec1, ec2, _ = st.columns([1, 1, 4])
        with ec1:
            xl = generate_feedback_excel()
            if xl: st.download_button("📥 Excel Export", xl, "oncoconnect_feedback.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with ec2:
            pdf = generate_feedback_pdf()
            if pdf: st.download_button("📥 PDF Report", pdf, "oncoconnect_feedback.pdf", "application/pdf", use_container_width=True)
    
    # Filters
    fc1, fc2, fc3 = st.columns(3)
    with fc1: sf = st.multiselect("Section Filter", sorted(set(f.get("section","") for f in fbl)), key="pfb_sec_f")
    with fc2: pf2 = st.multiselect("Priority", ["High","Medium","Low"], key="pfb_pri_f")
    with fc3: stf = st.multiselect("Status", sorted(set(f.get("status","Open") for f in fbl)), key="pfb_st_f")
    
    if sf: fbl = [f for f in fbl if f.get("section","") in sf]
    if pf2: fbl = [f for f in fbl if f.get("priority","") in pf2]
    if stf: fbl = [f for f in fbl if f.get("status","Open") in stf]
    
    st.markdown(f"**{len(fbl)} feedback item(s)**")
    
    for fb in fbl:
        pri = fb.get("priority", "Medium")
        bc = {"High": "badge-danger", "Medium": "badge-warning", "Low": "badge-success"}.get(pri, "badge-info")
        sc2 = fb.get("status", "Open")
        sbc = {"Open": "badge-info", "Accepted": "badge-success", "Rejected": "badge-danger", "In Review": "badge-warning"}.get(sc2, "badge-info")
        fc = fb.get("partner_country", fb.get("country", ""))
        
        st.markdown(f"""<div class='fb-card'>
            <div style='display:flex;justify-content:space-between;align-items:center;'>
                <div><strong>{FLAGS.get(fc,'')} #{fb.get('id','')} — {fb.get('section','')}</strong></div>
                <div><span class='badge {bc}'>{pri}</span> <span class='badge {sbc}'>{sc2}</span></div>
            </div>
            <p style='margin:0.5rem 0;color:#475569;'>{fb.get('feedback', fb.get('content',''))}</p>
            <span style='font-size:0.8rem;color:#94a3b8;'>By {fb.get('submitted_by','')} | {str(fb.get('created_at',''))[:10]}</span>
            {f"<div style='margin-top:0.5rem;padding:0.5rem;background:#f0fdf4;border-radius:8px;font-size:0.85rem;'><strong>Response:</strong> {fb.get('response','')}</div>" if fb.get('response') else ""}
        </div>""", unsafe_allow_html=True)
        
        if r == "Admin" and sc2 == "Open":
            uc1, uc2, uc3 = st.columns([2, 1, 1])
            with uc1: resp = st.text_input("Response", key=f"resp_{fb.get('id')}", placeholder="Admin response...")
            with uc2:
                if st.button("✅ Accept", key=f"acc_{fb.get('id')}"):
                    db_update_feedback_status(fb.get("id"), "Accepted", resp)
                    st.rerun()
            with uc3:
                if st.button("❌ Reject", key=f"rej_{fb.get('id')}"):
                    db_update_feedback_status(fb.get("id"), "Rejected", resp)
                    st.rerun()


# ═══════════════════════════════════════
# PAGE: PATIENT FEEDBACK
# ═══════════════════════════════════════
def page_patient_feedback():
    r = get_role()
    st.markdown("<div class='pro-header'><h1>💚 Patient Feedback</h1><p>Patient experience and needs assessment</p></div>", unsafe_allow_html=True)
    
    if r == "Patient":
        with st.form("patient_fb"):
            st.markdown("#### Share Your Experience")
            c1, c2 = st.columns(2)
            with c1:
                country = st.selectbox("Country", ["Turkey", "Poland", "Spain", "Other"])
                age = st.selectbox("Age Group", ["18-30", "31-45", "46-60", "60+"])
            with c2:
                cancer = st.text_input("Cancer Type", placeholder="e.g. Breast, Lung...")
                support = st.selectbox("Support Need", ["Emotional", "Medical Info", "Practical", "Social", "All"])
            digital = st.select_slider("Digital Literacy", ["Low", "Medium", "High"], value="Medium")
            matching = st.selectbox("Matching Preference", ["Same cancer type", "Same age group", "Same country", "No preference"])
            privacy = st.selectbox("Privacy Expectation", ["Anonymous", "First name only", "Full profile OK"])
            comments = st.text_area("Additional Comments", height=100)
            
            if st.form_submit_button("💚 Submit Feedback", type="primary", use_container_width=True):
                db_add_patient_feedback({
                    "country": country, "age_group": age, "cancer_type": cancer,
                    "support_need": support, "digital_literacy": digital,
                    "matching_preference": matching, "privacy_expectation": privacy,
                    "comments": comments, "submitted_by": get_name()
                })
                st.success("Thank you for your valuable feedback! 💚")
    
    if r == "Admin" or st.session_state.get("can_read_patient_fb"):
        pfb = db_get_patient_feedback()
        if pfb:
            st.subheader(f"📊 Patient Feedback ({len(pfb)} responses)")
            df = pd.DataFrame(pfb)
            if "support_need" in df.columns:
                fig = px.pie(df, names="support_need", title="Support Needs", color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df[[c for c in ["country","age_group","cancer_type","support_need","digital_literacy","matching_preference","privacy_expectation","comments","created_at"] if c in df.columns]], use_container_width=True, hide_index=True)
        else:
            st.info("No patient feedback yet.")
    elif r == "Patient":
        pass
    else:
        show_access_denied()


# ═══════════════════════════════════════
# PAGE: APPROVAL STATUS
# ═══════════════════════════════════════
def page_approval():
    r, c = get_role(), get_country()
    st.markdown("<div class='pro-header'><h1>🗳️ Approval Status</h1><p>Partner approval tracking for proposal submission</p></div>", unsafe_allow_html=True)
    
    ap = db_get_approvals()
    cols = st.columns(3)
    for col, cn in zip(cols, ["Turkey", "Poland", "Spain"]):
        with col:
            approved = ap.get(cn, False)
            bg = "linear-gradient(135deg,#dcfce7,#f0fdf4)" if approved else "linear-gradient(135deg,#fef9c3,#fffbeb)"
            ic = "✅" if approved else "⏳"
            st.markdown(f"""<div style='background:{bg};border-radius:16px;padding:2rem;text-align:center;border:1px solid {"#bbf7d0" if approved else "#fde68a"};'>
                <div style='font-size:3rem;'>{FLAGS[cn]}</div>
                <h3 style='margin:0.5rem 0;'>{PARTNER_MAP[cn]}</h3>
                <div style='font-size:2rem;'>{ic}</div>
                <p style='color:#64748b;'>{'Approved' if approved else 'Pending'}</p>
            </div>""", unsafe_allow_html=True)
    
    # Approve/revoke
    if r == "Partner" and c in PARTNER_MAP:
        st.markdown("---")
        if ap.get(c):
            if st.button(f"🔄 Revoke {c} Approval", type="secondary"):
                db_set_approval(c, False, get_name(), r); st.rerun()
        else:
            if st.button(f"✅ Approve on behalf of {c}", type="primary"):
                db_set_approval(c, True, get_name(), r); st.rerun()
    
    if r == "Admin":
        st.markdown("---")
        st.subheader("🛡️ Admin Controls")
        ac1, ac2 = st.columns(2)
        for col2, cn in zip(st.columns(3), ["Turkey", "Poland", "Spain"]):
            with col2:
                if ap.get(cn):
                    if st.button(f"Revoke {cn}", key=f"rev_{cn}"): db_set_approval(cn, False, get_name(), "Admin"); st.rerun()
                else:
                    if st.button(f"Approve {cn}", key=f"apv_{cn}"): db_set_approval(cn, True, get_name(), "Admin"); st.rerun()
        if st.button("🔄 Reset All Approvals", type="secondary"):
            db_reset_all_approvals(get_name()); st.rerun()
    
    # Log
    log = db_get_approval_log()
    if log:
        st.subheader("📋 Approval History")
        st.dataframe(pd.DataFrame(log)[["action","country","performed_by","role","created_at"]].head(20), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════
# PAGE: ANNOUNCEMENTS
# ═══════════════════════════════════════
def page_announcements():
    r = get_role()
    st.markdown("<div class='pro-header'><h1>📢 Announcements</h1><p>Project updates and important notices</p></div>", unsafe_allow_html=True)
    
    perm = get_permission("Announcements", r)
    if perm in ("write", "full"):
        with st.expander("➕ Post Announcement", expanded=False):
            with st.form("ann_form"):
                title = st.text_input("Title")
                content = st.text_area("Content", height=100)
                pri = st.select_slider("Priority", ["Low", "Medium", "High"], value="Medium")
                if st.form_submit_button("📢 Post", type="primary"):
                    if title and content:
                        db_add_announcement(title, content, get_name(), pri)
                        st.success("Posted!"); st.rerun()
    
    for a in db_get_announcements(): ann_card(a)


# ═══════════════════════════════════════
# PAGE: DOCUMENTS
# ═══════════════════════════════════════
def page_documents():
    r = get_role()
    st.markdown("<div class='pro-header'><h1>📁 Document Center</h1><p>Project files and deliverables</p></div>", unsafe_allow_html=True)
    
    if not SUPABASE_OK:
        st.warning("Document storage requires Supabase connection."); return
    
    perm = get_permission("Documents", r)
    if perm in ("upload", "full"):
        with st.expander("📤 Upload Document"):
            cat = st.selectbox("Category", ["Proposal Draft", "Meeting Minutes", "Budget", "Research", "Deliverable", "Template", "Other"])
            desc = st.text_input("Description")
            uf = st.file_uploader("File", type=["pdf","docx","xlsx","pptx","png","jpg","csv","md","txt"])
            if uf and st.button("📤 Upload", type="primary"):
                sp = f"documents/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uf.name}"
                if upload_to_storage(uf.getvalue(), sp, uf.type or "application/octet-stream"):
                    save_document_metadata(uf.name, uf.type, uf.size, cat, desc, get_name(), get_country(), sp)
                    st.success(f"✅ Uploaded: {uf.name}"); st.rerun()
    
    try:
        docs = sb().table("documents").select("*").eq("is_active", True).order("created_at", desc=True).execute().data or []
        if docs:
            st.subheader(f"📄 Documents ({len(docs)})")
            for d in docs:
                with st.expander(f"📄 {d.get('file_name','')} — {d.get('category','')}"):
                    st.markdown(f"**Category:** {d.get('category','')} | **By:** {d.get('uploaded_by','')} | **Date:** {str(d.get('created_at',''))[:10]}")
                    if d.get("description"): st.markdown(f"*{d['description']}*")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        data = download_from_storage(d.get("storage_path", ""))
                        if data: st.download_button("📥 Download", data, d.get("file_name","file"), use_container_width=True)
                    if r == "Admin":
                        with dc2:
                            if st.button("🗑️ Delete", key=f"del_doc_{d.get('id')}"):
                                delete_from_storage(d.get("storage_path", ""))
                                sb().table("documents").update({"is_active": False}).eq("id", d["id"]).execute()
                                st.success("Deleted!"); st.rerun()
        else: st.info("No documents uploaded yet.")
    except Exception as e: st.error(f"Error loading documents: {e}")


# ═══════════════════════════════════════
# PAGE: AI CENTER
# ═══════════════════════════════════════
def page_ai_center():
    st.markdown("<div class='pro-header'><h1>🧠 AI Decision Center</h1><p>AI-powered feedback analysis and proposal improvement</p></div>", unsafe_allow_html=True)
    
    if not AI_ENABLED:
        st.warning("AI engine not configured. Add OpenRouter or OpenAI API key to secrets."); return
    
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Analyze Feedback", "✍️ Section Revision", "📊 AI Decisions Log", "📋 Improvement Log"])
    
    with tab1:
        fbl = db_get_partner_feedback()
        open_fb = [f for f in fbl if f.get("status") == "Open"]
        if not open_fb: st.info("No open feedback to analyze."); return
        
        sel = st.selectbox("Select Feedback", [f"#{f.get('id')} [{f.get('section','')}] {f.get('feedback', f.get('content',''))[:80]}..." for f in open_fb])
        if sel:
            idx = int(sel.split("#")[1].split(" ")[0])
            fb = next((f for f in open_fb if f.get("id") == idx), None)
            if fb and st.button("🧠 Analyze with AI", type="primary"):
                with st.spinner("AI analyzing..."):
                    sec = fb.get("section", "")
                    sd = _find_section_for_feedback(sec)
                    sc = sd.get("content", "") if sd else ""
                    result = ai_analyze_feedback_v2(fb.get("feedback", fb.get("content", "")), sec, sc)
                    
                    st.json(result)
                    db_log_ai_decision(fb.get("id"), result.get("decision",""), result.get("confidence",0), result.get("reasoning",""), result.get("target_section",""))
                    
                    if result.get("decision") == "integrate" and result.get("suggested_text"):
                        st.markdown("### 📝 Suggested Revision")
                        st.markdown(result["suggested_text"])
                        if st.button("✅ Apply to Proposal"):
                            sk = sd.get("section_key", sec) if sd else sec
                            nv = db_update_section_content(sk, result["suggested_text"], "AI Engine", fb.get("id"))
                            db_log_improvement(fb.get("id"), sec, sc, result["suggested_text"], result.get("reasoning",""), "ai_integrate", "AI Engine")
                            db_update_feedback_status(fb.get("id"), "Accepted", f"AI integrated (v{nv})")
                            st.success(f"Applied! Section updated to v{nv}"); st.rerun()
    
    with tab2:
        st.markdown("### ✍️ Generate Section Revision")
        sections = db_get_proposal_sections()
        if not sections: st.info("No proposal sections loaded."); return
        sk_sel = st.selectbox("Section", [f"{s.get('section_key')} — {s.get('section_title','')}" for s in sections])
        if sk_sel:
            sk = sk_sel.split(" — ")[0]
            sd = db_get_section_by_key(sk)
            if sd:
                st.text_area("Current Content", sd.get("content", ""), height=150, disabled=True)
                fb_input = st.text_area("Feedback / Instruction", height=80, placeholder="What should be improved?")
                if fb_input and st.button("✍️ Generate Revision", type="primary"):
                    with st.spinner("AI writing..."):
                        revised = ai_generate_section_revision(sk, sd.get("content", ""), fb_input)
                        st.markdown("### Revised Version")
                        st.markdown(revised)
                        if st.button("✅ Apply Revision"):
                            nv = db_update_section_content(sk, revised, "AI Engine")
                            db_log_improvement(None, sd.get("section_title",""), sd.get("content",""), revised, fb_input, "ai_revision", "AI Engine")
                            st.success(f"Applied v{nv}!"); st.rerun()
    
    with tab3:
        decisions = db_get_ai_decisions()
        if decisions:
            st.dataframe(pd.DataFrame(decisions).head(50), use_container_width=True, hide_index=True)
        else: st.info("No AI decisions yet.")
    
    with tab4:
        imps = db_get_improvement_log()
        if imps:
            st.dataframe(pd.DataFrame(imps).head(50), use_container_width=True, hide_index=True)
        else: st.info("No improvements logged yet.")


# ═══════════════════════════════════════
# PAGE: ADMIN PANEL
# ═══════════════════════════════════════
def page_admin():
    st.markdown("<div class='pro-header'><h1>🛡️ Admin Panel</h1><p>System administration and proposal management</p></div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📝 Proposal Sections", "📥 Import Proposal", "📤 Export"])
    
    with tab1:
        st.markdown("### System Status")
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1: st.metric("Database", "Connected" if SUPABASE_OK else "Local")
        with sc2: st.metric("AI Engine", "Active" if AI_ENABLED else "Inactive")
        with sc3: st.metric("Export", "Ready" if EXPORT_OK else "Unavailable")
        with sc4: st.metric("Role", get_role())
        
        ap = db_get_approvals()
        fbc = len(db_get_partner_feedback())
        pfbc = len(db_get_patient_feedback())
        mc = len(db_get_meetings())
        
        st.markdown("### Data Summary")
        dc1, dc2, dc3, dc4 = st.columns(4)
        with dc1: st.metric("Partner Feedback", fbc)
        with dc2: st.metric("Patient Feedback", pfbc)
        with dc3: st.metric("AI Decisions", len(db_get_ai_decisions()))
        with dc4: st.metric("Meetings", mc)
    
    with tab2:
        sections = db_get_proposal_sections()
        if sections:
            for s in sections:
                with st.expander(f"📄 {s.get('section_title','')} (v{s.get('version',1)})"):
                    new_content = st.text_area("Content", s.get("content",""), height=200, key=f"sec_{s.get('section_key')}")
                    if st.button("💾 Save", key=f"save_{s.get('section_key')}"):
                        nv = db_update_section_content(s["section_key"], new_content, get_name())
                        st.success(f"Saved v{nv}!"); st.rerun()
        else:
            st.info("No proposal sections. Import a proposal below.")
    
    with tab3:
        st.markdown("### 📥 Import Proposal from Markdown")
        md_text = st.text_area("Paste full proposal markdown", height=300, placeholder="## Project Summary\n...\n## Problem Analysis\n...")
        if md_text and st.button("📥 Parse & Import", type="primary"):
            parsed = parse_proposal_md(md_text)
            if parsed:
                for sk, content in parsed.items():
                    st.markdown(f"**{sk}**: {len(content)} chars")
                if st.button("✅ Confirm Import"):
                    for sk, content in parsed.items():
                        title = sk.replace("_", " ").title()
                        if SUPABASE_OK:
                            try:
                                sb().table("proposal_sections").upsert({
                                    "section_key": sk, "section_title": title,
                                    "content": content, "version": 1,
                                    "last_updated_by": get_name(), "is_active": True
                                }).execute()
                            except: pass
                    st.success(f"Imported {len(parsed)} sections!"); st.rerun()
            else: st.warning("Could not parse sections. Use ## headings.")
    
    with tab4:
        st.markdown("### 📤 Export Data")
        if EXPORT_OK:
            ec1, ec2 = st.columns(2)
            with ec1:
                xl = generate_feedback_excel()
                if xl:
                    st.download_button("📥 Full Feedback Excel", xl, f"oncoconnect_feedback_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            with ec2:
                pdf = generate_feedback_pdf()
                if pdf:
                    st.download_button("📥 Full Feedback PDF", pdf, f"oncoconnect_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                                      "application/pdf", use_container_width=True)
            
            # Meeting export
            st.markdown("---")
            st.markdown("### 📅 Meeting Export")
            meetings = db_get_meetings()
            if meetings:
                mdf = pd.DataFrame(meetings)
                csv = mdf.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Meetings CSV", csv, "meetings_export.csv", "text/csv", use_container_width=True)
        else:
            st.warning("Install openpyxl and fpdf2 for export functionality.")


# ═══════════════════════════════════════
# PAGE: USER MANAGEMENT
# ═══════════════════════════════════════
def page_user_management():
    st.markdown("<div class='pro-header'><h1>👥 User Management</h1><p>Manage platform users and permissions</p></div>", unsafe_allow_html=True)
    
    if not SUPABASE_OK:
        st.info("User management requires Supabase. Showing built-in users.")
        df = pd.DataFrame([{"Username": k, "Name": v["name"], "Role": v["role"], "Country": v["country"], "Org": v["org"]} for k, v in USERS_DB.items()])
        st.dataframe(df, use_container_width=True, hide_index=True)
        return
    
    try:
        users = sb().table("app_users").select("*").execute().data or []
        if users:
            df = pd.DataFrame(users)
            cols_show = [c for c in ["username","display_name","role","country","organisation","is_active","last_login"] if c in df.columns]
            st.dataframe(df[cols_show], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### ➕ Add User")
        with st.form("add_user"):
            uc1, uc2 = st.columns(2)
            with uc1:
                nu = st.text_input("Username")
                nn = st.text_input("Display Name")
                np2 = st.text_input("Password", type="password")
            with uc2:
                nr = st.selectbox("Role", ["Admin", "Partner", "Patient"])
                nc = st.selectbox("Country", ["Turkey", "Poland", "Spain", "All", "N/A"])
                no = st.text_input("Organisation")
            if st.form_submit_button("➕ Add User", type="primary"):
                if nu and nn and np2:
                    try:
                        sb().table("app_users").insert({
                            "username": nu.lower(), "password_hash": np2,
                            "display_name": nn, "role": nr, "country": nc,
                            "organisation": no, "is_active": True
                        }).execute()
                        st.success(f"User '{nu}' created!"); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
    except Exception as e: st.error(f"Error: {e}")


# ═══════════════════════════════════════
# SIDEBAR + MAIN
# ═══════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
        <div style='text-align:center;padding:1rem 0;'>
            <div style='font-size:2.5rem;'>🧬</div>
            <h2 style='color:#2ABFBF;margin:0.3rem 0;font-size:1.3rem;'>OncoConnect</h2>
            <p style='color:#64748b;font-size:0.75rem;margin:0;'>Co-Creation Hub v4.0</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        r = get_role()
        badge = ROLE_BADGES.get(r, r)
        cn = get_country()
        flag = FLAGS.get(cn, "🌍")
        
        st.markdown(f"""
        <div style='background:rgba(42,191,191,0.1);border-radius:12px;padding:1rem;margin-bottom:1rem;'>
            <p style='margin:0;color:#2ABFBF;font-weight:600;'>{get_name()}</p>
            <p style='margin:0.2rem 0;color:#94a3b8;font-size:0.85rem;'>{badge}</p>
            <p style='margin:0;color:#94a3b8;font-size:0.85rem;'>{flag} {cn} | {get_org()}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        pages = []
        all_pages = ["Dashboard", "Work Packages", "Gantt Chart", "Partners", "Partner Feedback",
                     "Patient Feedback", "Approval Status", "Announcements", "Documents", "Meetings",
                     "🧠 AI Center", "Admin Panel", "User Management"]
        
        for p in all_pages:
            if check_access(p, r): pages.append(p)
        
        page_icons = {"Dashboard": "📊", "Work Packages": "📦", "Gantt Chart": "📅", "Partners": "🤝",
                     "Partner Feedback": "💬", "Patient Feedback": "💚", "Approval Status": "🗳️",
                     "Announcements": "📢", "Documents": "📁", "Meetings": "📅",
                     "🧠 AI Center": "🧠", "Admin Panel": "🛡️", "User Management": "👥"}
        
        page = st.radio("Navigation", pages, format_func=lambda x: f"{page_icons.get(x,'')} {x}", label_visibility="collapsed")
        
        st.markdown("---")
        
        # Quick status
        ap = db_get_approvals()
        an = sum(1 for v in ap.values() if v)
        st.markdown(f"""
        <div style='font-size:0.8rem;color:#94a3b8;'>
            <p>🔗 DB: {'✅' if SUPABASE_OK else '⚠️'} | 🧠 AI: {'✅' if AI_ENABLED else '⚠️'}</p>
            <p>🗳️ Approvals: {an}/3 | 📤 Export: {'✅' if EXPORT_OK else '⚠️'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Next meeting quick view
        meetings = db_get_meetings()
        today_str = str(date.today())
        upcoming = sorted([m for m in meetings if str(m.get("meeting_date","")) >= today_str], key=lambda x: str(x.get("meeting_date","")))
        if upcoming:
            nm = upcoming[0]
            st.markdown(f"""
            <div style='background:rgba(45,140,255,0.1);border-radius:10px;padding:0.8rem;margin-top:0.5rem;'>
                <p style='margin:0;font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:1px;'>Next Meeting</p>
                <p style='margin:0.2rem 0;color:#2D8CFF;font-weight:600;font-size:0.85rem;'>{nm.get("title","")[:30]}</p>
                <p style='margin:0;color:#94a3b8;font-size:0.8rem;'>📅 {nm.get("meeting_date","")} 🕐 {str(nm.get("start_time",""))[:5]}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True): logout()
        
        st.markdown(f"<p style='text-align:center;font-size:0.7rem;color:#475569;margin-top:1rem;'>© 2025 OncoConnect<br>Erasmus+ KA210</p>", unsafe_allow_html=True)
        
        return page


def main():
    init_session()
    if not render_login(): return
    inject_pro_css()
    
    page = render_sidebar()
    wp_df, pf = load_static()
    
    if page == "Dashboard":
         page_dashboard(wp_df, partners_df)
    elif page == "Work Packages": page_work_packages(wp_df)
    elif page == "Gantt Chart": page_gantt(wp_df)
    elif page == "Partners": page_partners(pf)
    elif page == "Partner Feedback": page_partner_feedback()
    elif page == "Patient Feedback": page_patient_feedback()
    elif page == "Approval Status": page_approval()
    elif page == "Announcements": page_announcements()
    elif page == "Documents": page_documents()
    elif page == "Meetings": page_meetings()
    elif page == "🧠 AI Center": page_ai_center()
    elif page == "Admin Panel": page_admin()
    elif page == "User Management": page_user_management()


if __name__ == "__main__":
    main()
