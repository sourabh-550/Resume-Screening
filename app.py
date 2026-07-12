import streamlit as st
import pandas as pd
from app.parser import extract_resume_text
from app.extractor import extract_structured_info, generate_explanation
from app.scorer import compute_final_score
import tempfile
import os

st.set_page_config(
    page_title="Smart Resume Screener",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Custom CSS ----------
st.markdown("""
<style>
    .main-header {
        font-size: 2.4rem;
        font-weight: 800;
        margin-bottom: 0;
        background: linear-gradient(90deg, #FF4B4B, #FF8C42);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        color: #9CA3AF;
        font-size: 1rem;
        margin-top: 0.2rem;
        margin-bottom: 1.5rem;
    }
    .candidate-card {
        background-color: #1A1D24;
        border: 1px solid #2D3139;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
    }
    .rank-badge {
        display: inline-block;
        background: linear-gradient(135deg, #FF4B4B, #FF8C42);
        color: white;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 4px 12px;
        border-radius: 20px;
        margin-bottom: 8px;
    }
    .score-pill {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1.1rem;
    }
    .score-high { background-color: #16382A; color: #4ADE80; }
    .score-mid { background-color: #3D3116; color: #FBBF24; }
    .score-low { background-color: #3D1A1A; color: #F87171; }

    .skill-tag {
        display: inline-block;
        background-color: #1F2937;
        color: #D1D5DB;
        padding: 3px 10px;
        border-radius: 14px;
        font-size: 0.78rem;
        margin: 2px;
        border: 1px solid #374151;
    }
    .skill-tag-match {
        background-color: #16382A;
        color: #4ADE80;
        border: 1px solid #22543D;
    }
    .skill-tag-missing {
        background-color: #3D1A1A;
        color: #F87171;
        border: 1px solid #5B2323;
    }
    .footer-note {
        text-align: center;
        color: #6B7280;
        font-size: 0.85rem;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #2D3139;
    }
</style>
""", unsafe_allow_html=True)


def score_class(score):
    if score >= 65:
        return "score-high"
    elif score >= 40:
        return "score-mid"
    return "score-low"


def render_skill_tags(skills, tag_type=""):
    css_class = f"skill-tag {tag_type}".strip()
    if not skills:
        return "<span style='color:#6B7280; font-size:0.85rem;'>None</span>"
    return " ".join([f"<span class='{css_class}'>{s}</span>" for s in skills])


# ---------- Header ----------
st.markdown('<p class="main-header">🎯 Smart Resume Screener</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">AI-powered candidate ranking with semantic matching, skill analysis, and explainable scoring</p>',
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### 📋 Setup")
    st.markdown("**Step 1 — Job Description**")
    jd_file = st.file_uploader("Upload JD (.txt)", type=["txt"], label_visibility="collapsed")

    st.markdown("**Step 2 — Candidate Resumes**")
    resume_files = st.file_uploader(
        "Upload Resumes (PDF/DOCX)", type=["pdf", "docx"],
        accept_multiple_files=True, label_visibility="collapsed"
    )

    st.markdown("---")
    run_button = st.button("🚀 Run Screening", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("##### ⚙️ How it works")
    st.caption("1. Resumes & JD parsed via LLM extraction\n\n2. Semantic similarity via sentence embeddings\n\n3. Hybrid scoring: semantic + skill overlap + experience\n\n4. AI-generated ranking explanations")

    st.markdown("---")
    st.caption("Built by Sourabh Saxena · [GitHub](https://github.com/sourabh-550)")


# ---------- Main Logic ----------
if run_button:
    if not jd_file or not resume_files:
        st.error("⚠️ Please upload both a job description and at least one resume.")
        st.stop()

    with st.spinner("Parsing job description..."):
        jd_text = jd_file.getvalue().decode("utf-8")
        jd_data = extract_structured_info(jd_text)

    if jd_data is None:
        st.error("Failed to parse JD. Please check the file and try again.")
        st.stop()

    results = []
    progress = st.progress(0, text="Starting resume analysis...")
    for idx, f in enumerate(resume_files):
        progress.progress((idx) / len(resume_files), text=f"Analyzing {f.name}...")
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

    progress.progress(1.0, text="Generating AI explanations...")
    for r in results:
        r["explanation"] = generate_explanation(jd_data["skills"], r)
    progress.empty()

    if not results:
        st.error("No resumes could be parsed successfully.")
        st.stop()

    results.sort(key=lambda x: x["final_score"], reverse=True)
    st.success(f"✅ Screening complete — {len(results)} candidate(s) ranked")

    # JD Summary
    st.markdown("### 📄 Job Description")
    st.info(jd_data.get("summary", ""))

    req_skills = ", ".join(jd_data.get("skills", []))
    st.caption(f"**Required skills:** {req_skills}")

    st.markdown("### 🏆 Ranked Candidates")

    for i, r in enumerate(results, 1):
        sc_class = score_class(r["final_score"])
        matched_tags = render_skill_tags(r["matched_skills"], "skill-tag-match")
        missing_tags = render_skill_tags(r["missing_skills"], "skill-tag-missing")

        card_html = f"""
        <div class="candidate-card">
            <span class="rank-badge">RANK #{i}</span>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                <div>
                    <h3 style="margin:0;">{r['candidate_name']}</h3>
                    <p style="color:#9CA3AF; font-size:0.85rem; margin:2px 0 0 0;">📄 {r['filename']} &nbsp;|&nbsp; {r['experience_years']} yrs experience</p>
                </div>
                <span class="score-pill {sc_class}">{r['final_score']}/100</span>
            </div>
            <div style="display:flex; gap:2rem; margin-top:14px; margin-bottom:10px;">
                <div><p style="color:#9CA3AF; font-size:0.78rem; margin:0;">SEMANTIC MATCH</p><p style="font-size:1.2rem; font-weight:700; margin:0;">{r['semantic_similarity']}%</p></div>
                <div><p style="color:#9CA3AF; font-size:0.78rem; margin:0;">SKILL MATCH</p><p style="font-size:1.2rem; font-weight:700; margin:0;">{r['skill_match_pct']}%</p></div>
            </div>
            <p style="margin:10px 0 4px 0; font-size:0.85rem; color:#9CA3AF;">✅ MATCHED SKILLS</p>
            <div>{matched_tags}</div>
            <p style="margin:12px 0 4px 0; font-size:0.85rem; color:#9CA3AF;">❌ MISSING SKILLS</p>
            <div>{missing_tags}</div>
            <p style="margin-top:14px; padding-top:12px; border-top:1px solid #2D3139; font-size:0.9rem; color:#D1D5DB;">
                🤖 <b>AI Insight:</b> {r['explanation']}
            </p>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    # ---------- Chart ----------
    st.markdown("### 📊 Score Comparison")
    df = pd.DataFrame([
        {"Candidate": r["candidate_name"], "Final Score": r["final_score"],
         "Semantic Similarity": r["semantic_similarity"], "Skill Match": r["skill_match_pct"]}
        for r in results
    ])
    st.bar_chart(df.set_index("Candidate")[["Final Score", "Semantic Similarity", "Skill Match"]])

else:
    st.markdown("""
    <div style="text-align:center; padding: 4rem 2rem; background-color:#1A1D24; border-radius:16px; border:1px dashed #374151; margin-top:2rem;">
        <h3>👈 Get started</h3>
        <p style="color:#9CA3AF;">Upload a job description and candidate resumes in the sidebar, then click <b>Run Screening</b> to see AI-ranked results.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown(
    '<p class="footer-note">Smart Resume Screener · Built with FastAPI, Streamlit, Groq LLaMA & Sentence Transformers</p>',
    unsafe_allow_html=True,
)