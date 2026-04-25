"""
OncoConnect Co-Creation Hub
Erasmus+ KA210 Small-Scale Partnership
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════
# PAGE CONFIG (must be first Streamlit command)
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

    # Test connection
    _client = get_supabase()
    SUPABASE_OK = True

except Exception as e:
    st.sidebar.error(f"⚠️ Supabase: {e}")
    SUPABASE_OK = False


def sb():
    if SUPABASE_OK:
        return get_supabase()
    return None


# ═══════════════════════════════════════════════════
# DB FUNCTIONS (with fallback)
# ═══════════════════════════════════════════════════
def db_get_approvals() -> dict:
    default = {"Turkey": False, "Poland": False, "Spain": False}
    if not SUPABASE_OK:
        return st.session_state.get("local_approvals", default)
    try:
        res = sb().table("approvals").select("country, approved").execute()
        return {row["country"]: row["approved"] for row in res.data}
    except Exception as e:
        st.error(f"DB Error: {e}")
        return default


def db_set_approval(country_name: str, approved: bool, performed_by: str, user_role: str):
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


def db_get_approval_log() -> list:
    if not SUPABASE_OK:
        return []
    try:
        res = sb().table("approval_log").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception:
        return []


def db_get_partner_feedback() -> list:
    if not SUPABASE_OK:
        return st.session_state.get("local_feedback", [])
    try:
        res = sb().table("partner_feedback").select("*").order("created_at", desc=True).execute()
        return res.data
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


def db_update_feedback_status(fb_id: int, new_status: str, response: str = None):
    if not SUPABASE_OK:
        return
    try:
        data = {"status": new_status}
        if response:
            data["response"] = response
        sb().table("partner_feedback").update(data).eq("id", fb_id).execute()
    except Exception as e:
        st.error(f"DB Error: {e}")


def db_get_patient_feedback() -> list:
    if not SUPABASE_OK:
        return st.session_state.get("local_patient_fb", [])
    try:
        res = sb().table("patient_feedback").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception:
        return []


def db_add_patient_feedback(data: dict):
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


def db_get_announcements() -> list:
    if not SUPABASE_OK:
        return st.session_state.get("local_announcements", [])
    try:
        res = sb().table("announcements").select("*").order("created_at", desc=True).execute()
        return res.data
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


# ═══════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════
@st.cache_data
def load_csv(path):
    return pd.read_csv(path)


def load_static():
    wp = load_csv("data/work_packages.csv")
    partners = load_csv("data/partners.csv")
    return wp, partners


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
        "<p style='color:#777;'>Erasmus+ KA210 — Peer mentorship for cancer patients</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    blank1, col, blank2 = st.columns([1, 2, 1])
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
            st.markdown("""
            | User | Pass | Role |
            |------|------|------|
            | admin | admin123 | Admin |
            | turkey | tr2025 | Partner TR |
            | poland | pl2025 | Partner PL |
            | spain | es2025 | Partner ES |
            | patient | patient123 | Patient |
            """)
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
    prep_remaining = max(0, (SUBMISSION_DEADLINE - now).days)
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

    if prep_progress < 0.5:
        prep_color = "#a855f7"
    elif prep_progress < 0.8:
        prep_color = "#f59e0b"
    else:
        prep_color = "#ef4444"

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown(
            f"""
            <div style="
                background:linear-gradient(135deg,#1a1a2e,#2d1b4e);
                border-radius:16px; padding:1.5rem; text-align:center;
                color:white; min-height:280px;
            ">
                <p style="margin:0;font-size:.75rem;opacity:.7;letter-spacing:2px;">
                    PREPARATION PHASE</p>
                <p style="margin:.3rem 0 0;font-size:.85rem;opacity:.8;">
                    Co-creation and proposal development</p>
                <div style="
                    margin:1rem auto; width:120px; height:120px;
                    border-radius:50%;
                    background:conic-gradient({prep_color} {deg}deg, #333 0deg);
                    display:flex; align-items:center; justify-content:center;
                ">
                    <div style="
                        width:100px; height:100px; border-radius:50%;
                        background:#1a1a2e; display:flex;
                        align-items:center; justify-content:center;
                        flex-direction:column;
                    ">
                        <span style="font-size:1.8rem;font-weight:bold;color:{prep_color};">
                            {pct}%</span>
                        <span style="font-size:.65rem;opacity:.6;">COMPLETE</span>
                    </div>
                </div>
                <p style="margin:0;font-size:.8rem;opacity:.6;">
                    Started: {PREPARATION_START.strftime('%d %b %Y')} |
                    Elapsed: {prep_elapsed} days
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(
            f"""
            <div style="
                background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);
                border-radius:16px; padding:1.5rem; text-align:center;
                color:white; min-height:280px;
            ">
                <p style="margin:0;font-size:.75rem;opacity:.7;letter-spacing:2px;">
                    SUBMISSION DEADLINE</p>
                <p style="margin:.3rem 0 0;font-size:.85rem;opacity:.8;">
                    {SUBMISSION_DEADLINE.strftime('%d %B %Y, %H:%M')}</p>
                <div style="
                    display:flex; justify-content:center;
                    gap:1.5rem; margin:1.2rem 0;
                ">
                    <div>
                        <span style="font-size:2.8rem;font-weight:bold;color:{sub_color};">
                            {days}</span>
                        <br><span style="font-size:.75rem;opacity:.6;">DAYS</span>
                    </div>
                    <div>
                        <span style="font-size:2.8rem;font-weight:bold;color:{sub_color};">
                            {hours:02d}</span>
                        <br><span style="font-size:.75rem;opacity:.6;">HOURS</span>
                    </div>
                    <div>
                        <span style="font-size:2.8rem;font-weight:bold;color:{sub_color};">
                            {minutes:02d}</span>
                        <br><span style="font-size:.75rem;opacity:.6;">MIN</span>
                    </div>
                </div>
                <p style="margin:0;font-size:.8rem;opacity:.6;">
                    Erasmus+ KA210 Expected Call 2027
                </p>
            </div>
            """,
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
        f"<br><span style='font-size:.8rem;color:#999;'>By: {row.get('author','')}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════
def page_dashboard(wp_df, partners_df):
    st.title("🧬 OncoConnect Co-Creation Hub")
    st.caption("Erasmus+ KA210 — Peer mentorship for cancer patients")
    render_countdown()

    approvals = db_get_approvals()
    fb_count = len(db_get_partner_feedback())
    approved_n = sum(1 for v in approvals.values() if v)
    remaining_days = (SUBMISSION_DEADLINE - datetime.now()).days

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Work Packages", len(wp_df))
    c2.metric("Partners", len(partners_df))
    c3.metric("Feedback", fb_count)
    c4.metric("Approvals", f"{approved_n}/3")
    c5.metric("Days Left", remaining_days)

    st.subheader("Partner Approval Status")
    ac1, ac2, ac3 = st.columns(3)
    for col, cname in zip([ac1, ac2, ac3], ["Turkey", "Poland", "Spain"]):
        ok = approvals.get(cname, False)
        org = PARTNER_MAP[cname]
        with col:
            if ok:
                st.success(f"{FLAGS[cname]} {org} — Approved")
            else:
                st.warning(f"{FLAGS[cname]} {org} — Pending")

    ch1, ch2 = st.columns(2)
    with ch1:
        st.subheader("Budget Distribution")
        if "budget_eur" in wp_df.columns:
            fig = px.pie(wp_df, names="wp_id", values="budget_eur",
                         hover_data=["wp_name"],
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
    with ch2:
        st.subheader("WP Status")
        sc = wp_df["status"].value_counts().reset_index()
        sc.columns = ["status", "count"]
        fig2 = px.bar(sc, x="status", y="count", color="status")
        fig2.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Work Packages")
    display_cols = [c for c in ["wp_id", "wp_name", "lead_country", "start_month", "end_month", "status", "budget_eur"] if c in wp_df.columns]
    st.dataframe(wp_df[display_cols], use_container_width=True, hide_index=True)

    st.subheader("Latest Announcements")
    anns = db_get_announcements()[:3]
    for a in anns:
        ann_card(a)


def page_work_packages(wp_df):
    st.title("Work Packages")
    sel = st.selectbox("Select", wp_df["wp_id"].tolist())
    wp = wp_df[wp_df["wp_id"] == sel].iloc[0]

    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader(f"{wp['wp_id']}: {wp['wp_name']}")
        st.write(f"**Lead:** {wp['lead_partner']} ({wp.get('lead_country', '')})")
        st.write(f"**Supporting:** {wp['supporting_partners']}")
        st.write(f"**Duration:** M{wp['start_month']} to M{wp['end_month']}")
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


def page_gantt(wp_df):
    st.title("📊 Interactive Gantt Chart — 18 Months")

    g = wp_df.copy()
    g["Start"] = g["start_month"].apply(lambda m: PROJECT_START + timedelta(days=(m - 1) * 30))
    g["Finish"] = g["end_month"].apply(lambda m: PROJECT_START + timedelta(days=m * 30))
    g["Task"] = g["wp_id"] + ": " + g["wp_name"]
    g["Duration (months)"] = g["end_month"] - g["start_month"]
    lc = "lead_country" if "lead_country" in g.columns else "lead_partner"

    # ── Filters ──
    st.subheader("🔍 Filters")
    fc1, fc2, fc3 = st.columns(3)

    with fc1:
        countries = g[lc].unique().tolist()
        sel_countries = st.multiselect("Lead Country", countries, default=countries)
    with fc2:
        statuses = g["status"].unique().tolist()
        sel_status = st.multiselect("Status", statuses, default=statuses)
    with fc3:
        view_mode = st.radio("View Mode", ["Timeline", "Duration Bars", "Both"], horizontal=True)

    # Apply filters
    filtered = g[g[lc].isin(sel_countries) & g["status"].isin(sel_status)]

    if filtered.empty:
        st.warning("No work packages match the selected filters.")
        return

    # ── Timeline View ──
    if view_mode in ("Timeline", "Both"):
        st.subheader("📅 Timeline View")

        # Build hover text
        filtered["hover"] = filtered.apply(
            lambda r: (
                f"<b>{r['wp_id']}: {r['wp_name']}</b><br>"
                f"Lead: {r['lead_partner']} ({r.get(lc, '')})<br>"
                f"Duration: M{r['start_month']}–M{r['end_month']} ({r['Duration (months)']} months)<br>"
                f"Status: {r['status']}<br>"
                f"Budget: €{r['budget_eur']:,.0f}" if "budget_eur" in r.index else
                f"<b>{r['wp_id']}: {r['wp_name']}</b><br>"
                f"Lead: {r['lead_partner']}<br>"
                f"M{r['start_month']}–M{r['end_month']}"
            ),
            axis=1,
        )

        fig = px.timeline(
            filtered,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color=lc,
            hover_data={
                "lead_partner": True,
                "status": True,
                "Duration (months)": True,
                "Start": False,
                "Finish": False,
                "Task": False,
                lc: False,
            },
            color_discrete_map={
                "Turkey": "#e74c3c",
                "Poland": "#3498db",
                "Spain": "#f39c12",
            },
        )

        fig.update_yaxes(autorange="reversed")

        # Today marker
        today = datetime.now()
        fig.add_shape(
            type="line",
            x0=today, x1=today, y0=0, y1=1,
            yref="paper",
            line=dict(color="red", width=2, dash="dash"),
        )
        fig.add_annotation(
            x=today, y=1.06, yref="paper",
            text=f"📍 Today ({today.strftime('%d %b %Y')})",
            showarrow=False,
            font=dict(color="red", size=11, family="Arial Black"),
        )

        # Project milestones
        milestones = [
            {"month": 1, "label": "Kickoff", "color": "#28a745"},
            {"month": 6, "label": "Needs Report", "color": "#17a2b8"},
            {"month": 10, "label": "Matching Protocol", "color": "#f39c12"},
            {"month": 15, "label": "Pilot Complete", "color": "#e74c3c"},
            {"month": 18, "label": "Final Report", "color": "#6f42c1"},
        ]

        for ms in milestones:
            ms_date = PROJECT_START + timedelta(days=(ms["month"] - 1) * 30)
            fig.add_shape(
                type="line",
                x0=ms_date, x1=ms_date, y0=0, y1=1,
                yref="paper",
                line=dict(color=ms["color"], width=1, dash="dot"),
            )
            fig.add_annotation(
                x=ms_date, y=-0.08, yref="paper",
                text=f"M{ms['month']}: {ms['label']}",
                showarrow=False,
                font=dict(color=ms["color"], size=9),
                textangle=-45,
            )

        # Status pattern
        for i, row in filtered.iterrows():
            if row["status"] == "Completed":
                fig.add_annotation(
                    x=row["Finish"], y=row["Task"],
                    text="✅", showarrow=False, font=dict(size=16),
                )
            elif row["status"] == "In Progress":
                fig.add_annotation(
                    x=row["Start"], y=row["Task"],
                    text="🔄", showarrow=False, font=dict(size=14),
                    xshift=-15,
                )

        fig.update_layout(
            height=500,
            xaxis_title="",
            yaxis_title="",
            hovermode="closest",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                title="Lead Country",
            ),
            margin=dict(b=100),
        )

        # Range slider
        fig.update_xaxes(
            rangeslider_visible=True,
            rangeslider_thickness=0.08,
        )

        st.plotly_chart(fig, use_container_width=True)

    # ── Duration Bars ──
    if view_mode in ("Duration Bars", "Both"):
        st.subheader("⏱️ Duration Comparison")

        fig2 = px.bar(
            filtered,
            x="Duration (months)",
            y="Task",
            color=lc,
            orientation="h",
            text="Duration (months)",
            hover_data=["lead_partner", "status", "start_month", "end_month"],
            color_discrete_map={
                "Turkey": "#e74c3c",
                "Poland": "#3498db",
                "Spain": "#f39c12",
            },
        )

        # Add budget as secondary info
        if "budget_eur" in filtered.columns:
            for i, row in filtered.iterrows():
                fig2.add_annotation(
                    x=row["Duration (months)"],
                    y=row["Task"],
                    text=f"€{row['budget_eur']:,.0f}",
                    showarrow=False,
                    xshift=35,
                    font=dict(size=10, color="#666"),
                )

        fig2.update_traces(textposition="inside", textfont_size=12)
        fig2.update_layout(
            height=400,
            yaxis=dict(autorange="reversed"),
            xaxis_title="Duration (months)",
            yaxis_title="",
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Summary Stats ──
    st.subheader("📈 Summary")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total WPs", len(filtered))
    sc2.metric("Avg Duration", f"{filtered['Duration (months)'].mean():.1f} mo")
    if "budget_eur" in filtered.columns:
        sc3.metric("Total Budget", f"€{filtered['budget_eur'].sum():,.0f}")
        sc4.metric("Avg Budget", f"€{filtered['budget_eur'].mean():,.0f}")

    # ── WP Detail on Click ──
    st.subheader("📦 Work Package Details")
    selected_wp = st.selectbox(
        "Select a work package to view details",
        filtered["wp_id"].tolist(),
        format_func=lambda x: f"{x}: {filtered[filtered['wp_id']==x]['wp_name'].values[0]}",
    )

    if selected_wp:
        wp = filtered[filtered["wp_id"] == selected_wp].iloc[0]
        dc1, dc2, dc3 = st.columns(3)

        with dc1:
            st.markdown(f"**Lead:** {wp['lead_partner']}")
            st.markdown(f"**Country:** {FLAGS.get(wp.get(lc, ''), '')} {wp.get(lc, '')}")
            st.markdown(f"**Supporting:** {wp['supporting_partners']}")

        with dc2:
            st.markdown(f"**Period:** Month {wp['start_month']} → Month {wp['end_month']}")
            st.markdown(f"**Duration:** {wp['Duration (months)']} months")
            st.markdown(f"**Status:** {wp['status']}")

        with dc3:
            if "budget_eur" in wp.index:
                st.metric("Budget", f"€{wp['budget_eur']:,.0f}")
                pct = wp["budget_eur"] / TOTAL_BUDGET * 100
                st.progress(pct / 100)
                st.caption(f"{pct:.1f}% of total budget")

        if "description" in wp.index:
            st.info(f"**Description:** {wp['description']}")
        if "deliverables" in wp.index:
            st.markdown("**Deliverables:**")
            for d in str(wp["deliverables"]).split(";"):
                st.markdown(f"- {d.strip()}")

    # ── Overlap Analysis ──
    st.subheader("🔗 WP Overlap Analysis")
    overlap_data = []
    wps = filtered.to_dict("records")
    for i, w1 in enumerate(wps):
        for w2 in wps[i+1:]:
            start = max(w1["start_month"], w2["start_month"])
            end = min(w1["end_month"], w2["end_month"])
            if start < end:
                overlap_data.append({
                    "WP Pair": f"{w1['wp_id']} + {w2['wp_id']}",
                    "Overlap": f"M{start}–M{end}",
                    "Months": end - start,
                })

    if overlap_data:
        ov_df = pd.DataFrame(overlap_data).sort_values("Months", ascending=False)
        fig3 = px.bar(ov_df, x="Months", y="WP Pair", orientation="h",
                       text="Overlap", color="Months",
                       color_continuous_scale="YlOrRd")
        fig3.update_layout(height=300, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No overlapping work packages in current selection.")

def page_partners(partners_df):
    st.title("OncoConnect Consortium")
    for _, p in partners_df.iterrows():
        flag = FLAGS.get(p["country"], "")
        st.markdown(f"### {flag} {p['organisation']}")
        st.write(f"**Country:** {p['country']} | **Role:** {p['role']} | **Type:** {p.get('type', 'N/A')}")
        st.write(p.get("description", ""))
        st.divider()

    st.subheader("Partner Locations")
    st.map(pd.DataFrame({"lat": [39.93, 52.23, 41.39], "lon": [32.86, 21.01, 2.17]}), zoom=3)


def page_partner_feedback():
    st.title("Partner Feedback")
    r = get_role()
    c = get_country()

    if r in ("Admin", "Partner"):
        with st.form("fb_form", clear_on_submit=True):
            if r == "Partner":
                fb_country = c
                fb_org = get_org()
                st.write(f"**Partner:** {FLAGS.get(c, '')} {fb_org}")
            else:
                fb_country = st.selectbox("Country", ["Turkey", "Poland", "Spain"])
                fb_org = PARTNER_MAP.get(fb_country, "")

            section = st.selectbox("Section", [
                "Needs Analysis", "Objectives", "Methodology", "Work Packages",
                "Impact", "Dissemination", "Budget", "Ethics/Data Protection",
            ])
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
        st.dataframe(df, use_container_width=True, hide_index=True)

        if r == "Admin":
            st.subheader("Update Status")
            fb_id = st.selectbox("Feedback ID", df["id"].tolist())
            new_status = st.selectbox("Status", ["Open", "Under Review", "Accepted", "Rejected"])
            resp = st.text_input("Response")
            if st.button("Update"):
                db_update_feedback_status(fb_id, new_status, resp if resp else None)
                st.success("Updated!")
                st.rerun()
    else:
        st.info("No feedback yet.")


def page_patient_feedback():
    st.title("Patient Feedback")
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
            st.success("Thank you for your feedback!")
            st.balloons()

    if get_role() == "Admin":
        rows = db_get_patient_feedback()
        if rows:
            st.divider()
            st.subheader("Patient Feedback Data")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def page_approval():
    st.title("Proposal Approval Status")
    approvals = db_get_approvals()
    r = get_role()
    c = get_country()

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
                    report = json.dumps({
                        "project": "OncoConnect", "status": "Approved",
                        "approvals": approvals,
                        "exported": datetime.now().isoformat(),
                    }, indent=2)
                    st.download_button("Approval Report", report,
                                       "Approval_Report.json", "application/json",
                                       use_container_width=True)
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


def page_announcements():
    st.title("Announcements")
    anns = db_get_announcements()
    for a in anns:
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


def page_documents():
    st.title("Project Documents")
    t1, t2, t3 = st.tabs(["Proposal", "Resources", "Budget"])

    with t1:
        try:
            with open("documents/proposal_draft.md", "r", encoding="utf-8") as f:
                text = f.read()
            st.markdown(text)
            if get_role() == "Admin":
                st.download_button("Download", text, "proposal_draft.md",
                                   "text/markdown", use_container_width=True)
        except FileNotFoundError:
            st.warning("File not found.")

    with t2:
        st.markdown("""
        **Planned Documents:**
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


def page_admin():
    st.title("Admin Panel")
    if get_role() != "Admin":
        st.error("Access denied.")
        return

    t1, t2, t3 = st.tabs(["Overview", "Data", "Export"])

    with t1:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Feedback", len(db_get_partner_feedback()))
        m2.metric("Patient FB", len(db_get_patient_feedback()))
        m3.metric("Announcements", len(db_get_announcements()))
        approvals = db_get_approvals()
        m4.metric("Approvals", f"{sum(1 for v in approvals.values() if v)}/3")
        if SUPABASE_OK:
            st.success("Supabase: Connected")
        else:
            st.warning("Supabase: Not connected (using local fallback)")

    with t2:
        fb = db_get_partner_feedback()
        if fb:
            st.subheader("Partner Feedback")
            st.dataframe(pd.DataFrame(fb), use_container_width=True, hide_index=True)
        pf = db_get_patient_feedback()
        if pf:
            st.subheader("Patient Feedback")
            st.dataframe(pd.DataFrame(pf), use_container_width=True, hide_index=True)

    with t3:
        export = {
            "project": "OncoConnect",
            "exported": datetime.now().isoformat(),
            "approvals": db_get_approvals(),
            "feedback": db_get_partner_feedback(),
            "patient_feedback": db_get_patient_feedback(),
            "announcements": db_get_announcements(),
        }
        st.download_button("Export All (JSON)",
                           json.dumps(export, indent=2, ensure_ascii=False, default=str),
                           "oncoconnect_export.json", "application/json",
                           use_container_width=True, type="primary")

        if st.button("Reset Approvals"):
            for cname in ["Turkey", "Poland", "Spain"]:
                db_set_approval(cname, False, "Admin", "Admin")
            st.success("Reset done.")
            st.rerun()


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
                 "Announcements", "Documents", "Admin Panel"]
    elif r == "Partner":
        pages = ["Dashboard", "Work Packages", "Gantt Chart", "Partners",
                 "Partner Feedback", "Patient Feedback", "Approval Status",
                 "Announcements", "Documents"]
    else:
        pages = ["Dashboard", "Patient Feedback", "Announcements", "Documents"]

    page = st.sidebar.radio("Navigation", pages)
    st.sidebar.divider()

    if SUPABASE_OK:
        st.sidebar.success("DB: Connected")
    else:
        st.sidebar.warning("DB: Local mode")

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
    elif page == "Admin Panel":
        page_admin()


if __name__ == "__main__":
    main()
