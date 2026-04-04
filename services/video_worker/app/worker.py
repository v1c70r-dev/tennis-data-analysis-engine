#services/video_worker/app/worker.py
import json
import os
import tempfile

from app.db import get_job, update_job_status
from app.services.video_pipeline import process_video_file


def parse_s3_url(s3_url: str):
    parts = s3_url.replace("s3://", "").split("/", 1)
    return parts[0], parts[1]

def process_job(body, minio_client, publish_event):
    message = json.loads(body)
    job_id = message["job_id"]

    job = get_job(job_id)
    if not job:
        print(f"Job {job_id} no existe -> skip")
        return

    status, file_url = job
    if status != "pending":
        print(f"Job {job_id} status={status} -> skip")
        return

    update_job_status(job_id, "processing")
    bucket, object_name = parse_s3_url(file_url)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        input_path = tmp.name

    try:
        minio_client.fget_object(bucket, object_name, input_path)

        # Pasar job_id al pipeline para que use paths consistentes
        result_data = process_video_file(input_path, job_id=job_id)
        result = result_data["result"]

        # Guardar result.json bajo el job_id original
        output_object = f"{job_id}/processed/result.json"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as tmp_out:
            json.dump(result, tmp_out)
            output_path = tmp_out.name

        minio_client.fput_object(bucket, output_object, output_path)
        output_url = f"s3://{bucket}/{output_object}"

        update_job_status(job_id, "done", output_url)
        publish_event("video.done", {"job_id": job_id, "output_url": output_url})
        print(f"[VIDEO WORKER] Job {job_id} DONE")

    except Exception as e:
        print(f"[VIDEO WORKER] ERROR {job_id}: {e}")
        update_job_status(job_id, "failed")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)