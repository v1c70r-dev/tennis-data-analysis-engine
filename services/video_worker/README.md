# video_worker

FastAPI microservice for tennis match video analysis. Runs a computer vision pipeline (ball detection, player tracking, court keypoints) and stores all artifacts in MinIO.

---

## Request flows

```
POST /analysis
  -> receive uploaded file
  -> run_perception(video_path, job_id=<temp uuid>)
  -> upload artifacts to MinIO under {run_id}/processed/
  -> return full result JSON immediately
```

```
POST /upload  (api_gateway)
  -> MinIO: {job_id}/raw/{filename}
  -> Postgres: status=pending
  -> RabbitMQ: video.uploaded
       |
       v
  video_worker (consumer)
  -> Postgres: status=processing
  -> run_perception(video_path, job_id=job_id)
  -> MinIO: {job_id}/processed/
  -> Postgres: status=done
  -> RabbitMQ: video.done
```

`/analysis` requires only MinIO. No Postgres or RabbitMQ needed.

---

## MinIO output structure

```
{bucket}/
  {job_id}/
    raw/
      {filename}.mp4          <- /upload flow only
    processed/
      video.mp4               <- annotated output video
      result.json             <- full perception result
      ball_raw.csv
      players_raw.csv
      ball_stats.csv
      player_stats.csv
      player_summary.csv
```

---

## Project structure

```
app/
  main.py               # FastAPI app, lifespan, router registration
  config.py             # Settings: MinIO, device, model paths
  consumer.py           # RabbitMQ consumer
  worker.py             # Async job processing logic
  models/
    loader.py           # Load model weights at startup
  services/
    perception.py       # Core pipeline
    storage.py          # MinIO upload helpers
    video_pipeline.py   # Entrypoint for sync and async flows
  routers/
    analysis.py         # POST /analysis
models/                 # Model weight files (.pt / .pth)
docker-compose.yml      # FastAPI + MinIO
.env
```

---

## Setup

```bash
# First time: pull model weights
git lfs install
git lfs pull

# Start
docker-compose up --build -d

# Rebuild after changes
docker-compose down && docker-compose up --build -d

# Local dev
fastapi dev
```

---

## Testing

Swagger UI:
```
http://localhost:8000/docs
```

Linux / macOS:
```bash
curl -X POST http://localhost:8000/analysis/ -F "file=@tennis_match.mp4"
```

Windows PowerShell:
```powershell
curl.exe -X POST http://localhost:8000/analysis/ -F "file=@C:\path\to\tennis_match.mp4"
```

---

## Environment variables

| Variable | Description |
|---|---|
| `MINIO_ENDPOINT` | e.g. `http://minio:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key |
| `MINIO_SECRET_KEY` | MinIO secret key |
| `MINIO_BUCKET` | e.g. `tennis-data` |
| `MINIO_SECURE` | `true` or `false` |
| `RABBITMQ_URL` | AMQP connection URL |
| `DEVICE` | `cpu`, `cuda`, or `0` for GPU index |
| `BALL_MODEL_PATH` | Path to ball detection weights |
| `PLAYERS_MODEL_PATH` | Path to player tracking weights |
| `KPS_MODEL_PATH` | Path to court keypoints weights |
