# FROM python:3.11-slim

# WORKDIR /app

# ENV PYTHONUNBUFFERED=1

# # Dependencias
# COPY requirements.txt .

# RUN pip install --no-cache-dir --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt

# # Código
# COPY app .

# # Start
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
# PYTHONPATH debe incluir la raíz para que 'services.shared' sea visible
ENV PYTHONPATH=/app

# Copiamos requirements usando la ruta desde la raíz (contexto actual)
COPY services/api_gateway/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiamos la carpeta shared y el código del worker
COPY services/shared ./services/shared
COPY services/api_gateway ./services/api_gateway

# CAMBIO CRUCIAL: Nos movemos a la carpeta del worker para que el import 'app.main' funcione
WORKDIR /app/services/api_gateway

# Ejecutamos desde aquí. Ahora 'app.main' es local a esta carpeta
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]