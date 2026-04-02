import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Request
from app.services.perception import run_perception

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/")
async def analyze_video(request: Request, file: UploadFile = File(...)):
    # Save uploaded video to temp file
    suffix = os.path.splitext(file.filename)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = run_perception(tmp_path)
        flag = False
        if len(result) == 0:
            flag = False 
        else:
            flag = True
    finally:
        os.remove(tmp_path)
    return flag #success