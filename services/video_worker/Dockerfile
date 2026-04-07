#FROM python:3.11
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

WORKDIR /app

ENV PYTHONUNBUFFERED=1
# PYTHONPATH debe incluir la raíz para que 'services.shared' sea visible
ENV PYTHONPATH=/app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3.11 /usr/bin/python
# RUN apt-get update && apt-get install -y \
#     libgl1 \
#     libglib2.0-0 \
#     && rm -rf /var/lib/apt/lists/*

# Copiamos requirements usando la ruta desde la raíz (contexto actual)
COPY services/video_worker/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instalación de PyTorch 2.5.1 compatible con CUDA 12.x
# Usamos el wheel de cu121 ya que es el estándar de compatibilidad para drivers 12.3+
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.5.1 \
    torchvision==0.20.1 \
    torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cu121

# Copiamos la carpeta shared y el código del worker
COPY services/shared ./services/shared
COPY services/video_worker ./services/video_worker

# CAMBIO CRUCIAL: Nos movemos a la carpeta del worker para que el import 'app.main' funcione
WORKDIR /app/services/video_worker

# Ejecutamos desde aquí. Ahora 'app.main' es local a esta carpeta
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]