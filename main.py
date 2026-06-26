import os
import requests
from fastapi import FastAPI, UploadFile, File, Form
from sympy import simplify
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS so your HTML can talk to this server
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Config from Environment Variables
OCR_SPACE_KEY = os.getenv("OCR_SPACE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_math(teacher_ans, student_ans):
    t, s = str(teacher_ans).strip().lower(), str(student_ans).strip().lower()
    if t == s: return "correct"
    try:
        if simplify(f"{t} - ({s})") == 0: return "correct"
    except: pass
    return "incorrect"

def read_handwriting(image_bytes):
    url = "https://api.ocr.space/parse/image"
    payload = {"apikey": OCR_SPACE_KEY, "language": "eng", "OCREngine": "2"}
    files = {'file': ('image.jpg', image_bytes, 'image/jpeg')}
    response = requests.post(url, data=payload, files=files)
    result = response.json()
    if result.get("OCRExitCode") == 1:
        return result["ParsedResults"][0]["ParsedText"].strip()
    return ""

@app.post("/grade")
async def grade(assignment_id: str = Form(...), student_name: str = Form(...), file: UploadFile = File(...)):
    res = supabase.table("assignments").select("master_key").eq("id", assignment_id).execute()
    master_key = res.data[0]['master_key']
    image_content = await file.read()
    detected_text = read_handwriting(image_content)
    correct_ans = master_key.get("1")
    status = check_math(correct_ans, detected_text)
    
    submission = {
        "assignment_id": assignment_id, "student_name": student_name,
        "score": 1 if status == "correct" else 0,
        "results_json": [{"q": "1", "status": status, "text": detected_text}]
    }
    saved = supabase.table("submissions").insert(submission).execute()
    return {"status": "success", "ai_read": detected_text, "result": status}
