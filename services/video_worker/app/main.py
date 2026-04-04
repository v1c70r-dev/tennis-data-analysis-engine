#service/video_worker/app/main.py
import os
import json
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from minio import Minio
import pika

from app.models.loader import load_all_models
from app.config import settings
from app.consumer import start_consumer
from app.routers.analysis import router as analysis_router


def publish_event(queue: str, message: dict):
    connection = pika.BlockingConnection(
        pika.URLParameters(os.getenv("RABBITMQ_URL"))
    )
    channel = connection.channel()

    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=json.dumps(message),
    )

    connection.close()


minio_client = Minio(
    settings.minio_endpoint.replace("http://", ""),
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.models = load_all_models()
    print("Models loaded.")

    threading.Thread(
        target=start_consumer,
        args=(minio_client, publish_event),
        daemon=True
    ).start()

    yield
    print("Shutting down.")


app = FastAPI(title="Video Worker", lifespan=lifespan)
app.include_router(analysis_router)

@app.get("/health")
def health():
    return {"status": "ok"}