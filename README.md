# tennis-data-analysis-engine

## Estructura proyecto

```bash
tennis-data-analysis-engine/     <- backend + workers
├── docker-compose.yml            <- orquestador local completo
├── .env.local
├── services/
│   ├── api_gateway/
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   └── app/
│   ├── video_worker/
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   └── app/                 
│   └── analytics_worker/
│       ├── docker-compose.yml
│       ├── Dockerfile
│       └── app/
└── infra/
    ├── docker-compose.yml        <- levanta postgres + rabbitmq + minio juntos
    ├── postgres/
    │   └── docker-compose.yml
    ├── rabbitmq/
    │   └── docker-compose.yml
    └── minio/
        └── docker-compose.yml

tennis-frontend/                  <- repo independiente
├── docker-compose.yml
├── Dockerfile
└── src/
```

## Flujo de desarrollo

```bash
# desarrollar solo el video_worker
cd tennis-data-analysis-engine
docker-compose -f infra/docker-compose.yml up    # levanta solo postgres + rabbitmq + minio
cd services/video_worker
docker-compose up                                 # levanta solo el worker

# levantar todo el sistema backend
cd tennis-data-analysis-engine
docker-compose up

# frontend completamente independiente
cd tennis-frontend
docker-compose up
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
