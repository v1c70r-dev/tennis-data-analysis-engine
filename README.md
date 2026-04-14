# Tennis Data Analysis Engine


<div align="center">
    <img src="./documentation/tennis-app-front.png" style="width:1000px;">
</div>
<br>

# Project Architecture


<div align="center">
    <img src="./documentation/tennis_app_architecture.png" style="width:700px;">
</div>
<br>

## Video Worker

El núcleo de video worker es el loop frame a frame donde los 3 modelos ML (ResNet50 para keypoints, YOLO para jugadores, YOLO para pelota) corren en paralelo sobre cada frame, con MiniCourt actuando como el puente geométrico que convierte píxeles a metros reales vía homografía.
Los dos puntos de falla más relevantes a tener en cuenta son el claim atómico de Postgres (evita doble procesamiento) y el bloque try/except del worker que hace nack hacia la DLQ en caso de error, lo que protege que un job fallido no quede en loop infinito.

<div align="center">
    <img src="./documentation/video_worker.png" style="width:700px;">
</div>
<br>

## Analytics Worker

El worker consume un mensaje de video.processed, intenta apropiarse del job atómicamente en Postgres (evitando que dos workers procesen lo mismo), verifica que los 4 archivos requeridos existan en MinIO, genera el dashboard JSON y el PDF con PlayerStatsCreateReport, los sube a MinIO, y finalmente actualiza el status a report_ready en Postgres antes de hacer ack. Los dos puntos de falla son el claim y la verificación de archivos — ambos derivan al camino de mark_failed si algo no está listo.

<div align="center">
    <img src="./documentation/analytics_worker.png" style="width:700px;">
</div>
<br>

# API Docs

To check the API Gateway docs just go to `http://localhost:8000/docs`

<div align="center">
    <img src="./documentation/api_docs.png" style="width:1000px;">
</div>
<br>

# Project Structure

```bash
/tennis-data-analysis-engine
│
├── documentation
│   ├── pdfs
│   │   ├── arquitectura_sistema_de_colas.pdf
│   │   └── video_worker_README.pdf
│   ├── api_docs.png
│   ├── arquitectura_sistema_colas.docx
│   ├── general_diagram.png
│   ├── tennis-app-front.png
│   └── video_worker_README.docx
├── infra
│   ├── minio
│   │   └── docker-compose.yml
│   ├── nginx
│   │   ├── docker-compose.yml
│   │   └── nginx.conf
│   ├── postgres
│   │   └── docker-compose.yml
│   ├── rabbitmq
│   │   └── docker-compose.yml
│   └── docker-compose.yml
├── scripts
│   ├── down_infra.ps1
│   ├── init_db.ps1
│   └── up_infra.ps1
├── services
│   ├── analytics_worker
│   │   ├── app
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── create_report.py
│   │   │   ├── db.py
│   │   │   ├── main.py
│   │   │   └── player_stats_analysis.py
│   │   ├── experimentation
│   │   │   ├── data
│   │   │   │   ├── tennis_match_1
│   │   │   │   └── tennis_match_2
│   │   │   └── notebooks
│   │   │       ├── ball_stats_analysis.ipynb
│   │   │       └── player_stats_analysis.ipynb
│   │   ├── .dockerignore
│   │   ├── .env
│   │   ├── .env_example.txt
│   │   ├── .gitignore
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── api_gateway
│   │   ├── app
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   ├── .dockerignore
│   │   ├── .gitignore
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── shared
│   │   ├── __init__.py
│   │   ├── .gitignore
│   │   └── queue_definitions.py
│   ├── video_worker
│   │   ├── app
│   │   │   ├── models
│   │   │   │   ├── __init__.py
│   │   │   │   └── loader.py
│   │   │   ├── services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ball_stats.py
│   │   │   │   ├── court_key_points_detector.py
│   │   │   │   ├── mini_court.py
│   │   │   │   ├── perception.py
│   │   │   │   ├── player_stats.py
│   │   │   │   ├── player_tracker.py
│   │   │   │   ├── storage.py
│   │   │   │   ├── tennis_ball_detector.py
│   │   │   │   ├── video_overlay_stats.py
│   │   │   │   └── video_pipeline.py
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── consumer.py
│   │   ├── db.py
│   │   ├── main.py
│   │   ├── worker.py
│   │   ├── experimentation
│   │   │   ├── best_models
│   │   │   │   ├── best_court_key_points_detection.pth
│   │   │   │   ├── best_tennis_ball_detection.pt
│   │   │   │   └── best_tennis_player_tracking.pt
│   │   │   ├── data
│   │   │   │   ├── tennis_ball_detection_v6i_yolo26
│   │   │   │   ├── tennis_court_key_points
│   │   │   │   ├── tennis_match.jpg
│   │   │   │   └── tennis_match.mp4
│   │   │   ├── detect
│   │   │   ├── notebooks
│   │   │   │   ├── checkpoints
│   │   │   │   ├── 01_tennis_ball_detection_and_players_tracking.ipynb
│   │   │   │   ├── 02_tennis_court_detector.ipynb
│   │   │   │   ├── 03_joint_models.ipynb
│   │   │   │   ├── output.mp4
│   │   │   │   └── yolo26x.pt
│   │   │   ├── papers
│   │   │   │   ├── trackNetModel.pdf
│   │   │   │   └── yolo26.pdf
│   │   │   ├── runs
│   │   │   └── runs_court_detector
│   │   │       └── court_detection.mp4
│   │   ├── models
│   │   │   ├── best_court_key_points_detection.pth
│   │   │   ├── best_tennis_ball_detection.pt
│   │   │   └── best_tennis_player_tracking.pt
│   │   ├── tests
│   │   ├── .dockerignore
│   │   ├── .env
│   │   ├── .env_example.txt
│   │   ├── .gitattributes
│   │   ├── .gitignore
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   └── requirements.txt
│   └── __init__.py
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
└── requirements.txt
```

