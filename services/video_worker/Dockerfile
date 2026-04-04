FROM python:3.11

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# ===============================
# System dependencies (mínimas)
# ===============================
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ===============================
# Instalar dependencias primero (cache)
# ===============================
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instalar primero Torch apuntando al repositorio de CUDA (con gpu)
# RUN pip install --no-cache-dir torch==2.5.1+cu121 \
#     --extra-index-url https://download.pytorch.org/whl/cu121

# ===============================
# Copiar SOLO código necesario
# ===============================
COPY app ./app
COPY models ./models

#NO copiar experimentation

# ===============================
# Start
# ===============================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]