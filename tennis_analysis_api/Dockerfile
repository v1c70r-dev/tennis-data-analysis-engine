FROM python:3.11
WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instalar primero Torch apuntando al repositorio de CUDA (con gpu)

# RUN pip install --no-cache-dir torch==2.5.1+cu121 \
#     --extra-index-url https://download.pytorch.org/whl/cu121

# Luego instalar el resto de dependencias (sin gpu)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]