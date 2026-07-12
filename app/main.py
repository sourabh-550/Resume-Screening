from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
from typing import List

from .parser import extract_resume_text
from .extractor import extract_structured_info, generate_explanation
from .scorer import compute_final_score

app = FastAPI(title="Smart Resume Screener API")

# Allow frontend (Streamlit) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (MVP — swap for a DB later)
STORE = {
    "jd_data": None,
    "resumes": {}   # filename -> structured data
}

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload-jd")
async def upload_jd(file: UploadFile = File(...)):
    """Accepts a .txt file containing the job description."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="JD must be a .txt file")

    content = (await file.read()).decode("utf-8")
    jd_structured = extract_structured_info(content)

    if jd_structured is None:
        raise HTTPException(status_code=500, detail="Failed to parse JD")

    STORE["jd_data"] = jd_structured
    return {"message": "JD uploaded and parsed successfully", "data": jd_structured}


@app.post("/upload-resumes")
async def upload_resumes(files: List[UploadFile] = File(...)):
    """Accepts multiple PDF/DOCX resumes, parses and extracts structured info."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = {}
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".pdf", ".docx"]:
            continue  # skip unsupported files

        temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        try:
            text = extract_resume_text(temp_path)
            structured = extract_structured_info(text)
            if structured:
                STORE["resumes"][file.filename] = structured
                results[file.filename] = "parsed successfully"
            else:
                results[file.filename] = "failed to parse"
        finally:
            os.remove(temp_path)  # cleanup temp file

    return {"message": "Resumes processed", "results": results}


@app.get("/rankings")
async def get_rankings():
    """Compute and return ranked candidates against the uploaded JD."""
    if STORE["jd_data"] is None:
        raise HTTPException(status_code=400, detail="Upload a JD first")
    if not STORE["resumes"]:
        raise HTTPException(status_code=400, detail="No resumes uploaded yet")

    jd_data = STORE["jd_data"]
    ranked = []

    for filename, resume_data in STORE["resumes"].items():
        score = compute_final_score(jd_data, resume_data)
        explanation = generate_explanation(jd_data["skills"], score)
        score["explanation"] = explanation
        score["filename"] = filename
        ranked.append(score)

    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return {"jd_summary": jd_data.get("summary"), "rankings": ranked}


@app.delete("/reset")
async def reset_store():
    """Clear stored JD and resumes — useful for testing/demo resets."""
    STORE["jd_data"] = None
    STORE["resumes"] = {}
    return {"message": "Store cleared"}


@app.get("/")
async def root():
    return {"status": "Smart Resume Screener API is running"}