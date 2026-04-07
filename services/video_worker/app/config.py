import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Esto carga el archivo .env manualmente por si Pydantic no lo encuentra
load_dotenv()

class Settings(BaseSettings):
    #device: str
    ball_model_path: str
    players_model_path: str
    kps_model_path: str
    
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = False

    # Configuración para que Pydantic busque el archivo .env
    model_config = SettingsConfigDict(
        env_file=".env",           # Nombre del archivo
        env_file_encoding='utf-8',
        extra='ignore'             # Ignora variables extras que no estén en la clase
    )

# Aquí es donde ocurre la "magia" de la inicialización
settings = Settings()

# Debug rápido: Si esto imprime algo, el .env se leyó bien
print(f"--- CONFIG CARGADA: {settings.ball_model_path} ---")