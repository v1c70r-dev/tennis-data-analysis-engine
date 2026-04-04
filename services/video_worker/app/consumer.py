#services/video_worker/app/consumer.py
import os
import pika

from app.worker import process_job


def start_consumer(minio_client, publish_event):
    connection = pika.BlockingConnection(
        pika.URLParameters(os.getenv("RABBITMQ_URL"))
    )
    channel = connection.channel()

    channel.queue_declare(queue="video.uploaded", durable=True)

    def callback(ch, method, properties, body):
        process_job(body, minio_client, publish_event)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue="video.uploaded", on_message_callback=callback)

    print("Video worker listening...")
    channel.start_consuming()