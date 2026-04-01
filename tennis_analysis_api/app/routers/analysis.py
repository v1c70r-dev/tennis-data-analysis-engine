import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Request
from app.services.perception import read_video, save_video, run_perception, clean_data

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/")
async def analyze_video(request: Request, file: UploadFile = File(...)):
    # Save uploaded video to temp file
    suffix = os.path.splitext(file.filename)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        
        raw_result = run_perception(tmp_path)
        result = clean_data(raw_result)
    finally:
        os.remove(tmp_path)
    return result