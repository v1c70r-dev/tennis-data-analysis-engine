# services/analytics_worker/app/main.py
import os
import json
import time
from minio import Minio
import pika
from services.shared.queue_definitions import declare_all
from services.analytics_worker.app.player_stats_analysis import PlayerStatsAnalysis
from app.config import settings
from app.db import get_db_connection, try_claim_job
import io
import pandas as pd

# ===============================
# Config
# ===============================
RABBITMQ_URL = os.environ["RABBITMQ_URL"]
S3_BUCKET = os.environ["S3_BUCKET"]

# ===============================
# Minio initialization
# ===============================
minio_client = Minio(
    settings.minio_endpoint.replace("http://", ""),
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


def try_claim_job(job_id: str, expected_status: str, next_status: str) -> bool:
    """
    Atomically transition a job from expected_status to next_status.
    Returns True if this worker claimed the job, False otherwise.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE jobs
            SET status = %s
            WHERE id = %s AND status = %s
            RETURNING id
            """,
            (next_status, job_id, expected_status),
        )
        claimed = cur.fetchone() is not None
        conn.commit()
        return claimed
    finally:
        conn.close()


def finalize_job(job_id: str, report_url: str):
    """Write the final status and report URL in a single UPDATE."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE jobs SET status = %s, report_url = %s WHERE id = %s",
            ("report_ready", report_url, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_failed(job_id: str):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE jobs SET status = 'failed' WHERE id = %s", (job_id,))
        conn.commit()
    finally:
        conn.close()

# ===============================
# Processing logic
# ===============================
def process_analytics(job_id: str, output_url: str):
    print(f"[analytics_worker] Processing job {job_id}")

    claimed = try_claim_job(job_id, expected_status="processed", next_status="generating_report")
    if not claimed:
        print(f"[analytics_worker] Job {job_id} not in 'processed' state => skipping")
        return

    try:
        # 1. Descargar result.json y player_stats.csv desde MinIO
        with open(output_url) as f:
            video_processing_result = json.load(f)

        csv_bytes = minio_client.get_object(
            bucket_name=S3_BUCKET,
            object_name=f"{job_id}/processed/player_stats.csv"
        ).read().decode("utf-8")

        analysis = PlayerStatsAnalysis(
            fps=video_processing_result["video_data"]["fps"],
            df=pd.read_csv(io.StringIO(csv_bytes)),
        )

        # 2. Generar todos los datos del dashboard (summary + figuras Plotly serializadas)
        #    y subirlos como dashboard.json → el frontend los consume directamente
        dashboard_data = analysis.get_dashboard_data(
            expresed_in_time=True,
            flip_view=True,
        )
        dashboard_json = json.dumps(dashboard_data).encode("utf-8")
        minio_client.put_object(
            bucket_name=S3_BUCKET,
            object_name=f"{job_id}/report/dashboard.json",
            data=io.BytesIO(dashboard_json),
            length=len(dashboard_json),
            content_type="application/json",
        )

        # 3. Generar PDF y subirlo a MinIO
        local_pdf = f"/tmp/{job_id}_report.pdf"
        analysis.export_pdf(
            output_path=local_pdf,
            expresed_in_time=True,
            flip_view=True,
        )
        with open(local_pdf, "rb") as f:
            pdf_bytes = f.read()
        minio_client.put_object(
            bucket_name=S3_BUCKET,
            object_name=f"{job_id}/report/report.pdf",
            data=io.BytesIO(pdf_bytes),
            length=len(pdf_bytes),
            content_type="application/pdf",
        )

        report_url = f"s3://{S3_BUCKET}/{job_id}/report/report.pdf"
        finalize_job(job_id, report_url)
        print(f"[analytics_worker] Job {job_id} -> report_ready")

    except Exception as e:
        print(f"[analytics_worker] Job {job_id} failed: {e}")
        mark_failed(job_id)
        raise


# ===============================
# Consumer
# ===============================
def callback(ch, method, properties, body):
    """
    ACK only after successful processing.
    On failure, NACK with requeue=False -> message goes to DLQ.
    """
    message = json.loads(body)
    job_id = message["job_id"]
    output_url = message.get("output_url", "")

    try:
        process_analytics(job_id, output_url)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[analytics_worker] Unhandled error for job {job_id}, sending to DLQ: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consumer():
    print("[analytics_worker] Starting consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    #_declare_queues(channel)
    declare_all(channel)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="video.processed", on_message_callback=callback)
    channel.start_consuming()


# ===============================
# Entry point with reconnect loop
# ===============================
if __name__ == "__main__":
    while True:
        try:
            start_consumer()
        except Exception as e:
            print(f"[analytics_worker] Connection lost, retrying in 5s: {e}")
            time.sleep(5)