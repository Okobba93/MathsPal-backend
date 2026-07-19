import os, requests, random, string, json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OCR_KEY = os.getenv("OCR_SPACE_KEY")
S_URL = os.getenv("SUPABASE_URL")
S_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(S_URL, S_KEY)

@app.get("/")
def home(): return {"status": "MathsPal Brain Awake"}

@app.get("/assignments")
async def get_assignments():
    res = supabase.table("assignments").select("*").order("created_at", desc=True).execute()
    return {"status": "success", "data": res.data}

@app.get("/submissions")
async def get_submissions():
    res = supabase.table("submissions").select("*").order("created_at", desc=True).execute()
    return {"status": "success", "data": res.data}

@app.post("/create-assignment")
async def create_assignment(title: str = Form(...), master_key: str = Form(...)):
    short = 'MP-' + ''.join(random.choices(string.digits, k=4))
    data = {"title": title, "master_key": json.loads(master_key), "short_code": short}
    supabase.table("assignments").insert(data).execute()
    return {"status": "success", "short_code": short}

# --- NEW: THE DELETE FUNCTION ---
@app.post("/delete-assignment")
async def delete_assignment(assignment_id: str = Form(...)):
    try:
        # 1. Delete all student submissions for this quiz first
        supabase.table("submissions").delete().eq("assignment_id", assignment_id).execute()
        # 2. Delete the quiz itself
        supabase.table("assignments").delete().eq("id", assignment_id).execute()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/grade")
async def grade(short_code: str = Form(...), student_name: str = Form(...), files: List[UploadFile] = File(...)):
    res = supabase.table("assignments").select("*").eq("short_code", short_code.strip().upper()).execute()
    if not res.data: return {"status": "error", "error": "Invalid Class Code"}
    master_key = res.data[0]['master_key']
    assignment_id = res.data[0]['id']
    all_text = ""
    for file in files:
        content = await file.read()
        f = {'file': ('img.jpg', content, 'image/jpeg')}
        ocr_res = requests.post("https://api.ocr.space/parse/image", data={"apikey": OCR_KEY, "OCREngine": "2"}, files=f, timeout=25).json()
        if ocr_res.get("OCRExitCode") == 1: all_text += " " + ocr_res["ParsedResults"][0]["ParsedText"]
    final_results = []
    correct_count = 0
    for q, ans in master_key.items():
        match = str(ans).strip().lower() in all_text.lower()
        if match: correct_count += 1
        final_results.append({"q": q, "status": "correct" if match else "incorrect"})
    supabase.table("submissions").insert({"assignment_id": assignment_id, "student_name": student_name, "score": correct_count, "results_json": final_results}).execute()
    return {"status": "success", "results": final_results, "score": f"{correct_count}/{len(master_key)}"}
