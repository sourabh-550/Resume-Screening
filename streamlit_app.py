import streamlit as st
import requests
import pandas as pd

BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Smart Resume Screener", layout="wide")
st.title("🎯 Smart Resume Screening & Candidate Ranking")
st.caption("Upload a job description and resumes to get AI-ranked candidates with explanations.")

# --- Sidebar: Uploads ---
with st.sidebar:
    st.header("1. Upload Job Description")
    jd_file = st.file_uploader("Job Description (.txt)", type=["txt"])

    st.header("2. Upload Resumes")
    resume_files = st.file_uploader(
        "Resumes (PDF/DOCX)", type=["pdf", "docx"], accept_multiple_files=True
    )

    run_button = st.button("🚀 Run Screening", type="primary", use_container_width=True)
    reset_button = st.button("🔄 Reset", use_container_width=True)

if reset_button:
    requests.delete(f"{BASE_URL}/reset")
    st.success("Store cleared. Upload fresh files to run again.")
    st.stop()

# --- Main Logic ---
if run_button:
    if not jd_file or not resume_files:
        st.error("Please upload both a JD and at least one resume.")
        st.stop()

    with st.spinner("Uploading and parsing job description..."):
        jd_response = requests.post(
            f"{BASE_URL}/upload-jd", files={"file": (jd_file.name, jd_file.getvalue())}
        )
    if jd_response.status_code != 200:
        st.error(f"JD upload failed: {jd_response.text}")
        st.stop()

    with st.spinner(f"Parsing {len(resume_files)} resume(s)..."):
        files_payload = [
            ("files", (f.name, f.getvalue())) for f in resume_files
        ]
        resume_response = requests.post(f"{BASE_URL}/upload-resumes", files=files_payload)
    if resume_response.status_code != 200:
        st.error(f"Resume upload failed: {resume_response.text}")
        st.stop()

    with st.spinner("Ranking candidates..."):
        rankings_response = requests.get(f"{BASE_URL}/rankings")
    if rankings_response.status_code != 200:
        st.error(f"Ranking failed: {rankings_response.text}")
        st.stop()

    data = rankings_response.json()
    st.success("Screening complete!")

    st.subheader("📋 Job Description Summary")
    st.info(data["jd_summary"])

    st.subheader("🏆 Ranked Candidates")

    for i, r in enumerate(data["rankings"], 1):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### #{i} — {r['candidate_name']}")
                st.caption(f"📄 {r['filename']}")
            with col2:
                st.metric("Final Score", f"{r['final_score']}/100")

            c1, c2, c3 = st.columns(3)
            c1.metric("Semantic Match", f"{r['semantic_similarity']}%")
            c2.metric("Skill Match", f"{r['skill_match_pct']}%")
            c3.metric("Experience", f"{r['experience_years']} yrs")

            st.markdown(f"**✅ Matched Skills:** {', '.join(r['matched_skills']) if r['matched_skills'] else 'None'}")
            st.markdown(f"**❌ Missing Skills:** {', '.join(r['missing_skills']) if r['missing_skills'] else 'None'}")
            st.markdown(f"**🤖 AI Explanation:** {r['explanation']}")

    # Score comparison chart
    st.subheader("📊 Score Comparison")
    df = pd.DataFrame([
        {"Candidate": r["candidate_name"], "Final Score": r["final_score"],
         "Semantic Similarity": r["semantic_similarity"], "Skill Match": r["skill_match_pct"]}
        for r in data["rankings"]
    ])
    st.bar_chart(df.set_index("Candidate")[["Final Score", "Semantic Similarity", "Skill Match"]])

else:
    st.info("👈 Upload a job description and resumes in the sidebar, then click 'Run Screening'.")