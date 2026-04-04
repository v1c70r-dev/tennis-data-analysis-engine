import os
import uuid
import json
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import psycopg2
import pika
from minio import Minio
from io import BytesIO

app = FastAPI(title="API Gateway")

# ===============================
# Config
# ===============================
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
POSTGRES_PORT = os.environ["POSTGRES_PORT"]
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

RABBITMQ_URL = os.environ["RABBITMQ_URL"]

S3_ENDPOINT = os.environ["S3_ENDPOINT"].replace("http://", "")
S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
S3_BUCKET = os.environ["S3_BUCKET"]

# ===============================
# MinIO Client
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
# Helpers
# ===============================
def get_db_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )

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
# Models
# ===============================
class JobResponse(BaseModel):
    job_id: str
    status: str

# ===============================
# Endpoints
# ===============================

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())

    contents = await file.read()

    object_name = f"{job_id}/raw/{file.filename}"
    file_url = f"s3://{S3_BUCKET}/{object_name}"

    # ===============================
    # 1. Subir a MinIO
    # ===============================
    minio_client.put_object(
        bucket_name=S3_BUCKET,
        object_name=object_name,
        data=BytesIO(contents),
        length=len(contents),
        content_type=file.content_type,
    )

    # ===============================
    # 2. Guardar en DB
    # ===============================
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO jobs (id, status, input_url)
        VALUES (%s, %s, %s)
        """,
        (job_id, "pending", file_url),
    )

    conn.commit()
    cur.close()
    conn.close()

    # ===============================
    # 3. Publicar evento
    # ===============================
    publish_event(
        queue="video.uploaded",
        message={"job_id": job_id},
    )

    return {
        "job_id": job_id,
        "status": "pending"
    }

@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT status FROM jobs WHERE id = %s",
        (job_id,),
    )

    result = cur.fetchone()

    cur.close()
    conn.close()

    if not result:
        return {"error": "job not found"}

    return {"job_id": job_id, "status": result[0]}