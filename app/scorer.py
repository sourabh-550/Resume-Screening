from dotenv import load_dotenv
load_dotenv()

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def compute_semantic_similarity(text1: str, text2: str) -> float:
    """Cosine similarity between two texts using sentence embeddings."""
    embeddings = model.encode([text1, text2])
    sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(sim)

def compute_skill_overlap(jd_skills: list, resume_skills: list) -> dict:
    """Exact + fuzzy skill match between JD and resume."""
    jd_skills_lower = set(s.lower().strip() for s in jd_skills)
    resume_skills_lower = set(s.lower().strip() for s in resume_skills)
    
    matched = jd_skills_lower.intersection(resume_skills_lower)
    missing = jd_skills_lower - resume_skills_lower
    
    overlap_pct = len(matched) / len(jd_skills_lower) if jd_skills_lower else 0
    
    return {
        "matched_skills": list(matched),
        "missing_skills": list(missing),
        "overlap_percentage": round(overlap_pct * 100, 1)
    }

def compute_final_score(jd_data: dict, resume_data: dict) -> dict:
    """Combine semantic similarity + skill overlap into weighted final score."""
    
    # Semantic similarity on summary/profile text
    jd_text = jd_data.get("summary", "") + " " + " ".join(jd_data.get("skills", []))
    resume_text = resume_data.get("summary", "") + " " + " ".join(resume_data.get("skills", []))
    semantic_score = compute_semantic_similarity(jd_text, resume_text)
    
    # Skill overlap
    skill_result = compute_skill_overlap(jd_data.get("skills", []), resume_data.get("skills", []))
    skill_score = skill_result["overlap_percentage"] / 100
    
    # Experience score (simple: does it meet minimum, capped at 1.0)
    jd_exp = float(jd_data.get("experience_years", 0) or 0)
    resume_exp = float(resume_data.get("experience_years", 0) or 0)
    experience_score = min(resume_exp / max(jd_exp, 0.5), 1.0) if jd_exp > 0 else 1.0
    
    # Weighted final score
    final_score = (
        semantic_score * 0.4 +
        skill_score * 0.5 +
        experience_score * 0.1
    )
    
    return {
        "candidate_name": resume_data.get("name"),
        "final_score": round(final_score * 100, 1),
        "semantic_similarity": round(semantic_score * 100, 1),
        "skill_match_pct": skill_result["overlap_percentage"],
        "matched_skills": skill_result["matched_skills"],
        "missing_skills": skill_result["missing_skills"],
        "experience_years": resume_exp,
    }