import os, requests
from fastapi import FastAPI, UploadFile, File, Form
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OCR_KEY = os.getenv("OCR_SPACE_KEY")
S_URL = os.getenv("SUPABASE_URL")
S_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(S_URL, S_KEY)

@app.post("/grade")
async def grade(assignment_id: str = Form(...), student_name: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        res = supabase.table("assignments").select("master_key").eq("id", assignment_id.strip()).execute()
        if not res.data: return {"status": "error", "error": "ID not found"}
        master_key = res.data[0]['master_key']
        all_text = ""
        for file in files:
            content = await file.read()
            payload = {"apikey": OCR_KEY, "language": "eng", "OCREngine": "2"}
            f = {'file': ('img.jpg', content, 'image/jpeg')}
            ocr_res = requests.post("https://api.ocr.space/parse/image", data=payload, files=f, timeout=25).json()
            if ocr_res.get("OCRExitCode") == 1:
                all_text += " " + ocr_res["ParsedResults"][0]["ParsedText"]
        final_results = []
        correct_count = 0
        for q, ans in master_key.items():
            match = str(ans).strip().lower() in all_text.lower()
            if match: correct_count += 1
            final_results.append({"q": q, "status": "correct" if match else "incorrect"})
        supabase.table("submissions").insert({"assignment_id": assignment_id, "student_name": student_name, "score": correct_count, "results_json": final_results}).execute()
        return {"status": "success", "results": final_results, "score": f"{correct_count}/{len(master_key)}", "saw": all_text}
    except Exception as e: return {"status": "error", "error": str(e)}

@app.get("/")
def home(): return {"status": "MathsPal Batch Brain Awake"}
