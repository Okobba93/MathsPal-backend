import os
import requests
from fastapi import FastAPI, UploadFile, File, Form
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# SECURITY FIX: This allows your phone to talk to the server
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OCR_SPACE_KEY = os.getenv("OCR_SPACE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.post("/grade")
async def grade(assignment_id: str = Form(...), student_name: str = Form(...), file: UploadFile = File(...)):
    print(f"--- SERVER RECEIVED REQUEST FROM {student_name} ---")
    try:
        # 1. Fetch Key from Supabase
        res = supabase.table("assignments").select("master_key").eq("id", assignment_id).execute()
        if not res.data:
            return {"status": "error", "error": "Assignment ID not found"}
        
        master_key = res.data[0]['master_key']
        
        # 2. OCR (Using Engine 1 for speed)
        image_content = await file.read()
        url = "https://api.ocr.space/parse/image"
        payload = {"apikey": OCR_SPACE_KEY, "language": "eng", "OCREngine": "2"}
        files = {'file': ('image.jpg', image_content, 'image/jpeg')}
        
        response = requests.post(url, data=payload, files=files, timeout=15)
        ocr_data = response.json()
        
        detected_text = ""
        if ocr_data.get("OCRExitCode") == 1:
            detected_text = ocr_data["ParsedResults"][0]["ParsedText"].strip()
        
        # 3. Simple Grade (Check if answer is anywhere in the text)
        correct_ans = str(master_key.get("1")).strip()
        status = "correct" if correct_ans in detected_text else "incorrect"
        
        return {"status": "success", "ai_read": detected_text, "result": status}

    except Exception as e:
        print(f"SERVER CRASH: {str(e)}")
        return {"status": "error", "error": str(e)}

@app.get("/")
def home():
    return {"status": "MathsPal Brain is Awake"}
