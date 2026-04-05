# services/video_worker/app/consumer.py
import os
import pika

from app.worker import process_job
from services.shared.queue_definitions import declare_all

# def _declare_queues(channel):
#     """Declare queues with Dead Letter Queue support. Idempotent."""
#     channel.queue_declare(
#         queue="video.uploaded",
#         durable=True,
#         arguments={
#             "x-dead-letter-exchange": "",
#             "x-dead-letter-routing-key": "video.uploaded.dead",
#         },
#     )
#     channel.queue_declare(queue="video.uploaded.dead", durable=True)

#     # Declare downstream queue here so it exists before VideoWorker publishes to it
#     channel.queue_declare(
#         queue="video.processed",
#         durable=True,
#         arguments={
#             "x-dead-letter-exchange": "",
#             "x-dead-letter-routing-key": "video.processed.dead",
#         },
#     )
#     channel.queue_declare(queue="video.processed.dead", durable=True)


# def start_consumer(minio_client, publish_event):
#     connection = pika.BlockingConnection(
#         pika.URLParameters(os.getenv("RABBITMQ_URL")+"?heartbeat=600&blocked_connection_timeout=300") 
#         #AUmenta el tiempo de heartbeat y blocked_connection_timeout para evitar 
#         # desconexiones prematuras durante el procesamiento de trabajos largos (en dev con cpu demora aprox 3 minutos)
#     )
#     channel = connection.channel()
#     declare_all(channel)
#     #_declare_queues(channel)

#     # Process one message at a time — prevents a single worker from
#     # hoarding the queue while processing a long ML job.
#     channel.basic_qos(prefetch_count=1)

#     def callback(ch, method, properties, body):
#         """
#         ACK is only sent after successful processing.
#         On failure, NACK with requeue=False sends the message to the DLQ
#         instead of retrying indefinitely (which would loop on hard errors).
#         """
#         try:
#             process_job(body, minio_client, publish_event)
#             if ch.is_open:
#                 ch.basic_ack(delivery_tag=method.delivery_tag)
#             else:
#                 print("[video_worker] Connection lost during processing. Message will be requeued by RabbitMQ automatically.")
#         except Exception as e:
#             print(f"[video_worker] Unhandled error, sending to DLQ:: {e}")
#             if ch.is_open:
#                 ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

#     channel.basic_consume(queue="video.uploaded", on_message_callback=callback)
#     print("[video_worker] Listening on video.uploaded...")
#     channel.start_consuming()

import threading

def start_consumer(minio_client, publish_event):
    # Heartbeat largo y timeout de conexión bloqueada (5 minutos) para evitar desconexiones prematuras durante el procesamiento de trabajos largos.)
    params = pika.URLParameters(os.getenv("RABBITMQ_URL") + "?heartbeat=300&blocked_connection_timeout=300")
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    declare_all(channel)
    channel.basic_qos(prefetch_count=1)

    def process_and_ack(ch, method, body, minio_client, publish_event):
        try:
            # El trabajo pesado ocurre aquí
            process_job(body, minio_client, publish_event)
            
            # Usamos add_callback_threadsafe para interactuar con el canal desde otro hilo
            ch.connection.add_callback_threadsafe(
                lambda: ch.basic_ack(delivery_tag=method.delivery_tag)
            )
            print(f"[video_worker] Job {method.delivery_tag} exitoso.")
        except Exception as e:
            print(f"[video_worker] Error: {e}")
            ch.connection.add_callback_threadsafe(
                lambda: ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            )

    def callback(ch, method, properties, body):
        # Lanzamos el proceso en un hilo nuevo para no bloquear el latido (heartbeat)
        t = threading.Thread(
            target=process_and_ack, 
            args=(ch, method, body, minio_client, publish_event)
        )
        t.start()

    channel.basic_consume(queue="video.uploaded", on_message_callback=callback)
    channel.start_consuming()