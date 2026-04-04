import os
import json
import time
import psycopg2
import pika

# ===============================
# Config
# ===============================
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "tennis")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

# ===============================
# DB
# ===============================
def get_db_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )

# ===============================
# Event publishing
# ===============================
def publish_event(queue: str, message: dict):
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=json.dumps(message),
    )

    connection.close()

# ===============================
# Processing logic
# ===============================
def process_analytics(job_id: str):
    print(f"[analytics_worker] Processing job {job_id}")

    # Simulación de procesamiento
    time.sleep(3)

    report_path = f"s3://tennis-data/{job_id}/report.pdf"

    # Actualizar DB
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE jobs
        SET status = %s
        WHERE id = %s
        """,
        ("done", job_id),
    )

    conn.commit()
    cur.close()
    conn.close()

    # Publicar evento
    publish_event(
        queue="report.done",
        message={
            "job_id": job_id,
            "report_path": report_path,
        },
    )

    print(f"[analytics_worker] Done job {job_id}")

# ===============================
# Consumer
# ===============================
def callback(ch, method, properties, body):
    message = json.loads(body)
    job_id = message["job_id"]

    try:
        process_analytics(job_id)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        # retry automático (RabbitMQ requeue)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def start_consumer():
    print("[analytics_worker] Starting consumer...")

    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()

    channel.queue_declare(queue="video.done", durable=True)
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(queue="video.done", on_message_callback=callback)

    channel.start_consuming()

# ===============================
# Entry point
# ===============================
if __name__ == "__main__":
    # retry loop simple para esperar RabbitMQ
    while True:
        try:
            start_consumer()
        except Exception as e:
            print(f"Retrying connection... {e}")
            time.sleep(5)