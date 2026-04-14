# services/video_worker/app/services/video_pipeline.py
from app.services.perception import run_perception

# Este es el método ejecutado cuando se llama al endpoint /upload. Recibe un archivo de video .mp4
# 1. Encola el job en video.upload, 
# 2. Registra el job en postgresql (db tennis, tabla jobs)
# 3. Envía el video en crudo a MinIO (tennis-data/{jobid}/raw/video_subido_sin_procesar.mp4) 
def process_video_file(input_path: str, job_id: str) -> dict:
    result = run_perception(input_path, job_id=job_id)
    return {
        "success": len(result.get("ball_data", [])) > 0,
        "result": result,
    }