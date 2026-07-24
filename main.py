import os, requests, random, string, json
from fastapi import FastAPI, UploadFile, File, Form, Header
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

S_URL = os.getenv("SUPABASE_URL")
S_KEY = os.getenv("SUPABASE_KEY")
OCR_KEY = os.getenv("OCR_SPACE_KEY")
supabase: Client = create_client(S_URL, S_KEY)

# HELPER: Get User ID from the secret token
async def get_user_id(auth_header: str):
    try:
        token = auth_header.replace("Bearer ", "")
        user = supabase.auth.get_user(token)
        return user.user.id
    except: return None

@app.get("/assignments")
async def get_assignments(authorization: Optional[str] = Header(None)):
    uid = await get_user_id(authorization)
    if not uid: return {"status": "error", "error": "Unauthorized"}
    # ONLY FETCH QUIZZES OWNED BY THIS TEACHER
    res = supabase.table("assignments").select("*").eq("owner_id", uid).order("created_at", desc=True).execute()
    return {"status": "success", "data": res.data}

@app.get("/submissions")
async def get_submissions(authorization: Optional[str] = Header(None)):
    uid = await get_user_id(authorization)
    if not uid: return {"status": "error", "error": "Unauthorized"}
    # FETCH SUBMISSIONS FOR QUIZZES OWNED BY THIS TEACHER
    my_quizzes = supabase.table("assignments").select("id").eq("owner_id", uid).execute()
    ids = [q['id'] for q in my_quizzes.data]
    res = supabase.table("submissions").select("*").in_("assignment_id", ids).order("created_at", desc=True).execute()
    return {"status": "success", "data": res.data}

@app.post("/create-assignment")
async def create_assignment(title: str = Form(...), master_key: str = Form(...), authorization: Optional[str] = Header(None)):
    uid = await get_user_id(authorization)
    if not uid: return {"status": "error", "error": "Unauthorized"}
    short = 'MP-' + ''.join(random.choices(string.digits, k=4))
    data = {"title": title, "master_key": json.loads(master_key), "short_code": short, "owner_id": uid}
    supabase.table("assignments").insert(data).execute()
    return {"status": "success", "short_code": short}

@app.post("/delete-assignment")
async def delete_assignment(assignment_id: str = Form(...), authorization: Optional[str] = Header(None)):
    uid = await get_user_id(authorization)
    if not uid: return {"status": "error", "error": "Unauthorized"}
    # Ensure they own it before deleting
    check = supabase.table("assignments").select("owner_id").eq("id", assignment_id).execute()
    if check.data and check.data[0]['owner_id'] == uid:
        supabase.table("submissions").delete().eq("assignment_id", assignment_id).execute()
        supabase.table("assignments").delete().eq("id", assignment_id).execute()
        return {"status": "success"}
    return {"status": "error", "error": "Not your assignment"}

@app.post("/grade")
async def grade(short_code: str = Form(...), student_name: str = Form(...), files: List[UploadFile] = File(...)):
    res = supabase.table("assignments").select("*").eq("short_code", short_code.strip().upper()).execute()
    if not res.data: return {"status": "error", "error": "Invalid Code"}
    m_key = res.data[0]['master_key']
    all_text = ""
    for file in files:
        f = {'file': ('img.jpg', await file.read(), 'image/jpeg')}
        ocr = requests.post("https://api.ocr.space/parse/image", data={"apikey": OCR_KEY, "OCREngine": "2"}, files=f, timeout=25).json()
        if ocr.get("OCRExitCode") == 1: all_text += " " + ocr["ParsedResults"][0]["ParsedText"]
    results = []
    correct_count = 0
    for q, ans in m_key.items():
        match = str(ans).strip().lower() in all_text.lower()
        if match: correct_count += 1
        results.append({"q": q, "status": "correct" if match else "incorrect"})
    supabase.table("submissions").insert({"assignment_id": res.data[0]['id'], "student_name": student_name, "score": correct_count, "results_json": results}).execute()
    return {"status": "success", "results": results, "score": f"{correct_count}/{len(m_key)}"}

@app.get("/")
def home(): return {"status": "Isolated Brain Awake"}
