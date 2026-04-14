param(
    [switch]$Detach
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   TENNIS DATA ANALYSIS ENGINE - START   " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Verificar que Docker esté corriendo
try {
    docker info | Out-Null
} catch {
    Write-Host " Docker no está corriendo." -ForegroundColor Red
    exit 1
}

# Verificar docker compose
try {
    docker compose version | Out-Null
} catch {
    Write-Host " Docker Compose no está disponible." -ForegroundColor Red
    exit 1
}

# Ir al root del proyecto (por si ejecutan desde scripts/)
$projectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $projectRoot

Write-Host "`n Directorio del proyecto: $projectRoot" -ForegroundColor Yellow

# Build + up
if ($Detach) {
    Write-Host "`n Levantando servicios en background..." -ForegroundColor Green
    docker compose up --build -d
} else {
    Write-Host "`n Levantando servicios..." -ForegroundColor Green
    docker compose up --build
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n Error al levantar los servicios" -ForegroundColor Red
    exit 1
}

Write-Host "`n Servicios levantados correctamente" -ForegroundColor Green

# Mostrar endpoints útiles
Write-Host "`n Endpoints disponibles:" -ForegroundColor Cyan
Write-Host " - API Gateway:  http://localhost:8000"
Write-Host " - RabbitMQ UI:  http://localhost:15672"
Write-Host " - MinIO UI:     http://localhost:9001"
Write-Host " - NGINX:     http://localhost:80"
Write-Host " - Postgres:     localhost:5432"

Write-Host "`n Para ver logs:"
Write-Host "   docker compose logs -f"

Write-Host "`n Para detener:"
Write-Host "   docker compose down"