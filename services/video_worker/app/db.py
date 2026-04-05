# services/video_worker/app/db.py
import os
import psycopg2

POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]


def get_db_connection():
    # The VideoWorker processes one job at a time (prefetch_count=1),
    # so a single persistent connection is sufficient. For higher concurrency,
    # replace with psycopg2.pool.ThreadedConnectionPool.
    return psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def get_job(job_id: str):
    """Return (status, input_url) or None if not found."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status, input_url FROM jobs WHERE id = %s", (job_id,))
        return cur.fetchone()
    finally:
        conn.close()


def try_claim_job(job_id: str, expected_status: str, next_status: str) -> bool:
    """
    Atomically transition a job from expected_status to next_status.

    Uses UPDATE ... WHERE status = expected_status RETURNING id so that
    concurrent workers competing for the same message can only one succeed.
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


def update_job_status(job_id: str, status: str, output_url: str = None):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if output_url:
            cur.execute(
                "UPDATE jobs SET status = %s, output_url = %s WHERE id = %s",
                (status, output_url, job_id),
            )
        else:
            cur.execute(
                "UPDATE jobs SET status = %s WHERE id = %s",
                (status, job_id),
            )
        conn.commit()
    finally:
        conn.close()