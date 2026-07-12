import streamlit as st
import pandas as pd
from app.parser import extract_resume_text
from app.extractor import extract_structured_info, generate_explanation
from app.scorer import compute_final_score
import tempfile
import os

st.set_page_config(page_title="Smart Resume Screener", layout="wide")
st.title("🎯 Smart Resume Screening & Candidate Ranking")
st.caption("Upload a job description and resumes to get AI-ranked candidates with explanations.")

with st.sidebar:
    st.header("1. Upload Job Description")
    jd_file = st.file_uploader("Job Description (.txt)", type=["txt"])

    st.header("2. Upload Resumes")
    resume_files = st.file_uploader(
        "Resumes (PDF/DOCX)", type=["pdf", "docx"], accept_multiple_files=True
    )

    run_button = st.button("🚀 Run Screening", type="primary", use_container_width=True)

if run_button:
    if not jd_file or not resume_files:
        st.error("Please upload both a JD and at least one resume.")
        st.stop()

    with st.spinner("Parsing job description..."):
        jd_text = jd_file.getvalue().decode("utf-8")
        jd_data = extract_structured_info(jd_text)

    if jd_data is None:
        st.error("Failed to parse JD. Please check the file and try again.")
        st.stop()

    results = []
    with st.spinner(f"Parsing {len(resume_files)} resume(s)..."):
        for f in resume_files:
            ext = os.path.splitext(f.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(f.getvalue())
                tmp_path = tmp.name

            try:
                text = extract_resume_text(tmp_path)
                structured = extract_structured_info(text)
                if structured:
                    score = compute_final_score(jd_data, structured)
                    score["filename"] = f.name
                    results.append(score)
            finally:
                os.remove(tmp_path)

    if not results:
        st.error("No resumes could be parsed successfully.")
        st.stop()

    with st.spinner("Generating explanations..."):
        for r in results:
            r["explanation"] = generate_explanation(jd_data["skills"], r)

    results.sort(key=lambda x: x["final_score"], reverse=True)
    st.success("Screening complete!")

    st.subheader("📋 Job Description Summary")
    st.info(jd_data.get("summary", ""))

    st.subheader("🏆 Ranked Candidates")
    for i, r in enumerate(results, 1):
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

    st.subheader("📊 Score Comparison")
    df = pd.DataFrame([
        {"Candidate": r["candidate_name"], "Final Score": r["final_score"],
         "Semantic Similarity": r["semantic_similarity"], "Skill Match": r["skill_match_pct"]}
        for r in results
    ])
    st.bar_chart(df.set_index("Candidate")[["Final Score", "Semantic Similarity", "Skill Match"]])
else:
    st.info("👈 Upload a job description and resumes in the sidebar, then click 'Run Screening'.")