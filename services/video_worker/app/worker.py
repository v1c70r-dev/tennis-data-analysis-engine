# services/video_worker/app/worker.py
import json
import os
import tempfile

from app.db import get_job, update_job_status, try_claim_job
from app.services.video_pipeline import process_video_file


def parse_s3_url(s3_url: str):
    parts = s3_url.replace("s3://", "").split("/", 1)
    return parts[0], parts[1]


def process_job(body, minio_client, publish_event):
    message = json.loads(body)
    job_id = message["job_id"]

    #  Guard 1: job must exist 
    job = get_job(job_id)
    if not job:
        print(f"[video_worker] Job {job_id} not found => skipping")
        return

    status, file_url = job

    #  Guard 2: only process jobs in 'pending' state 
    # 'processing' is intentionally excluded: if a previous attempt wrote
    # 'processing' and then crashed, we rely on try_claim_job's atomic UPDATE
    # to decide whether this worker should take over or skip.
    if status not in ("pending",):
        print(f"[video_worker] Job {job_id} is '{status}' => skipping")
        return

    #  Optimistic lock: atomic transition pending -> processing 
    # Uses UPDATE ... WHERE status = 'pending' RETURNING id.
    # If two workers receive the same message simultaneously, only one wins.
    claimed = try_claim_job(job_id, expected_status="pending", next_status="processing")
    if not claimed:
        print(f"[video_worker] Job {job_id} already claimed by another worker => skipping")
        return

    bucket, object_name = parse_s3_url(file_url)
    input_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            input_path = tmp.name

        minio_client.fget_object(bucket, object_name, input_path)

        result_data = process_video_file(input_path, job_id=job_id)
        result = result_data["result"]

        # Save result.json under the job's namespace in MinIO
        output_object = f"{job_id}/processed/result.json"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as tmp_out:
            json.dump(result, tmp_out)
            output_path = tmp_out.name

        minio_client.fput_object(bucket, output_object, output_path)
        output_url = f"s3://{bucket}/{output_object}"

        # Write final state to DB before publishing the next event.
        # If publish_event fails after this, the AnalyticsWorker will never
        # pick up the job — but the DB is consistent (status='processed').
        # A reconciliation job can detect and re-publish stale 'processed' jobs.
        update_job_status(job_id, "processed", output_url)
        publish_event("video.processed", {"job_id": job_id, "output_url": output_url})

        print(f"[video_worker] Job {job_id} -> processed")

    except Exception as e:
        print(f"[video_worker] Job {job_id} failed: {e}")
        update_job_status(job_id, "failed")
        raise  # re-raise so the consumer sends a NACK -> DLQ

    finally:
        if input_path and os.path.exists(input_path):
            os.remove(input_path)