import os
import psycopg2


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def get_job(job_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT status, input_url FROM jobs WHERE id = %s",
        (job_id,),
    )

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result


def update_job_status(job_id, status, output_url=None):
    conn = get_db_connection()
    cur = conn.cursor()

    if output_url:
        cur.execute(
            """
            UPDATE jobs
            SET status = %s,
                output_url = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (status, output_url, job_id),
        )
    else:
        cur.execute(
            """
            UPDATE jobs
            SET status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (status, job_id),
        )

    conn.commit()
    cur.close()
    conn.close()