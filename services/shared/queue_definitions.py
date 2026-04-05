# shared/queue_definitions.py

QUEUES = {
    "video.uploaded": {
        "durable": True,
        "arguments": {
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "video.uploaded.dead",
        },
    },
    "video.processed": {
        "durable": True,
        "arguments": {
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "video.processed.dead",
        },
    },
    "video.uploaded.dead": {"durable": True},
    "video.processed.dead": {"durable": True},
}


def declare_all(channel):
    """Declara todas las colas. Idempotente, por lo q es seguro llamar múltiples veces."""
    for name, props in QUEUES.items():
        channel.queue_declare(
            queue=name,
            durable=props.get("durable", True),
            arguments=props.get("arguments"),
        )


def declare_queue(channel, name: str):
    """Declara una cola específica por nombre."""
    props = QUEUES[name]
    channel.queue_declare(
        queue=name,
        durable=props.get("durable", True),
        arguments=props.get("arguments"),
    )