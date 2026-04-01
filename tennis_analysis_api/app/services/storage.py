import io
from minio import Minio
from app.config import settings
from datetime import timedelta

client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

def ensure_bucket():
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)

def upload_file(local_path: str, object_name: str) -> str:
    ensure_bucket()
    client.fput_object(settings.minio_bucket, object_name, local_path)
    return object_name

def get_presigned_url(object_name: str) -> str:
    return client.presigned_get_object(
        settings.minio_bucket,
        object_name,
        expires=timedelta(hours=1),
    )