# Base de datos

* Estructura de la tabla `jobs` dentro de la base de datos `tennis` (Almacena el estado y metadata básica de cada job procesado por video_worker):

| column_name | data_type                     | is_nullable | column_default     | is_primary_key |
|-------------|-------------------------------|-------------|--------------------|----------------|
| id          | uuid                          | NO          |                    | 1              |
| status      | text                          | NO          |                    | 0              |
| input_url   | text                          | YES         |                    | 0              |
| output_url  | text                          | YES         |                    | 0              |
| report_url  | text                          | YES         |                    | 0              |
| created_at  | timestamp without time zone   | NO          | CURRENT_TIMESTAMP  | 0              |
| updated_at  | timestamp without time zone   | NO          | CURRENT_TIMESTAMP  | 0              |

* Cada job puede tener uno de los siguientes estados: `pending`, `processing`, `done`, `failed`
* Puedes acceder a través del contenedor docker `postgres` que corre en el puerto 5432 :

    ```bash
    psql -U postgres -d tennis
    select * from jobs limit 10;
    ```
* A modo de ejemplo:

| id                                   | status       | input_url                                                                 | output_url                                                                | report_url                                                               | created_at                 | updated_at                 |
|--------------------------------------|--------------|---------------------------------------------------------------------------|---------------------------------------------------------------------------|---------------------------------------------------------------------------|----------------------------|----------------------------|
| f5bca4f3-a6b7-46f0-9058-37f5568653ba | report_ready | s3://tennis-data/f5bca4f3-a6b7-46f0-9058-37f5568653ba/raw/tennis_match.mp4 | s3://tennis-data/f5bca4f3-a6b7-46f0-9058-37f5568653ba/processed/result.json | s3://tennis-data/f5bca4f3-a6b7-46f0-9058-37f5568653ba/report/report.pdf | 2026-04-12 19:44:06.812387 | 2026-04-12 19:44:06.812387 |

# Flow and commands for development

## 1. Build up the entire infrastructure (windows powershell)

```bash
# dentro de tennis-data-analysis-engine/
scripts/up_infra.ps1
# una vez levantada la infra, revisar que la bbdd exista, si así fuese, revisar que la tabla exista. si no, la crea
scripts/init_db.ps1
```

Estructura de la tabla `jobs` (Almacena el estado y metadata básica de cada procesamiento de video):

| Columna     | Tipo        | Restricciones        | Descripción                                      |
|------------|------------|---------------------|--------------------------------------------------|
| id         | UUID       | PRIMARY KEY         | Identificador único del job                      |
| status     | TEXT       | NOT NULL            | Estado del job (`pending`, `processing`, `done`, `failed`) |
| created_at | TIMESTAMP  | DEFAULT CURRENT_TIMESTAMP | Fecha de creación del job                        |


### 2. Build up the entire infrastructure for one service only

```bash
# 1. Infra
docker compose -f infra/docker-compose.yml up -d

# 2. Service (container)
docker compose up --build video_worker
```

### 3. Upload an image

Check the API docs in http://localhost:8000/docs

```bash
curl -X POST http://localhost:8000/upload -F "file=@C:\Users\sprou\Documents\tennis-data-analysis-engine\services\video_worker\experimentation\data\tennis_match.mp4"
```
```bash
curl -X POST http://localhost:8000/analysis -F "file=@C:\Users\sprou\Documents\tennis-data-analysis-engine\services\video_worker\experimentation\data\tennis_match.mp4"
```



## Crear entorno virtual
```bash
#Crear entorno virtual
python -m venv venv_tennis_data_analysis
#Activar entorno virtual (windows)
venv_tennis_data_analysis\Scripts\activate 
```

## CUDA, PyTorch y Utralytics

```bash
#Chequeo versión de drivers y toolkit
nvcc --version
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2023 NVIDIA Corporation
Built on Wed_Feb__8_05:53:42_Coordinated_Universal_Time_2023
Cuda compilation tools, release 12.1, V12.1.66
Build cuda_12.1.r12.1/compiler.32415258_0
#Instalar pytorch versión compatible
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
#Instalar ultralytics
pip install ultralytics
# Instalar roboflow para acceder a dataset de detección de pelota de tenis
pip install roboflow
```

## Datasets Tennis (videos + tennis ball track):

* https://universe.roboflow.com/viren-dhanwani/tennis-ball-detection
* Original downloaded video: https://www.youtube.com/watch?v=HjxclvUSQ88
* Tennis court detector: https://github.com/yastrebksv/TennisCourtDetector

## Inspiración

* https://www.youtube.com/watch?v=L23oIHZE14w&t=1s

## Extras:
https://www.kaggle.com/datasets/dissfya/atp-tennis-2000-2023daily-pull
Kafka (end to end): https://www.youtube.com/watch?v=yBc_UVnVhfY
