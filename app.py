"""
OncoConnect Co-Creation Hub
Erasmus+ KA210 Small-Scale Partnership
Supabase-backed version
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════
# SUPABASE CONNECTION (inline — no separate file needed)
# ═══════════════════════════════════════════════════
from supabase import create_client, Client


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def sb() -> Client:
    return get_supabase()


# ── Supabase CRUD Functions ──
def db_get_approvals() -> dict:
    try:
        res = sb().table("approvals").select("country, approved").execute()
        return {row["country"]: row["approved"] for row in res.data}
    except Exception as e:
        st.error(f"DB Error (approvals): {e}")
        return {"Turkey": False, "Poland": False, "Spain": False}


def db_set_approval(country: str, approved: bool, performed_by: str, role: str):
    now = datetime.utcnow().isoformat()
    sb().table("approvals").update({
        "approved": approved,
        "approved_by": performed_by if approved else None,
        "approved_at": now if approved else None,
        "updated_at": now,
    }).eq("country", country).execute()

    sb().table("approval_log").insert({
        "action": "approved" if approved else "revoked",
        "country": country,
        "performed_by": performed_by,
        "role": role,
    }).execute()


def db_get_approval_log() -> list:
    try:
        res = sb().table("approval_log").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception:
        return []


def db_get_partner_feedback() -> list:
    try:
        res = sb().table("partner_feedback").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception:
        return []


def db_add_partner_feedback(partner_country, organisation, section, feedback, priority, submitted_by):
    sb().table("partner_feedback").insert({
        "partner_country": partner_country,
        "organisation": organisation,
        "section": section,
        "feedback": feedback,
        "priority": priority,
        "status": "Open",
        "submitted_by": submitted_by,
    }).execute()


def db_update_feedback_status(feedback_id: int, new_status: str, response: str = None):
    data = {"status": new_status}
    if response:
        data["response"] = response
    sb().table("partner_feedback").update(data).eq("id", feedback_id).execute()


def db_get_patient_feedback() -> list:
    try:
        res = sb().table("patient_feedback").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception:
        return []


def db_add_patient_feedback(data: dict):
    sb().table("patient_feedback").insert(data).execute()


def db_get_announcements() -> list:
    try:
        res = sb().table("announcements").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception:
        return []


def db_add_announcement(title, content, author, priority):
    sb().table("announcements").insert({
        "title": title,
        "content": content,
        "author": author,
        "priority": priority,
    }).execute()


# ═══════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════
st.set_page_config(
    page_title="OncoConnect Co-Creation Hub",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

SUBMISSION_DEADLINE = datetime(2026, 11, 15, 17, 0, 0)
PROJECT_START = datetime(2025, 9, 1)
TOTAL_BUDGET = 60_000

PARTNER_MAP = {
    "Turkey": "Kanser Savaşçıları Derneği",
    "Poland": "Fundacja Onkologiczna Rakiety",
    "Spain": "Universitat de Barcelona",
}
FLAGS = {"Turkey": "🇹🇷", "Poland": "🇵🇱", "Spain": "🇪🇸"}
ROLE_BADGES = {"Admin": "🛡️ Admin", "Partner": "🤝 Partner", "Patient": "💚 Patient"}

# ═══════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════
USERS_DB = {
    "admin": {"password": "admin123", "name": "Project Admin", "role": "Admin", "country": "All", "org": "OncoConnect Consortium"},
    "turkey": {"password": "tr2025", "name": "KSD Coordinator", "role": "Partner", "country": "Turkey", "org": "Kanser Savaşçıları Derneği"},
    "poland": {"password": "pl2025", "name": "Rakiety Team", "role": "Partner", "country": "Poland", "org": "Fundacja Onkologiczna Rakiety"},
    "spain": {"password": "es2025", "name": "UB Research Team", "role": "Partner", "country": "Spain", "org": "Universitat de Barcelona"},
    "patient": {"password": "patient123", "name": "Patient Participant", "role": "Patient", "country": "N/A", "org": "N/A"},
}

# ═══════════════════════════════════════════════════
# DATA LOADERS (only CSV — static data)
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
def render_login() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        """
        <div style="text-align:center;padding:3rem 0 1rem;">
            <h1 style="font-size:2.8rem;">🧬 OncoConnect</h1>
            <h3 style="color:#555;font-weight:400;">Co-Creation Hub</h3>
            <p style="color:#777;max-width:600px;margin:auto;">
                Erasmus+ KA210 Small-Scale Partnership<br>
                Structured peer mentorship for cancer patients across Europe
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("### 🔐 Login")
        with st.form("login"):
            username = st.text_input("Username", placeholder="admin / turkey / poland / spain / patient")
            password = st.text_input("Password", type="password")
            go = st.form_submit_button("Login", use_container_width=True, type="primary")
            if go:
                u = USERS_DB.get(username)
                if u and u["password"] == password:
                    st.session_state.update(
                        authenticated=True,
                        username=username,
                        user_name=u["name"],
                        user_role=u["role"],
                        user_country=u["country"],
                        user_org=u["org"],
                    )
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

        with st.expander("ℹ️ Demo Credentials"):
            st.dataframe(
                pd.DataFrame([
                    ["admin", "admin123", "Admin", "All"],
                    ["turkey", "tr2025", "Partner", "🇹🇷 Turkey"],
                    ["poland", "pl2025", "Partner", "🇵🇱 Poland"],
                    ["spain", "es2025", "Partner", "🇪🇸 Spain"],
                    ["patient", "patient123", "Patient", "—"],
                ], columns=["Username", "Password", "Role", "Country"]),
                hide_index=True, use_container_width=True,
            )
    return False


