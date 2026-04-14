param(
    [switch]$RemoveVolumes
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   TENNIS DATA ENGINE - STOP INFRA       " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Verificar Docker
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

# Ir al root del proyecto
$projectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $projectRoot

Write-Host "`n Directorio del proyecto: $projectRoot" -ForegroundColor Yellow

# Construir comando base
$composeCommand = "docker compose -f infra/docker-compose.yml down"

if ($RemoveVolumes) {
    Write-Host "`n Eliminando infraestructura + volúmenes (DATA LOSS)" -ForegroundColor Red
    $composeCommand += " -v"
} else {
    Write-Host "`n Deteniendo infraestructura (manteniendo datos)" -ForegroundColor Yellow
}

# Ejecutar comando
Invoke-Expression $composeCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n Error al detener la infraestructura" -ForegroundColor Red
    exit 1
}

Write-Host "`n Infraestructura detenida correctamente" -ForegroundColor Green

if (-not $RemoveVolumes) {
    Write-Host "`n Tip:"
    Write-Host "   Usa -RemoveVolumes para limpiar completamente (Postgres, MinIO, etc.)"
}