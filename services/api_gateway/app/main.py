# services/api_gateway/app/main.py
import os
import uuid
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import psycopg2
import psycopg2.pool
import pika
from minio import Minio
from io import BytesIO
from services.shared.queue_definitions import declare_all

# ===============================
# Config
# ===============================
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

RABBITMQ_URL = os.environ["RABBITMQ_URL"]

S3_ENDPOINT = os.environ["S3_ENDPOINT"].replace("http://", "")
S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
S3_BUCKET = os.environ["S3_BUCKET"]

# ===============================
# Connection pool (PostgreSQL)
# Shared across requests; never open a new connection per-request.
# ===============================
db_pool: psycopg2.pool.ThreadedConnectionPool = None

def get_db_connection():
    return db_pool.getconn()

def release_db_connection(conn):
    db_pool.putconn(conn)

# ===============================
# RabbitMQ — persistent channel
# One connection + channel kept alive for the lifetime of the process.
# Re-created on failure via the helper below.
# ===============================
rabbit_connection = None
rabbit_channel = None

def ensure_rabbit_channel():
    global rabbit_connection, rabbit_channel
    if rabbit_connection is None or rabbit_connection.is_closed:
        rabbit_connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        rabbit_channel = rabbit_connection.channel()
        # Declare queues with Dead Letter Queue support
        #_declare_queues(rabbit_channel)
        declare_all(rabbit_channel)
    return rabbit_channel

def publish_event(queue: str, message: dict):
    """Publish a message. Re-establishes the channel on connection errors."""
    global rabbit_channel
    try:
        channel = ensure_rabbit_channel()
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent message
        )
    except (pika.exceptions.AMQPConnectionError, pika.exceptions.ChannelClosedByBroker):
        rabbit_channel = None
        channel = ensure_rabbit_channel()
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )

# ===============================
# MinIO client
# ===============================
minio_client = Minio(
    S3_ENDPOINT,
    access_key=S3_ACCESS_KEY,
    secret_key=S3_SECRET_KEY,
    secure=False,
)

def ensure_bucket_exists():
    if not minio_client.bucket_exists(S3_BUCKET):
        minio_client.make_bucket(S3_BUCKET)

# ===============================
# Lifespan: init + teardown
# ===============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    ensure_bucket_exists()
    ensure_rabbit_channel()
    print("[api_gateway] Startup complete.")
    yield
    if db_pool:
        db_pool.closeall()
    if rabbit_connection and not rabbit_connection.is_closed:
        rabbit_connection.close()
    print("[api_gateway] Shutdown complete.")

# ===============================
# App
# ===============================
app = FastAPI(title="API Gateway", lifespan=lifespan)

# ===============================
# Endpoints
# ===============================

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    contents = await file.read()

    object_name = f"{job_id}/raw/{file.filename}"
    file_url = f"s3://{S3_BUCKET}/{object_name}"

    # 1. Upload to MinIO
    minio_client.put_object(
        bucket_name=S3_BUCKET,
        object_name=object_name,
        data=BytesIO(contents),
        length=len(contents),
        content_type=file.content_type,
    )

    # 2. Insert job record
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO jobs (id, status, input_url) VALUES (%s, %s, %s)",
            (job_id, "pending", file_url),
        )
        conn.commit()
        cur.close()
    finally:
        release_db_connection(conn)

    # 3. Publish to queue
    publish_event("video.uploaded", {"job_id": job_id})

    return {"job_id": job_id, "status": "pending"}


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, report_url FROM jobs WHERE id = %s",
            (job_id,),
        )
        result = cur.fetchone()
        cur.close()
    finally:
        release_db_connection(conn)

    if not result:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_id,
        "status": result[0],
        "report_url": result[1],  # None until report_ready
    }