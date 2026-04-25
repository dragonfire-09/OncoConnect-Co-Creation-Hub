import streamlit as st
import pandas as pd
import plotly.express as px 
from datetime import datetime

st.set_page_config(
    page_title="OncoConnect Co-Creation Hub",
    page_icon="🧬",
    layout="wide"
)

# -----------------------------
# Data Loaders
# -----------------------------
@st.cache_data
def load_csv(path):
    return pd.read_csv(path)

wp_df = load_csv("data/work_packages.csv")
partners_df = load_csv("data/partners.csv")
feedback_df = load_csv("data/feedback.csv")
announcements_df = load_csv("data/announcements.csv")

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("🧬 OncoConnect")
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Work Packages",
        "Gantt Chart",
        "Partner Feedback",
        "Patient Feedback",
        "Approval Status",
        "Announcements",
        "Documents"
    ]
)

submission_deadline = datetime(2027, 3, 15)
today = datetime.now()
remaining_days = (submission_deadline - today).days

# -----------------------------
# Dashboard
# -----------------------------
if page == "Dashboard":
    st.title("OncoConnect Co-Creation Hub")
    st.caption("AI-supported proposal development and partner co-creation platform")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Work Packages", len(wp_df))
    col2.metric("Partners", len(partners_df))
    col3.metric("Feedback Records", len(feedback_df))
    col4.metric("Days to Submission", remaining_days)

    st.subheader("Project Status")
    st.info("Current phase: Proposal Draft Development & Partner Feedback Collection")

    st.subheader("Work Package Overview")
    st.dataframe(wp_df, use_container_width=True)

# -----------------------------
# Work Packages
# -----------------------------
elif page == "Work Packages":
    st.title("Work Package Management")
    st.dataframe(wp_df, use_container_width=True)

    selected_wp = st.selectbox("Select a Work Package", wp_df["wp_id"])
    wp = wp_df[wp_df["wp_id"] == selected_wp].iloc[0]

    st.subheader(wp["wp_name"])
    st.write(f"**Lead Partner:** {wp['lead_partner']}")
    st.write(f"**Supporting Partners:** {wp['supporting_partners']}")
    st.write(f"**Duration:** Month {wp['start_month']} – Month {wp['end_month']}")
    st.write(f"**Status:** {wp['status']}")

# -----------------------------
# Gantt Chart
# -----------------------------
elif page == "Gantt Chart":
    st.title("Project Gantt Chart")

    gantt_df = wp_df.copy()
    gantt_df["Start"] = gantt_df["start_month"]
    gantt_df["Finish"] = gantt_df["end_month"]

    fig = px.timeline(
        gantt_df,
        x_start="Start",
        x_end="Finish",
        y="wp_name",
        color="lead_partner",
        hover_data=["wp_id", "status", "supporting_partners"],
        title="OncoConnect Work Package Timeline"
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        xaxis_title="Project Month",
        yaxis_title="Work Packages",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Partner Feedback
# -----------------------------
elif page == "Partner Feedback":
    st.title("Partner Feedback Form")

    with st.form("partner_feedback_form"):
        partner_country = st.selectbox("Partner Country", ["Turkey", "Poland", "Spain", "Other"])
        organisation = st.text_input("Organisation Name")
        section = st.selectbox(
            "Proposal Section",
            ["Needs Analysis", "Objectives", "Methodology", "Work Packages", "Impact", "Dissemination", "Budget", "Ethics/Data Protection"]
        )
        feedback = st.text_area("Feedback / Recommendation")
        submitted = st.form_submit_button("Submit Feedback")

        if submitted:
            st.success("Feedback submitted successfully. Database integration will be added in the next version.")

    st.subheader("Existing Feedback")
    st.dataframe(feedback_df, use_container_width=True)

# -----------------------------
# Patient Feedback
# -----------------------------
elif page == "Patient Feedback":
    st.title("Patient Feedback Collection")

    with st.form("patient_feedback_form"):
        age_group = st.selectbox("Age Group", ["18–30", "31–45", "46–60", "60+"])
        support_need = st.selectbox(
            "Most Needed Support Area",
            ["Peer support", "Psychological support", "Reliable information", "Treatment experience sharing", "Community belonging"]
        )
        matching_preference = st.text_area("What would be important for you in patient-to-patient matching?")
        privacy_expectation = st.text_area("What are your privacy expectations?")
        submitted = st.form_submit_button("Submit Patient Feedback")

        if submitted:
            st.success("Patient feedback submitted successfully. Database integration will be added in the next version.")

# -----------------------------
# Approval Status
# -----------------------------
elif page == "Approval Status":
    st.title("Proposal Approval Status")

    approvals = {
        "Turkey": False,
        "Poland": False,
        "Spain": False
    }

    col1, col2, col3 = st.columns(3)

    col1.metric("Turkey Approval", "Pending" if not approvals["Turkey"] else "Approved")
    col2.metric("Poland Approval", "Pending" if not approvals["Poland"] else "Approved")
    col3.metric("Spain Approval", "Pending" if not approvals["Spain"] else "Approved")

    all_approved = all(approvals.values())

    st.subheader("Final Proposal Download")

    if all_approved:
        st.success("All country partners approved the proposal. Download is now active for admin.")
        st.button("Download Final Proposal")
    else:
        st.warning("Download will be activated only after all three country partners approve the proposal.")

# -----------------------------
# Announcements
# -----------------------------
elif page == "Announcements":
    st.title("Project Announcements & Updates")

    st.dataframe(announcements_df, use_container_width=True)

    st.subheader("Add New Announcement")
    with st.form("announcement_form"):
        title = st.text_input("Announcement Title")
        content = st.text_area("Announcement Content")
        submitted = st.form_submit_button("Publish Announcement")

        if submitted:
            st.success("Announcement created. Database saving will be added in the next version.")

# -----------------------------
# Documents
# -----------------------------
elif page == "Documents":
    st.title("Project Documents")

    st.info("This area will host proposal drafts, partner documents, meeting notes and official templates.")

    try:
        with open("documents/proposal_draft.md", "r", encoding="utf-8") as file:
            proposal_text = file.read()

        st.subheader("Current Proposal Draft")
        st.markdown(proposal_text)

    except FileNotFoundError:
        st.warning("proposal_draft.md not found.")
