Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   INIT DATABASE (Postgres)              " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Config (puedes alinear con .env si quieres)
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "tennis"
$DB_USER = "postgres"

# SQL
$CHECK_TABLE_SQL = @"
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'jobs'
);
"@

$CREATE_TABLE_SQL = @"
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL,
    input_url TEXT,
    output_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"@

# Esperar a que Postgres esté listo
Write-Host "`n Esperando a Postgres..." -ForegroundColor Yellow

$maxRetries = 10
$retry = 0
$connected = $false

while (-not $connected -and $retry -lt $maxRetries) {
    try {
        docker exec postgres pg_isready -U $DB_USER | Out-Null
        $connected = $true
    } catch {
        Start-Sleep -Seconds 3
        $retry++
        Write-Host "Reintentando conexión ($retry/$maxRetries)..."
    }
}

if (-not $connected) {
    Write-Host " No se pudo conectar a Postgres" -ForegroundColor Red
    exit 1
}

Write-Host " Postgres está listo" -ForegroundColor Green

# Verificar si tabla existe
Write-Host "`n Verificando tabla 'jobs'..." -ForegroundColor Yellow

$tableExists = docker exec -i postgres psql -U $DB_USER -d $DB_NAME -t -c $CHECK_TABLE_SQL
$tableExists = $tableExists.Trim()

if ($tableExists -eq "t") {
    Write-Host " La tabla 'jobs' ya existe" -ForegroundColor Green
} else {
    Write-Host " La tabla 'jobs' no existe. Creando..." -ForegroundColor Yellow

    docker exec -i postgres psql -U $DB_USER -d $DB_NAME -c $CREATE_TABLE_SQL | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host " Tabla 'jobs' creada correctamente" -ForegroundColor Green
    } else {
        Write-Host " Error al crear la tabla" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n Base de datos lista para usar" -ForegroundColor Cyan