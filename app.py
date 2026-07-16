import streamlit as st
import pandas as pd
import io
import json
import time
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
    /* ---- Google Fonts ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ---- Header ---- */
    .main-header {
        font-size: 2.4rem;
        font-weight: 800;
        margin-bottom: 0;
        background: linear-gradient(90deg, #FF4B4B, #FF8C42);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .sub-header {
        color: #9CA3AF;
        font-size: 1rem;
        margin-top: 0.2rem;
        margin-bottom: 1.5rem;
    }

    /* ---- Summary Bar ---- */
    .summary-bar {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.8rem;
        flex-wrap: wrap;
    }
    .metric-card {
        flex: 1;
        min-width: 160px;
        background: linear-gradient(135deg, #1A1D24, #22252E);
        border: 1px solid #2D3139;
        border-radius: 14px;
        padding: 1.1rem 1.4rem;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        border-color: #FF6B35;
    }
    .metric-label {
        color: #9CA3AF;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        color: #FAFAFA;
        font-size: 1.7rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .metric-value-sub {
        color: #FF8C42;
        font-size: 0.82rem;
        font-weight: 500;
        margin-top: 0.2rem;
    }

    /* ---- Candidate Cards ---- */
    .candidate-card {
        background-color: #1A1D24;
        border: 1px solid #2D3139;
        border-radius: 14px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.2s ease;
    }
    .candidate-card:hover {
        border-color: #FF6B35;
        box-shadow: 0 4px 24px rgba(255, 75, 75, 0.12);
        transform: translateY(-2px);
    }
    .rank-badge {
        display: inline-block;
        background: linear-gradient(135deg, #FF4B4B, #FF8C42);
        color: white;
        font-weight: 700;
        font-size: 0.82rem;
        padding: 4px 12px;
        border-radius: 20px;
        margin-bottom: 8px;
        letter-spacing: 0.04em;
    }
    .score-pill {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1.1rem;
    }
    /* WCAG AA compliant contrast ratios */
    .score-high { background-color: #0D2B1F; color: #52F097; border: 1px solid #22543D; }
    .score-mid  { background-color: #2E2510; color: #FCD34D; border: 1px solid #78641A; }
    .score-low  { background-color: #2B0F0F; color: #FC8181; border: 1px solid #742020; }

    /* ---- Skill Tags ---- */
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
    /* WCAG AA contrast: green on dark */
    .skill-tag-match {
        background-color: #0D2B1F;
        color: #52F097;
        border: 1px solid #22543D;
    }
    /* WCAG AA contrast: red on dark */
    .skill-tag-missing {
        background-color: #2B0F0F;
        color: #FC8181;
        border: 1px solid #742020;
    }

    /* ---- Card Sub-metrics ---- */
    .sub-metric-label {
        color: #9CA3AF;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin: 0;
    }
    .sub-metric-value {
        font-size: 1.2rem;
        font-weight: 700;
        margin: 0;
        color: #FAFAFA;
    }

    /* ---- Empty State ---- */
    .empty-state {
        text-align: center;
        padding: 3.5rem 2rem;
        background-color: #1A1D24;
        border-radius: 18px;
        border: 1px dashed #374151;
        margin-top: 2rem;
    }
    .step-grid {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin-top: 2rem;
        flex-wrap: wrap;
    }
    .step-box {
        background: #22252E;
        border: 1px solid #2D3139;
        border-radius: 14px;
        padding: 1.6rem 1.8rem;
        width: 200px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .step-box:hover {
        transform: translateY(-4px);
        border-color: #FF6B35;
    }
    .step-icon {
        font-size: 2.4rem;
        margin-bottom: 0.7rem;
    }
    .step-num {
        display: inline-block;
        background: linear-gradient(135deg, #FF4B4B, #FF8C42);
        color: white;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 9px;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        letter-spacing: 0.05em;
    }
    .step-title {
        color: #FAFAFA;
        font-weight: 700;
        font-size: 1rem;
        margin: 0.4rem 0 0.3rem 0;
    }
    .step-desc {
        color: #9CA3AF;
        font-size: 0.82rem;
        margin: 0;
    }
    .arrow-sep {
        font-size: 1.5rem;
        color: #374151;
        align-self: center;
        margin-top: 1rem;
    }

    /* ---- Loading Steps ---- */
    .loading-step {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        padding: 0.65rem 1rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        font-size: 0.92rem;
        font-weight: 500;
    }
    .loading-step-active {
        background: #22252E;
        color: #FF8C42;
        border: 1px solid #FF6B35;
    }
    .loading-step-done {
        background: #0D2B1F;
        color: #52F097;
        border: 1px solid #22543D;
    }
    .loading-step-pending {
        background: #16181F;
        color: #4B5563;
        border: 1px solid #2D3139;
    }

    /* ---- Controls Bar ---- */
    .controls-label {
        color: #9CA3AF;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }

    /* ---- Divider ---- */
    .section-divider {
        border: none;
        border-top: 1px solid #2D3139;
        margin: 1.5rem 0;
    }

    /* ---- Footer ---- */
    .footer-note {
        text-align: center;
        color: #6B7280;
        font-size: 0.85rem;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #2D3139;
    }

    /* ---- Tooltip helper ---- */
    [title] {
        cursor: help;
    }

    /* ---- Button hover ---- */
    .stButton > button {
        transition: background 0.2s ease, transform 0.15s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)


# ---------- Helper Functions ----------

def score_class(score: float) -> str:
    if score >= 65:
        return "score-high"
    elif score >= 40:
        return "score-mid"
    return "score-low"


def render_skill_tags(skills, tag_type=""):
    css_class = f"skill-tag {tag_type}".strip()
    if not skills:
        return "<span style='color:#6B7280; font-size:0.85rem;'>None</span>"
    return " ".join([f"<span class='{css_class}' title='{s}'>{s}</span>" for s in skills])


def build_radar_chart(candidate: dict):
    """Return a Plotly radar/spider figure for a single candidate."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    categories = ["Semantic Match", "Skill Match", "Experience Fit"]
    exp_fit = min(
        candidate.get("experience_years", 0) / max(float(candidate.get("_jd_exp", 3)), 0.5),
        1.0,
    ) * 100
    values = [
        candidate["semantic_similarity"],
        candidate["skill_match_pct"],
        round(exp_fit, 1),
    ]
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill="toself",
        fillcolor="rgba(255, 107, 53, 0.15)",
        line=dict(color="#FF6B35", width=2),
        name=candidate.get("candidate_name", "Candidate"),
        hovertemplate="%{theta}: <b>%{r:.1f}%</b><extra></extra>",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#1A1D24",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(color="#6B7280", size=9),
                gridcolor="#2D3139",
                linecolor="#2D3139",
            ),
            angularaxis=dict(
                tickfont=dict(color="#D1D5DB", size=10),
                gridcolor="#2D3139",
                linecolor="#2D3139",
            ),
        ),
        paper_bgcolor="#1A1D24",
        plot_bgcolor="#1A1D24",
        font=dict(color="#D1D5DB", family="Inter"),
        showlegend=False,
        margin=dict(l=30, r=30, t=30, b=30),
        height=260,
    )
    return fig


def build_score_bar_chart(results: list):
    """Return a Plotly grouped bar chart comparing all candidates."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    names = [r["candidate_name"] for r in results]
    final = [r["final_score"]         for r in results]
    sem   = [r["semantic_similarity"] for r in results]
    skill = [r["skill_match_pct"]     for r in results]

    fig = go.Figure(data=[
        go.Bar(name="Final Score",         x=names, y=final,  marker_color="#FF4B4B"),
        go.Bar(name="Semantic Similarity", x=names, y=sem,    marker_color="#FF8C42"),
        go.Bar(name="Skill Match",         x=names, y=skill,  marker_color="#FCD34D"),
    ])
    fig.update_layout(
        barmode="group",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font=dict(color="#D1D5DB", family="Inter"),
        legend=dict(
            bgcolor="#1A1D24", bordercolor="#2D3139", borderwidth=1,
            font=dict(size=11),
        ),
        xaxis=dict(gridcolor="#2D3139", tickfont=dict(color="#9CA3AF")),
        yaxis=dict(gridcolor="#2D3139", tickfont=dict(color="#9CA3AF"), range=[0, 105]),
        margin=dict(l=20, r=20, t=20, b=20),
        height=360,
    )
    return fig


def build_csv(results: list) -> bytes:
    rows = []
    for i, r in enumerate(results, 1):
        rows.append({
            "Rank":                i,
            "Candidate":          r["candidate_name"],
            "File":               r["filename"],
            "Final Score":        r["final_score"],
            "Semantic Similarity": r["semantic_similarity"],
            "Skill Match %":      r["skill_match_pct"],
            "Experience (yrs)":   r["experience_years"],
            "Matched Skills":     ", ".join(r["matched_skills"]),
            "Missing Skills":     ", ".join(r["missing_skills"]),
            "AI Insight":         r.get("explanation", ""),
        })
    df = pd.DataFrame(rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def build_summary_text(results: list, jd_summary: str) -> str:
    top3 = results[:3]
    lines = [
        "SMART RESUME SCREENER — TOP CANDIDATES SUMMARY",
        "=" * 52,
        f"Role: {jd_summary}",
        f"Total Candidates Screened: {len(results)}",
        "",
    ]
    for i, r in enumerate(top3, 1):
        lines += [
            f"#{i} {r['candidate_name']}  |  Score: {r['final_score']}/100",
            f"   Semantic: {r['semantic_similarity']}%  |  Skill Match: {r['skill_match_pct']}%  |  Experience: {r['experience_years']} yrs",
            f"   {r.get('explanation', '')}",
            "",
        ]
    lines.append("Generated by Smart Resume Screener — AI-powered candidate ranking")
    return "\n".join(lines)


def update_loading(placeholder, step: int, label: str):
    """
    Renders an animated step-by-step loading indicator.
    step: 0=Parsing JD, 1=Extracting Skills, 2=Computing Scores, 3=Generating Explanations
    """
    steps = [
        ("🔍", "Parsing Job Description"),
        ("⚡", "Extracting Skills & Info"),
        ("📊", "Computing Match Scores"),
        ("🤖", "Generating AI Explanations"),
    ]
    html_parts = ['<div style="max-width:460px; margin:0 auto; padding:1rem;">']
    html_parts.append(
        f'<p style="color:#9CA3AF; font-size:0.82rem; margin-bottom:0.8rem; '
        f'text-transform:uppercase; letter-spacing:0.06em;">⏳ {label}</p>'
    )
    for i, (icon, name) in enumerate(steps):
        if i < step:
            css    = "loading-step loading-step-done"
            prefix = "✅"
        elif i == step:
            css    = "loading-step loading-step-active"
            prefix = icon
        else:
            css    = "loading-step loading-step-pending"
            prefix = "○"
        html_parts.append(
            f'<div class="{css}" role="status" aria-label="{name}">'
            f'<span style="font-size:1.1rem;">{prefix}</span>{name}'
            f'</div>'
        )
    html_parts.append("</div>")
    placeholder.markdown("".join(html_parts), unsafe_allow_html=True)


# ---------- Header ----------
st.markdown('<p class="main-header">🎯 Smart Resume Screener</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">AI-powered candidate ranking with semantic matching, '
    'skill analysis, and explainable scoring</p>',
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### 📋 Setup")
    st.markdown("**Step 1 — Job Description**")
    jd_file = st.file_uploader(
        "Upload JD (.txt)", type=["txt"], label_visibility="collapsed",
        help="Upload a plain-text (.txt) file describing the role and required skills.",
    )

    st.markdown("**Step 2 — Candidate Resumes**")
    resume_files = st.file_uploader(
        "Upload Resumes (PDF/DOCX)", type=["pdf", "docx"],
        accept_multiple_files=True, label_visibility="collapsed",
        help="Upload one or more candidate resumes in PDF or DOCX format.",
    )

    st.markdown("---")
    run_button = st.button("🚀 Run Screening", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("##### ⚙️ How it works")
    st.caption(
        "1. Resumes & JD parsed via LLM extraction\n\n"
        "2. Semantic similarity via sentence embeddings\n\n"
        "3. Hybrid scoring: semantic + skill overlap + experience\n\n"
        "4. AI-generated ranking explanations"
    )

    st.markdown("---")
    st.caption("Built by Sourabh Saxena · [GitHub](https://github.com/sourabh-550)")


# ---------- Main Logic ----------
if run_button:
    if not jd_file or not resume_files:
        st.error("⚠️ Please upload both a job description and at least one resume.")
        st.stop()

    # --- Animated loading sequence ---
    loading_placeholder = st.empty()
    update_loading(loading_placeholder, 0, "Starting…")

    # Step 0: Parse JD
    jd_text = jd_file.getvalue().decode("utf-8")
    jd_data = extract_structured_info(jd_text)

    if jd_data is None:
        loading_placeholder.empty()
        st.error("Failed to parse JD. Please check the file and try again.")
        st.stop()

    update_loading(loading_placeholder, 1, "Parsing complete — extracting skills…")

    # Steps 1-2: Process each resume
    results = []
    n    = len(resume_files)
    prog = st.progress(0)

    for idx, f in enumerate(resume_files):
        update_loading(loading_placeholder, 2, f"Analyzing resume {idx + 1}/{n}: {f.name}")
        prog.progress((idx + 1) / n)

        ext = os.path.splitext(f.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(f.getvalue())
            tmp_path = tmp.name

        try:
            text       = extract_resume_text(tmp_path)
            structured = extract_structured_info(text)
            if structured:
                score              = compute_final_score(jd_data, structured)
                score["filename"]  = f.name
                # Store JD experience for radar chart normalisation (not passed to backend)
                score["_jd_exp"]   = float(jd_data.get("experience_years", 3) or 3)
                results.append(score)
        finally:
            os.remove(tmp_path)

    # Step 3: Explanations
    update_loading(loading_placeholder, 3, "Scores computed — generating AI insights…")
    for r in results:
        r["explanation"] = generate_explanation(jd_data["skills"], r)

    loading_placeholder.empty()
    prog.empty()

    if not results:
        st.error("No resumes could be parsed successfully.")
        st.stop()

    results.sort(key=lambda x: x["final_score"], reverse=True)
    st.success(f"✅ Screening complete — {len(results)} candidate(s) ranked")

    # Store in session state so controls don't re-run the pipeline
    st.session_state["results"]  = results
    st.session_state["jd_data"]  = jd_data


# ---------- Render Results (from session state) ----------
if "results" in st.session_state:
    results = st.session_state["results"]
    jd_data = st.session_state["jd_data"]

    # ---- JD Summary ----
    st.markdown("### 📄 Job Description")
    st.info(jd_data.get("summary", ""))
    req_skills = ", ".join(jd_data.get("skills", []))
    st.caption(f"**Required skills:** {req_skills}")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ---- Summary Metrics Bar ----
    avg_score  = round(sum(r["final_score"] for r in results) / len(results), 1)
    top_cand   = results[0]["candidate_name"] if results else "—"
    high_count = sum(1 for r in results if r["final_score"] >= 65)

    st.markdown(f"""
    <div class="summary-bar" role="region" aria-label="Screening summary metrics">
        <div class="metric-card" title="Total number of resumes processed">
            <div class="metric-label">Candidates Screened</div>
            <div class="metric-value">{len(results)}</div>
        </div>
        <div class="metric-card" title="Average final score across all candidates">
            <div class="metric-label">Average Score</div>
            <div class="metric-value">{avg_score}<span style="font-size:1rem;">/100</span></div>
        </div>
        <div class="metric-card" title="Candidate with the highest final score">
            <div class="metric-label">Top Candidate</div>
            <div class="metric-value" style="font-size:1.25rem; word-break:break-word;">{top_cand}</div>
            <div class="metric-value-sub">Score: {results[0]['final_score']}/100</div>
        </div>
        <div class="metric-card" title="Candidates scoring 65 or above (Strong Match)">
            <div class="metric-label">Strong Matches (&ge;65)</div>
            <div class="metric-value">{high_count}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Filter / Sort Controls ----
    st.markdown("### 🏆 Ranked Candidates")
    ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 2])

    with ctrl1:
        st.markdown('<p class="controls-label">🔍 Search by name</p>', unsafe_allow_html=True)
        search_query = st.text_input(
            "Search candidate", label_visibility="collapsed",
            placeholder="Type a name…", key="search_candidate",
        )

    with ctrl2:
        st.markdown('<p class="controls-label">↕ Sort by</p>', unsafe_allow_html=True)
        sort_by = st.selectbox(
            "Sort by", label_visibility="collapsed",
            options=["Final Score ↓", "Final Score ↑", "Skill Match ↓", "Semantic Similarity ↓"],
            key="sort_by",
        )

    with ctrl3:
        st.markdown('<p class="controls-label">🎯 Min skill match %</p>', unsafe_allow_html=True)
        min_skill = st.slider(
            "Min skill match", 0, 100, 0, 5,
            label_visibility="collapsed", key="min_skill",
            help="Filter out candidates below this skill match percentage.",
        )

    # Apply filters
    filtered = [r for r in results if r["skill_match_pct"] >= min_skill]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered = [r for r in filtered if q in (r["candidate_name"] or "").lower()]

    sort_key_map = {
        "Final Score ↓":          (lambda x: x["final_score"],        True),
        "Final Score ↑":          (lambda x: x["final_score"],        False),
        "Skill Match ↓":          (lambda x: x["skill_match_pct"],    True),
        "Semantic Similarity ↓":  (lambda x: x["semantic_similarity"], True),
    }
    sk, rev = sort_key_map[sort_by]
    filtered.sort(key=sk, reverse=rev)

    if not filtered:
        st.warning("No candidates match the current filters. Try adjusting the search or skill match threshold.")
    else:
        st.caption(f"Showing **{len(filtered)}** of **{len(results)}** candidates")

    # ---- Candidate Cards (collapsible) ----
    for i, r in enumerate(filtered, 1):
        sc_class     = score_class(r["final_score"])
        matched_tags = render_skill_tags(r["matched_skills"], "skill-tag-match")
        missing_tags = render_skill_tags(r["missing_skills"], "skill-tag-missing")

        # Always-visible summary card
        card_html = f"""
        <div class="candidate-card" role="article" aria-label="Candidate {r['candidate_name']} ranked {i}">
            <span class="rank-badge" aria-label="Rank {i}">RANK #{i}</span>
            <div style="display:flex; justify-content:space-between; align-items:center;
                        margin-top:6px; flex-wrap:wrap; gap:0.5rem;">
                <div>
                    <h3 style="margin:0; color:#FAFAFA;">{r['candidate_name']}</h3>
                    <p style="color:#9CA3AF; font-size:0.85rem; margin:2px 0 0 0;"
                       title="Source file and total experience">
                        📄 {r['filename']} &nbsp;|&nbsp; {r['experience_years']} yrs experience
                    </p>
                </div>
                <span class="score-pill {sc_class}"
                      aria-label="Final score {r['final_score']} out of 100"
                      title="Final weighted score (semantic 40%, skill 50%, experience 10%)">
                    {r['final_score']}/100
                </span>
            </div>
            <div style="display:flex; gap:2rem; margin-top:14px; margin-bottom:10px; flex-wrap:wrap;">
                <div title="Cosine similarity between JD and resume sentence embeddings">
                    <p class="sub-metric-label">SEMANTIC MATCH</p>
                    <p class="sub-metric-value">{r['semantic_similarity']}%</p>
                </div>
                <div title="Percentage of required JD skills found in this resume">
                    <p class="sub-metric-label">SKILL MATCH</p>
                    <p class="sub-metric-value">{r['skill_match_pct']}%</p>
                </div>
                <div title="Total years of experience listed in the resume">
                    <p class="sub-metric-label">EXPERIENCE</p>
                    <p class="sub-metric-value">{r['experience_years']} yrs</p>
                </div>
            </div>
            <p style="margin:10px 0 4px 0; font-size:0.82rem; color:#9CA3AF;
                      font-weight:600; letter-spacing:0.05em;">✅ MATCHED SKILLS</p>
            <div role="list" aria-label="Matched skills">{matched_tags}</div>
            <p style="margin:12px 0 4px 0; font-size:0.82rem; color:#9CA3AF;
                      font-weight:600; letter-spacing:0.05em;">❌ MISSING SKILLS</p>
            <div role="list" aria-label="Missing skills">{missing_tags}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # Expandable section: AI insight + radar chart
        with st.expander(f"🔎 View Full Analysis — {r['candidate_name']}", expanded=False):
            exp_col, radar_col = st.columns([3, 2])

            with exp_col:
                st.markdown(
                    f"<p style='font-size:0.92rem; color:#D1D5DB; line-height:1.65;'>"
                    f"🤖 <b>AI Insight:</b> {r.get('explanation', 'Not available.')}</p>",
                    unsafe_allow_html=True,
                )

            with radar_col:
                fig = build_radar_chart(r)
                if fig:
                    st.plotly_chart(
                        fig, use_container_width=True,
                        config={"displayModeBar": False},
                    )
                else:
                    st.caption("Install `plotly` to enable radar charts.")

    # ---- Score Comparison Chart ----
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 📊 Score Comparison")

    chart_data = filtered if filtered else results
    try:
        bar_fig = build_score_bar_chart(chart_data)
        if bar_fig:
            st.plotly_chart(bar_fig, use_container_width=True, config={"displayModeBar": False})
        else:
            raise ImportError
    except Exception:
        # Graceful fallback to Streamlit native chart
        df = pd.DataFrame([
            {
                "Candidate":          r["candidate_name"],
                "Final Score":        r["final_score"],
                "Semantic Similarity": r["semantic_similarity"],
                "Skill Match":        r["skill_match_pct"],
            }
            for r in chart_data
        ])
        st.bar_chart(df.set_index("Candidate")[["Final Score", "Semantic Similarity", "Skill Match"]])

    # ---- Export / Share ----
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 📤 Export & Share")

    dl_col1, dl_col2 = st.columns(2)

    with dl_col1:
        csv_bytes = build_csv(results)
        st.download_button(
            label="⬇️ Download Results as CSV",
            data=csv_bytes,
            file_name="resume_screening_results.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download the full ranked candidate table as a CSV file.",
        )

    with dl_col2:
        summary_text = build_summary_text(results, jd_data.get("summary", ""))
        st.download_button(
            label="📋 Download Top-3 Summary (.txt)",
            data=summary_text.encode("utf-8"),
            file_name="top3_candidate_summary.txt",
            mime="text/plain",
            use_container_width=True,
            help="Download a shareable plain-text summary of the top 3 candidates.",
        )

    with st.expander("📋 View & Copy Top-3 Summary Text", expanded=False):
        st.code(summary_text, language=None)
        st.caption("Select all and copy the text above to share via email or chat.")

else:
    # ---- Rich Empty State ----
    st.markdown("""
    <div class="empty-state" role="main" aria-label="Getting started guide">
        <div style="font-size:3rem; margin-bottom:0.5rem;">🎯</div>
        <h2 style="color:#FAFAFA; margin:0 0 0.5rem 0;">Smart Resume Screener</h2>
        <p style="color:#9CA3AF; max-width:480px; margin:0 auto 0.5rem auto;">
            Upload a <b>Job Description</b> and one or more <b>Candidate Resumes</b>
            in the sidebar, then click <b>Run Screening</b> to get AI-powered
            rankings in seconds.
        </p>
        <div class="step-grid" role="list" aria-label="How it works — 3 steps">
            <div class="step-box" role="listitem">
                <div class="step-icon" aria-hidden="true">📤</div>
                <div class="step-num">STEP 1</div>
                <p class="step-title">Upload</p>
                <p class="step-desc">Add your JD (.txt) and candidate resumes (PDF / DOCX)</p>
            </div>
            <div class="arrow-sep" aria-hidden="true">&#8594;</div>
            <div class="step-box" role="listitem">
                <div class="step-icon" aria-hidden="true">&#9889;</div>
                <div class="step-num">STEP 2</div>
                <p class="step-title">Analyze</p>
                <p class="step-desc">Groq LLM extracts skills; sentence embeddings compute semantic fit</p>
            </div>
            <div class="arrow-sep" aria-hidden="true">&#8594;</div>
            <div class="step-box" role="listitem">
                <div class="step-icon" aria-hidden="true">&#127942;</div>
                <div class="step-num">STEP 3</div>
                <p class="step-title">Rank</p>
                <p class="step-desc">Hybrid scoring ranks every candidate with an AI-written explanation</p>
            </div>
        </div>
        <p style="color:#4B5563; font-size:0.8rem; margin-top:2.2rem;">
            Powered by Groq LLaMA &middot; Sentence Transformers &middot; Streamlit
        </p>
    </div>
    """, unsafe_allow_html=True)


# ---------- Footer ----------
st.markdown(
    '<p class="footer-note">Smart Resume Screener &middot; '
    'Built with Streamlit, Groq LLaMA &amp; Sentence Transformers</p>',
    unsafe_allow_html=True,
)