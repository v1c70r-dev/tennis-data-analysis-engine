#services/analytics_worker/app/main.py
import os
import json
import time
from minio import Minio
import pika
from services.shared.queue_definitions import declare_all
from services.analytics_worker.app.create_report import PlayerStatsCreateReport
from services.analytics_worker.app.config import settings
from services.analytics_worker.app.db import get_db_connection, try_claim_job
import io
import pandas as pd

# ===============================
# Config
# ===============================
RABBITMQ_URL = os.environ["RABBITMQ_URL"]
S3_BUCKET    = os.environ["S3_BUCKET"]

# ===============================
# MinIO
# ===============================
minio_client = Minio(
    settings.minio_endpoint.replace("http://", ""),
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

# ===============================
# DB helpers
# ===============================
def try_claim_job(job_id: str, expected_status: str, next_status: str) -> bool:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE jobs SET status = %s WHERE id = %s AND status = %s RETURNING id",
            (next_status, job_id, expected_status),
        )
        claimed = cur.fetchone() is not None
        conn.commit()
        return claimed
    finally:
        conn.close()


def finalize_job(job_id: str, report_url: str):
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
# Verification
# ===============================
REQUIRED_PROCESSED_FILES = [
    "ball_stats.csv",
    "player_stats.csv",
    "result.json",
    "video.mp4",
]

def verify_processed_files(job_id: str) -> bool:
    for filename in REQUIRED_PROCESSED_FILES:
        try:
            minio_client.stat_object(S3_BUCKET, f"{job_id}/processed/{filename}")
        except Exception:
            print(f"[analytics_worker] Missing file: {job_id}/processed/{filename}")
            return False
    return True


def claim_and_verify(job_id: str) -> bool:
    claimed = try_claim_job(job_id, expected_status="processed", next_status="generating_report")
    if not claimed:
        print(f"[analytics_worker] Job {job_id} not in 'processed' state => skipping")
        return False
    if not verify_processed_files(job_id):
        print(f"[analytics_worker] Job {job_id} missing processed files => failing")
        mark_failed(job_id)
        return False
    return True

# ===============================
# Report generation
# ===============================
def generate_report(job_id: str, fps: float, player_stats_key: str) -> str:
    # 1. Cargar player_stats.csv desde MinIO
    csv_bytes = minio_client.get_object(S3_BUCKET, player_stats_key).read().decode("utf-8")
    df        = pd.read_csv(io.StringIO(csv_bytes))

    # 2. Una sola instancia sirve para Plotly (web) y matplotlib (PDF)
    report = PlayerStatsCreateReport(fps=fps, df=df)

    # 3. Dashboard JSON → Plotly → frontend
    dashboard_data = report.get_dashboard_data(expresed_in_time=True, flip_view=True)
    dashboard_json = json.dumps(dashboard_data).encode("utf-8")
    minio_client.put_object(
        bucket_name=S3_BUCKET,
        object_name=f"{job_id}/report/dashboard.json",
        data=io.BytesIO(dashboard_json),
        length=len(dashboard_json),
        content_type="application/json",
    )

    # 4. PDF → matplotlib → ReportLab
    local_pdf = f"/tmp/{job_id}_report.pdf"
    report.export_pdf(output_path=local_pdf, expresed_in_time=True, flip_view=True)
    with open(local_pdf, "rb") as f:
        pdf_bytes = f.read()
    minio_client.put_object(
        bucket_name=S3_BUCKET,
        object_name=f"{job_id}/report/report.pdf",
        data=io.BytesIO(pdf_bytes),
        length=len(pdf_bytes),
        content_type="application/pdf",
    )

    # 5. Verificar que ambos archivos existen en MinIO
    minio_client.stat_object(S3_BUCKET, f"{job_id}/report/dashboard.json")
    minio_client.stat_object(S3_BUCKET, f"{job_id}/report/report.pdf")

    return f"s3://{S3_BUCKET}/{job_id}/report/report.pdf"

# ===============================
# Orchestrator
# ===============================
def process_analytics(job_id: str, fps: float, player_stats_key: str, results_key: str):
    print(f"[analytics_worker] Processing job {job_id} | fps={fps!r}")

    if not claim_and_verify(job_id):
        return
    try:
        report_url = generate_report(job_id, fps, player_stats_key)
        finalize_job(job_id, report_url)
        print(f"[analytics_worker] Job {job_id} => report_ready")
    except Exception as e:
        print(f"[analytics_worker] Job {job_id} failed: {e}")
        mark_failed(job_id)
        raise

# ===============================
# Consumer
# ===============================
def callback(ch, method, properties, body):
    message          = json.loads(body)
    job_id           = message["job_id"]
    fps              = float(message["fps"])
    player_stats_key = message["player_stats_key"]
    results_key      = message["results_key"]

    try:
        process_analytics(job_id, fps, player_stats_key, results_key)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[analytics_worker] Unhandled error for job {job_id}, sending to DLQ: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consumer():
    print("[analytics_worker] Starting consumer...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel    = connection.channel()
    declare_all(channel)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="video.processed", on_message_callback=callback)
    channel.start_consuming()


# ===============================
# Entry point
# ===============================
if __name__ == "__main__":
    while True:
        try:
            start_consumer()
        except Exception as e:
            print(f"[analytics_worker] Connection lost, retrying in 5s: {e}")
            time.sleep(5)