def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


def R():
    return st.session_state.get("user_role", "Patient")

def C():
    return st.session_state.get("user_country", "N/A")

def UN():
    return st.session_state.get("user_name", "User")

def UO():
    return st.session_state.get("user_org", "N/A")


# ═══════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════
def render_countdown():
    now = datetime.now()
    rem = SUBMISSION_DEADLINE - now
    if rem.total_seconds() <= 0:
        st.error("⏰ **SUBMISSION DEADLINE PASSED!**")
        return
    days = rem.days
    hours, r2 = divmod(rem.seconds, 3600)
    minutes, _ = divmod(r2, 60)
    total_span = max((SUBMISSION_DEADLINE - datetime(2025, 5, 1)).days, 1)
    progress = max(0.0, min(1.0, 1 - days / total_span))
    color = "#28a745" if days > 365 else "#17a2b8" if days > 180 else "#ffc107" if days > 60 else "#dc3545"

    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);
            border-radius:16px;padding:1.5rem;text-align:center;color:white;margin-bottom:1rem;">
            <p style="margin:0;font-size:.9rem;opacity:.8;">
                ⏱️ SUBMISSION DEADLINE: {SUBMISSION_DEADLINE.strftime('%d %B %Y')}</p>
            <div style="display:flex;justify-content:center;gap:2rem;margin:1rem 0;">
                <div><span style="font-size:2.5rem;font-weight:bold;color:{color};">{days}</span>
                    <br><span style="font-size:.8rem;opacity:.7;">DAYS</span></div>
                <div><span style="font-size:2.5rem;font-weight:bold;color:{color};">{hours:02d}</span>
                    <br><span style="font-size:.8rem;opacity:.7;">HOURS</span></div>
                <div><span style="font-size:2.5rem;font-weight:bold;color:{color};">{minutes:02d}</span>
                    <br><span style="font-size:.8rem;opacity:.7;">MIN</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(progress)


