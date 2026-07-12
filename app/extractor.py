import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

EXTRACTION_PROMPT = """You are a resume/JD parser. Extract structured information 
from the text below and return ONLY valid JSON, no preamble, no markdown fences.

Return this exact schema:
{{
  "name": "string or null (null for JDs)",
  "skills": ["list", "of", "technical", "skills"],
  "experience_years": "number (estimate if not explicit, 0 if fresher/entry-level)",
  "education": "string describing degree/field",
  "job_titles": ["list of roles held or role being hired for"],
  "summary": "one sentence summary of profile/role"
}}

TEXT:
{text}
"""

def extract_structured_info(text: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT.format(text=text)}
        ],
        temperature=0.1,
    )
    
    raw_output = response.choices[0].message.content.strip()
    
    # Groq sometimes wraps JSON in markdown fences despite instructions
    raw_output = raw_output.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Raw output: {raw_output}")
        return None


EXPLANATION_PROMPT = """You are an AI recruiting assistant. Given a job description 
and a candidate's profile with match scores, write a concise 2-3 sentence explanation 
of why this candidate received this ranking. Be specific about strengths and gaps. 
Keep it professional and factual — no fluff.

JOB DESCRIPTION SKILLS: {jd_skills}

CANDIDATE: {candidate_name}
Final Score: {final_score}/100
Skill Match: {skill_match}%
Matched Skills: {matched_skills}
Missing Skills: {missing_skills}
Experience: {experience_years} years

Write the explanation now (2-3 sentences only, no preamble):
"""

def generate_explanation(jd_skills: list, score_data: dict) -> str:
    prompt = EXPLANATION_PROMPT.format(
        jd_skills=", ".join(jd_skills),
        candidate_name=score_data["candidate_name"],
        final_score=score_data["final_score"],
        skill_match=score_data["skill_match_pct"],
        matched_skills=", ".join(score_data["matched_skills"][:8]),
        missing_skills=", ".join(score_data["missing_skills"][:5]),
        experience_years=score_data["experience_years"],
    )
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    
    return response.choices[0].message.content.strip()