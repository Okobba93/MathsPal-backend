import os, requests, random, string, json
from fastapi import FastAPI, UploadFile, File, Form
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

# SECURITY FIX: Allows your website to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from Render Environment Variables
OCR_KEY = os.getenv("OCR_SPACE_KEY")
S_URL = os.getenv("SUPABASE_URL")
S_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(S_URL, S_KEY)

@app.get("/")
def home(): 
    return {"status": "MathsPal Brain Awake"}

# --- NEW: FETCH ALL ASSIGNMENTS FOR THE DASHBOARD ---
@app.get("/assignments")
async def get_assignments():
    try:
        res = supabase.table("assignments").select("*").order("created_at", desc=True).execute()
        return {"status": "success", "data": res.data}
    except Exception as e: 
        return {"status": "error", "error": str(e)}

# --- FETCH ALL SUBMISSIONS FOR THE DASHBOARD ---
@app.get("/submissions")
async def get_submissions():
    try:
        res = supabase.table("submissions").select("*").order("created_at", desc=True).execute()
        return {"status": "success", "data": res.data}
    except Exception as e: 
        return {"status": "error", "error": str(e)}

# --- CREATE A NEW QUIZ AND CODE ---
@app.post("/create-assignment")
async def create_assignment(title: str = Form(...), master_key: str = Form(...)):
    try:
        # Generate random 4-digit code: MP-1234
        short = 'MP-' + ''.join(random.choices(string.digits, k=4))
        # Ensure the answer key is saved as a proper JSON object
        key_data = json.loads(master_key)
        
        data = {"title": title, "master_key": key_data, "short_code": short}
        supabase.table("assignments").insert(data).execute()
        return {"status": "success", "short_code": short}
    except Exception as e: 
        return {"status": "error", "error": str(e)}

# --- GRADE THE HANDWRITTEN WORK ---
@app.post("/grade")
async def grade(short_code: str = Form(...), student_name: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        # Find the quiz using the short code
        res = supabase.table("assignments").select("*").eq("short_code", short_code.strip().upper()).execute()
        if not res.data: 
            return {"status": "error", "error": "Invalid Class Code"}
        
        ma
