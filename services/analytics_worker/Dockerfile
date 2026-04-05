# FROM python:3.11-slim

# WORKDIR /app

# ENV PYTHONUNBUFFERED=1
# ENV PYTHONPATH=/app
# # Dependencias
# COPY requirements.txt .

# RUN pip install --no-cache-dir --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt

# # Código
# COPY app ./app

# # Start
# CMD ["python", "-m", "app.main"]

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
# PYTHONPATH debe incluir la raíz para que 'services.shared' sea visible
ENV PYTHONPATH=/app

# Copiamos requirements usando la ruta desde la raíz (contexto actual)
COPY services/analytics_worker/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiamos la carpeta shared y el código del worker
COPY services/shared ./services/shared
COPY services/analytics_worker ./services/analytics_worker

# CAMBIO CRUCIAL: Nos movemos a la carpeta del worker para que el import 'app.main' funcione
WORKDIR /app/services/analytics_worker

# Ejecutamos desde aquí. Ahora 'app.main' es local a esta carpeta
#CMD ["python", "app.main:app", "--host"]
CMD ["python", "app/main.py"]