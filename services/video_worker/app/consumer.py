# services/video_worker/app/consumer.py
import os
import pika

from app.worker import process_job
from services.shared.queue_definitions import declare_all
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