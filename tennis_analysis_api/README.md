

```bash
tennis-analysis-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app + endpoints
│   ├── config.py                # settings (minio, device, model paths...)
│   │
│   ├── models/                  # model loading logic
│   │   ├── __init__.py
│   │   └── loader.py
│   │
│   ├── services/                # business logic
│   │   ├── __init__.py
│   │   ├── perception.py        # wraps perception_layer
│   │   └── storage.py           # minio upload/download
│   │
│   └── routers/                 # API endpoints
│       ├── __init__.py
│       └── analysis.py
│
├── models/                      # model weights (.pt / .pth files)
│   ├── best_tennis_ball_detection.pt
│   ├── best_tennis_player_tracking.pt
│   └── best_court_key_points_detection.pth
│
├── tests/
│   └── test_analysis.py
│
├── Dockerfile
├── docker-compose.yml           # FastAPI + MinIO together
├── requirements.txt
└── .env                         # secrets / config vars
```

```bash
#reiniciar docker
docker-compose down
docker-compose up --build -d
```

```bash
git lfs install
git lfs pull
docker-compose up --build -d
fast api dev
```

```bash
curl -X POST http://localhost:8000/analysis/ \
  -F "file=@your_video.mp4"

#En mi caso (prueba local)
curl -X POST http://localhost:8000/analysis/ -F "file=@C:\Users\sprou\Documents\tennis-data-analysis-engine\experimentation\data\tennis_match.mp4"
```


```bash
#La estructura en MinIO queda así:
{bucket}/
└── {run_id}/
    ├── video.mp4
    ├── ball_raw.csv        <- ball_df directo del loop
    ├── players_raw.csv     <- players_df directo del loop
    ├── ball_stats.csv      <- ball_df enriquecido con speed_kmh, dist_meters, mx, my
    ├── player_stats.csv    <- players_df enriquecido con speed_kmh, dist_meters, mx, my
    └── player_summary.csv  <- resumen por jugador: avg_speed, max_speed, total_dist
```