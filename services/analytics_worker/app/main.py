# services/analytics_worker/app/main.py
import os
import json
import time
import psycopg2
import pika
from services.shared.queue_definitions import declare_all

# ===============================
# Config
# ===============================
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "tennis")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
S3_BUCKET = os.getenv("S3_BUCKET", "tennis-data")

# ===============================
# DB helpers
# ===============================
def get_db_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
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

    #  Idempotency guard 
    # Only accept jobs in 'processed' state.
    # 'generating_report' handles crash-then-retry: if this worker claimed the
    # job but crashed, the next delivery finds it in 'generating_report' and
    # skips cleanly without duplicating the report.
    claimed = try_claim_job(job_id, expected_status="processed", next_status="generating_report")
    if not claimed:
        print(f"[analytics_worker] Job {job_id} not in 'processed' state => skipping")
        return

    try:
        # TODO: replace with real analytics logic:
        #   1. Download result.json from output_url (MinIO)
        #   2. Compute stats, generate charts
        #   3. Build PDF, upload to MinIO under {job_id}/report/report.pdf
        report_url = f"s3://{S3_BUCKET}/{job_id}/report/report.pdf"
        time.sleep(3)  # placeholder

        # Single DB write: status + report_url atomically.
        # The Frontend learns about completion via polling GET /jobs/:id.
        # No event needs to be published polling reads this directly.
        finalize_job(job_id, report_url)

        print(f"[analytics_worker] Job {job_id} -> report_ready")

    except Exception as e:
        print(f"[analytics_worker] Job {job_id} failed: {e}")
        mark_failed(job_id)
        raise  # re-raise so the consumer sends a NACK -> DLQ


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