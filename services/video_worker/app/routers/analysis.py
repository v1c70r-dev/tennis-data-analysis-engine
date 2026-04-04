#services/video_worker/app/routers/analysis.py
from fastapi import APIRouter, UploadFile, File
from app.services.video_pipeline import process_uploaded_file

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/")
async def analyze_video(file: UploadFile = File(...)):
    result = await process_uploaded_file(file)

    return {
        "success": result["success"],
        "frames_detected": len(result["result"])
    }