def card_html(title, value, border="#ddd"):
    st.markdown(
        f"""
        <div style="border:2px solid {border};border-radius:12px;
            padding:1rem;text-align:center;background:white;">
            <p style="margin:0;font-size:.85rem;color:#888;">{title}</p>
            <p style="margin:0;font-size:1.6rem;font-weight:700;">{value}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ann_card(row):
    p = row.get("priority", "Low")
    icon = {"High": "🔴", "Medium": "🟡"}.get(p, "🟢")
    border = {"High": "#dc3545", "Medium": "#ffc107"}.get(p, "#28a745")
    date = str(row.get("created_at", row.get("date", "")))[:10]
    st.markdown(
        f"""
        <div style="border-left:4px solid {border};padding:1rem;
            margin-bottom:.7rem;background:#f8f9fa;border-radius:0 8px 8px 0;">
            <strong>{icon} {row['title']}</strong>
            <span style="float:right;color:#666;font-size:.85rem;">{date}</span>
            <br><span style="color:#444;">{row['content']}</span>
            <br><span style="font-size:.8rem;color:#999;">By: {row.get('author','')}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════
def page_dashboard(wp_df, partners_df):
    st.title("🧬 OncoConnect Co-Creation Hub")
    st.caption("Erasmus+ KA210 — Structured peer mentorship for cancer patients")

    render_countdown()

    approvals = db_get_approvals()
    fb_count = len(db_get_partner_feedback())
    approved_n = sum(1 for v in approvals.values() if v)
    remaining_days = (SUBMISSION_DEADLINE - datetime.now()).days

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        card_html("Work Packages", len(wp_df), "#4A90D9")
    with c2:
        card_html("Partners", len(partners_df), "#50C878")
    with c3:
        card_html("Feedback", fb_count, "#F5A623")
    with c4:
        card_html("Approvals", f"{approved_n}/3", "#28a745" if approved_n == 3 else "#ffc107")
    with c5:
        card_html("Days Left", remaining_days, "#dc3545" if remaining_days < 90 else "#17a2b8")

    # Approval mini
    st.subheader("🗳️ Partner Approval Status")
    ac1, ac2, ac3 = st.columns(3)
    for col, cname in zip([ac1, ac2, ac3], ["Turkey", "Poland", "Spain"]):
        ok = approvals.get(cname, False)
        org = PARTNER_MAP[cname]
        with col:
            if ok:
                st.success(f"{FLAGS[cname]} **{org}**\n\n✅ Approved")
            else:
                st.warning(f"{FLAGS[cname]} **{org}**\n\n⏳ Pending")

    # Charts
    ch1, ch2 = st.columns(2)
    with ch1:
        st.subheader("💰 Budget — €60,000")
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
        fig2 = px.bar(sc, x="status", y="count", color="status",
                       color_discrete_map={"In Progress": "#4A90D9", "Not Started": "#ffc107", "Completed": "#28a745"})
        fig2.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # WP Table
    st.subheader("📋 Work Packages")
    cols = [c for c in ["wp_id", "wp_name", "lead_country", "start_month", "end_month", "status", "budget_eur"] if c in wp_df.columns]
    st.dataframe(wp_df[cols], use_container_width=True, hide_index=True)

    # Announcements
    st.subheader("📢 Latest Announcements")
    anns = db_get_announcements()[:3]
    for a in anns:
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
            st.write("**Deliverables:**")
            for d in str(wp["deliverables"]).split(";"):
                st.write(f"  - {d.strip()}")
    with c2:
        s = wp["status"]
        if s == "In Progress":
            st.info(f"🔄 {s}")
        elif s == "Completed":
            st.success(f"✅ {s}")
        else:
            st.warning(f"⏳ {s}")
        if "budget_eur" in wp.index:
            st.metric("Budget", f"€{wp['budget_eur']:,.0f}")
        st.metric("Duration", f"{wp['end_month'] - wp['start_month']} months")

    st.divider()
    st.dataframe(wp_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
# PAGE: GANTT
# ═══════════════════════════════════════════════════
def page_gantt(wp_df):
    st.title("📊 Gantt Chart — 18 Months")
    g = wp_df.copy()
    g["Start"] = g["start_month"].apply(lambda m: PROJECT_START + timedelta(days=(m - 1) * 30))
    g["Finish"] = g["end_month"].apply(lambda m: PROJECT_START + timedelta(days=m * 30))
    g["Task"] = g["wp_id"] + ": " + g["wp_name"]
    lc = "lead_country" if "lead_country" in g.columns else "lead_partner"

    fig = px.timeline(g, x_start="Start", x_end="Finish", y="Task", color=lc,
                       hover_data=["lead_partner", "status"],
                       color_discrete_map={"Turkey": "#e74c3c", "Poland": "#3498db", "Spain": "#f39c12"})
    fig.update_yaxes(autorange="reversed")
    fig.add_vline(x=datetime.now(), line_dash="dash", line_color="red", annotation_text="Today")
    fig.update_layout(height=450, xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════
# PAGE: PARTNERS
# ═══════════════════════════════════════════════════
def page_partners(partners_df):
    st.title("🤝 OncoConnect Consortium")
    st.markdown("**Patient perspective** (TR & PL) + **Scientific expertise** (ES)")

    for _, p in partners_df.iterrows():
        flag = FLAGS.get(p["country"], "🏳️")
        clr = "#e74c3c" if p["role"] == "Coordinator" else "#3498db"
        st.markdown(
            f"""
            <div style="border:1px solid #e0e0e0;border-radius:12px;padding:1.5rem;
                margin-bottom:1rem;background:white;border-left:5px solid {clr};">
                <h3 style="margin:0 0 .5rem;">{flag} {p['organisation']}</h3>
                <p><strong>Country:</strong> {p['country']} |
                   <strong>Role:</strong> <span style="color:{clr};font-weight:600;">{p['role']}</span> |
                   <strong>Type:</strong> {p.get('type', 'N/A')}</p>
                <p style="color:#555;">{p.get('description', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("🗺️ Partner Locations")
    st.map(pd.DataFrame({"lat": [39.93, 52.23, 41.39], "lon": [32.86, 21.01, 2.17]}), zoom=3)


# ═══════════════════════════════════════════════════
# PAGE: PARTNER FEEDBACK (Supabase)
# ═══════════════════════════════════════════════════
def page_partner_feedback():
    st.title("💬 Partner Feedback")
    r, c = R(), C()

    if r in ("Admin", "Partner"):
        st.subheader("📝 Submit New Feedback")
        with st.form("fb_form", clear_on_submit=True):
            if r == "Partner":
                fb_country = c
                fb_org = UO()
                st.write(f"**Partner:** {FLAGS.get(c, '')} {fb_org}")
            else:
                fb_country = st.selectbox("Country", ["Turkey", "Poland", "Spain"])
                fb_org = PARTNER_MAP.get(fb_country, "")

            section = st.selectbox("Section", [
                "Needs Analysis", "Objectives", "Methodology", "Work Packages",
                "Impact", "Dissemination", "Budget", "Ethics/Data Protection", "Consortium",
            ])
            text = st.text_area("Feedback / Recommendation", height=150)
            priority = st.select_slider("Priority", ["Low", "Medium", "High"], "Medium")
            go = st.form_submit_button("Submit", type="primary", use_container_width=True)

            if go and text.strip():
                db_add_partner_feedback(fb_country, fb_org, section, text, priority, UN())
                st.success("✅ Feedback saved to database!")
                st.rerun()
    else:
        st.info("ℹ️ Only partners and admins can submit feedback.")

    st.divider()
    st.subheader("📋 All Feedback")
    rows = db_get_partner_feedback()
    if rows:
        df = pd.DataFrame(rows)
        display = [c2 for c2 in ["id", "partner_country", "organisation", "section", "feedback", "priority", "status", "submitted_by", "created_at"] if c2 in df.columns]
        sections = sorted(df["section"].unique())
        filt = st.multiselect("Filter by Section", sections)
        if filt:
            df = df[df["section"].isin(filt)]
        st.dataframe(df[display], use_container_width=True, hide_index=True)

        if r == "Admin" and len(df) > 0:
            st.subheader("🔧 Update Status")
            fb_id = st.selectbox("Feedback ID", df["id"].tolist())
            new_status = st.selectbox("New Status", ["Open", "Under Review", "Accepted", "Rejected"])
            resp = st.text_input("Response (optional)")
            if st.button("Update", type="primary"):
                db_update_feedback_status(fb_id, new_status, resp if resp else None)
                st.success("✅ Updated!")
                st.rerun()

        if len(df) > 2:
            st.subheader("📊 Analytics")
            fc1, fc2 = st.columns(2)
            with fc1:
                st.plotly_chart(px.histogram(df, x="section", color="section", title="By Section").update_layout(showlegend=False, height=350), use_container_width=True)
            with fc2:
                st.plotly_chart(px.histogram(df, x="partner_country", color="partner_country", title="By Country").update_layout(showlegend=False, height=350), use_container_width=True)
    else:
        st.info("No feedback yet.")


# ═══════════════════════════════════════════════════
# PAGE: PATIENT FEEDBACK (Supabase)
# ═══════════════════════════════════════════════════
def page_patient_feedback():
    st.title("💚 Patient Feedback")
    st.markdown("> *Your voice matters. OncoConnect is designed **with** patients.*")

    with st.form("pf_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            age = st.selectbox("Age Group", ["18-30", "31-45", "46-60", "60+"])
            pf_country = st.selectbox("Country", ["Turkey", "Poland", "Spain", "Other"])
            cancer = st.selectbox("Cancer Type (optional)", ["Prefer not to say", "Breast", "Lung", "Colorectal", "Prostate", "Lymphoma", "Other"])
        with c2:
            support = st.selectbox("Most Needed Support", [
                "Peer support", "Psychological support", "Reliable information",
                "Treatment sharing", "Community belonging", "Caregiver support",
            ])
            digital = st.select_slider("Digital Comfort", ["Very Low", "Low", "Medium", "High", "Very High"], "Medium")
            language = st.multiselect("Language(s)", ["Turkish", "Polish", "Spanish", "English", "Other"])

        matching = st.text_area("What matters for peer matching?", height=100)
        privacy = st.text_area("Privacy expectations?", height=100)
        extra = st.text_area("Additional comments?", height=80)
        go = st.form_submit_button("Submit", type="primary", use_container_width=True)

        if go:
            db_add_patient_feedback({
                "age_group": age, "country": pf_country, "cancer_type": cancer,
                "support_need": support, "digital_literacy": digital,
                "languages": ", ".join(language), "matching_preference": matching,
                "privacy_expectation": privacy, "additional": extra,
            })
            st.success("✅ Thank you! Your feedback is stored securely.")
            st.balloons()

    if R() == "Admin":
        rows = db_get_patient_feedback()
        if rows:
            st.divider()
            st.subheader("📊 Patient Feedback (Admin)")
            df = pd.DataFrame(rows)
            st.metric("Total Responses", len(df))
            if len(df) >= 2:
                pc1, pc2 = st.columns(2)
                with pc1:
                    st.plotly_chart(px.histogram(df, x="support_need", title="Support Needs"), use_container_width=True)
                with pc2:
                    st.plotly_chart(px.histogram(df, x="country", title="By Country"), use_container_width=True)
            st.dataframe(df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
# PAGE: APPROVAL STATUS (Supabase)
# ═══════════════════════════════════════════════════
def page_approval():
    st.title("🗳️ Proposal Approval Status")
    st.markdown("All **3 partners** must approve before download is enabled. Only **Admin** can download.")

    approvals = db_get_approvals()
    r, c = R(), C()

    cols = st.columns(3)
    for col, cname in zip(cols, ["Turkey", "Poland", "Spain"]):
        ok = approvals.get(cname, False)
        flag = FLAGS[cname]
        org = PARTNER_MAP[cname]
        bg = "#d4edda" if ok else "#fff3cd"
        border = "#28a745" if ok else "#ffc107"

        with col:
            st.markdown(
                f"""
                <div style="border:2px solid {border};border-radius:14px;
                    padding:1.5rem;text-align:center;background:{bg};min-height:200px;">
                    <h2 style="margin:0;">{flag}</h2>
                    <h4 style="margin:.3rem 0;">{org}</h4>
                    <h3>{'✅ APPROVED' if ok else '⏳ PENDING'}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
            can_approve = (r == "Partner" and c == cname and not ok) or (r == "Admin" and not ok)
            if can_approve:
                if st.button(f"✅ Approve as {cname}", key=f"a_{cname}", use_container_width=True, type="primary"):
                    db_set_approval(cname, True, UN(), r)
                    st.rerun()
            if r == "Admin" and ok:
                if st.button(f"↩️ Revoke {cname}", key=f"r_{cname}", use_container_width=True):
                    db_set_approval(cname, False, UN(), r)
                    st.rerun()

    st.divider()
    n = sum(1 for v in approvals.values() if v)
    st.subheader("📥 Final Proposal Download")
    st.progress(n / 3)
    st.write(f"**{n}/3** approved")

    if n == 3:
        st.success("🎉 All partners approved!")
        if r == "Admin":
            try:
                with open("documents/proposal_draft.md", "r", encoding="utf-8") as f:
                    content = f.read()
                dc1, dc2 = st.columns(2)
                with dc1:
                    st.download_button("📄 Download Proposal (MD)", content,
                                       "OncoConnect_Final_Proposal.md", "text/markdown",
                                       use_container_width=True, type="primary")
                with dc2:
                    report = {"project": "OncoConnect", "programme": "Erasmus+ KA210",
                              "status": "Approved", "approvals": approvals,
                              "exported": datetime.now().isoformat()}
                    st.download_button("📊 Approval Report (JSON)",
                                       json.dumps(report, indent=2, ensure_ascii=False),
                                       "Approval_Report.json", "application/json",
                                       use_container_width=True)
            except FileNotFoundError:
                st.error("proposal_draft.md not found.")
        else:
            st.info("ℹ️ Only Admin can download.")
    else:
        waiting = [f"{FLAGS[w]} {w}" for w, v in approvals.items() if not v]
        st.warning(f"⏳ Waiting: **{', '.join(waiting)}**")

    if r == "Admin":
        log = db_get_approval_log()
        if log:
            st.divider()
            st.subheader("📜 Approval Log")
            st.dataframe(pd.DataFrame(log), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════
# PAGE: ANNOUNCEMENTS (Supabase)
# ═══════════════════════════════════════════════════
def page_announcements():
    st.title("📢 Announcements")
    anns = db_get_announcements()
    for a in anns:
        ann_card(a)

    if R() in ("Admin", "Partner"):
        st.divider()
        st.subheader("➕ Post Announcement")
        with st.form("ann_form", clear_on_submit=True):
            title = st.text_input("Title")
            content = st.text_area("Content", height=120)
            priority = st.select_slider("Priority", ["Low", "Medium", "High"], "Medium")
            if st.form_submit_button("Publish", type="primary", use_container_width=True):
                if title.strip() and content.strip():
                    db_add_announcement(title, content, f"{UN()} ({UO()})", priority)
                    st.success("✅ Published!")
                    st.rerun()


# ═══════════════════════════════════════════════════
# PAGE: DOCUMENTS
# ═══════════════════════════════════════════════════
def page_documents():
    st.title("📁 Project Documents")
    t1, t2, t3 = st.tabs(["📄 Proposal", "📎 Resources", "💰 Budget"])

    with t1:
        try:
            with open("documents/proposal_draft.md", "r", encoding="utf-8") as f:
                text = f.read()
            st.markdown(text)
            if R() == "Admin":
                st.divider()
                st.download_button("📥 Download (MD)", text, "proposal_draft.md", "text/markdown", use_container_width=True)
        except FileNotFoundError:
            st.warning("proposal_draft.md not found.")

    with t2:
        st.markdown("""
        **Planned:**
        - 📋 Partner Agreement
        - 📝 Ethics Templates (GDPR + KVKK)
        - 🗓️ Meeting Minutes
        - 📖 Mentor Training Curriculum
        - 🔬 Matching Protocol Docs
        """)

    with t3:
        st.subheader("💰 Budget — €60,000")
        bd = pd.DataFrame({
            "Work Package": ["WP1: Management", "WP2: Needs Analysis", "WP3: Development", "WP4: Pilot", "WP5: Eval & Dissemination"],
            "Budget (€)": [12000, 7000, 15000, 12000, 14000],
            "Pct": ["20%", "11.7%", "25%", "20%", "23.3%"],
            "Lead": ["🇹🇷 KSD", "🇵🇱 Rakiety", "🇪🇸 UB", "🇹🇷 KSD", "🇪🇸 UB"],
        })
        st.dataframe(bd, hide_index=True, use_container_width=True)
        fig = px.bar(bd, x="Work Package", y="Budget (€)", color="Lead", text="Budget (€)")
        fig.update_traces(texttemplate="€%{text:,.0f}", textposition="outside")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════
# PAGE: ADMIN
# ═══════════════════════════════════════════════════
def page_admin():
    st.title("🛡️ Admin Panel")
    if R() != "Admin":
        st.error("🚫 Access denied.")
        return

    t1, t2, t3, t4 = st.tabs(["📊 Overview", "📝 Feedback", "🗳️ Log", "📦 Export"])

    with t1:
        fb = db_get_partner_feedback()
        pf = db_get_patient_feedback()
        anns = db_get_announcements()
        approvals = db_get_approvals()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Partner Feedback", len(fb))
        m2.metric("Patient Feedback", len(pf))
        m3.metric("Announcements", len(anns))
        m4.metric("Approvals", f"{sum(1 for v in approvals.values() if v)}/3")
        st.success("✅ Connected to Supabase")

    with t2:
        st.subheader("Partner Feedback")
        fb = db_get_partner_feedback()
        st.dataframe(pd.DataFrame(fb), use_container_width=True, hide_index=True) if fb else st.info("No data.")

        st.subheader("Patient Feedback")
        pf = db_get_patient_feedback()
        st.dataframe(pd.DataFrame(pf), use_container_width=True, hide_index=True) if pf else st.info("No data.")

    with t3:
        log = db_get_approval_log()
        st.dataframe(pd.DataFrame(log), use_container_width=True, hide_index=True) if log else st.info("No log.")

    with t4:
        export = {
            "project": "OncoConnect", "programme": "Erasmus+ KA210",
            "exported_at": datetime.now().isoformat(),
            "approvals": db_get_approvals(),
            "approval_log": db_get_approval_log(),
            "partner_feedback": db_get_partner_feedback(),
            "patient_feedback": db_get_patient_feedback(),
            "announcements": db_get_announcements(),
        }
        st.download_button("📥 Export All (JSON)",
                           json.dumps(export, indent=2, ensure_ascii=False, default=str),
                           "oncoconnect_export.json", "application/json",
                           use_container_width=True, type="primary")
        st.divider()
        if st.button("🔄 Reset Approvals"):
            for cname in ["Turkey", "Poland", "Spain"]:
                db_set_approval(cname, False, "Admin Reset", "Admin")
            st.success("✅ Reset done.")
            st.rerun()


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════
def main():
    if not render_login():
        return

    wp_df, partners_df = load_static()
    r = R()

    # Sidebar
    st.sidebar.markdown("### 🧬 OncoConnect")
    st.sidebar.caption("Erasmus+ KA210")
    st.sidebar.markdown(f"👤 **{UN()}**")
    st.sidebar.markdown(f"🏷️ {ROLE_BADGES.get(r, r)}")
    if r == "Partner":
        st.sidebar.markdown(f"🌍 {FLAGS.get(C(), '')} {C()}")
        st.sidebar.markdown(f"🏢 {UO()}")
    st.sidebar.divider()

    nav = {
        "Admin": ["Dashboard", "Work Packages", "Gantt Chart", "Partners",
                   "Partner Feedback", "Patient Feedback", "Approval Status",
                   "Announcements", "Documents", "🛡️ Admin Panel"],
        "Partner": ["Dashboard", "Work Packages", "Gantt Chart", "Partners",
                     "Partner Feedback", "Patient Feedback", "Approval Status",
                     "Announcements", "Documents"],
        "Patient": ["Dashboard", "Patient Feedback", "Announcements", "Documents"],
    }

    page = st.sidebar.radio("Navigation", nav.get(r, nav["Patient"]))
    st.sidebar.divider()

    # DB status
    try:
        db_get_approvals()
        st.sidebar.success("🔗 DB: Connected", icon="✅")
    except Exception:
        st.sidebar.error("🔗 DB: Error", icon="❌")

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()

    # Router
    routes = {
        "Dashboard": lambda: page_dashboard(wp_df, partners_df),
        "Work Packages": lambda: page_work_packages(wp_df),
        "Gantt Chart": lambda: page_gantt(wp_df),
        "Partners": lambda: page_partners(partners_df),
        "Partner Feedback": page_partner_feedback,
        "Patient Feedback": page_patient_feedback,
        "Approval Status": page_approval,
        "Announcements": page_announcements,
        "Documents": page_documents,
        "🛡️ Admin Panel": page_admin,
    }
    routes.get(page, lambda: st.error("Page not found"))()


if __name__ == "__main__":
    main()
