# services/video_worker/app/services/video_pipeline.py
import tempfile
import os
from app.services.perception import run_perception
import uuid

def process_video_file(input_path: str, job_id: str) -> dict:
    result = run_perception(input_path, job_id=job_id)
    return {
        "success": len(result.get("ball_data", [])) > 0,
        "result": result,
    }

# Este método se llama desde el endpoint /analysis, que recibe un archivo subido por el usuario. 
# El método genera un job_id temporal para MinIO, procesa el video y luego elimina el archivo temporal.
# Este método síncrono solo se usa a modo de prueba y no se registra en la base de datos Postgres, ya que 
# el flujo principal de procesamiento de videos se maneja a través de MinIO y RabbitMQ.
async def process_uploaded_file(upload_file) -> dict:
    """Flujo síncrono: llamado por /analysis, genera su propio job_id temporal."""
    job_id = str(uuid.uuid4())  # no se registra en Postgres, solo para MinIO
    suffix = os.path.splitext(upload_file.filename)[-1] or ".mp4"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await upload_file.read()
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        return process_video_file(tmp_path, job_id=job_id)
    finally:
        os.remove(tmp_path)