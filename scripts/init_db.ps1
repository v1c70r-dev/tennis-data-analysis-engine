Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   INIT DATABASE (Postgres)              " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Config
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "tennis"
$DB_USER = "postgres"

# Verificar si la tabla ya existe
$CHECK_TABLE_SQL = @"
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'jobs'
);
"@

# Crear tabla, función y trigger (solo si la tabla no existe)
$CREATE_SQL = @"
CREATE TABLE jobs (
    id                UUID        PRIMARY KEY,
    status            TEXT        NOT NULL,
    input_url         TEXT,
    output_url        TEXT,
    report_url        TEXT,
    created_at        TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT jobs_status_check CHECK (status IN (
        'pending',
        'processing',
        'processed',
        'generating_report',
        'report_ready',
        'failed'
    ))
);

-- Actualiza updated_at automáticamente en cada UPDATE
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS \$\$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
\$\$ LANGUAGE plpgsql;

CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
"@

# ===============================
# Esperar a que Postgres esté listo
# ===============================
Write-Host "`n Esperando a Postgres..." -ForegroundColor Yellow

$maxRetries = 10
$retry = 0
$connected = $false

while (-not $connected -and $retry -lt $maxRetries) {
    try {
        $result = docker exec postgres pg_isready -U $DB_USER 2>&1
        if ($LASTEXITCODE -eq 0) {
            $connected = $true
        } else {
            throw "not ready"
        }
    } catch {
        $retry++
        Write-Host "  Reintentando conexión ($retry/$maxRetries)..." -ForegroundColor DarkYellow
        Start-Sleep -Seconds 3
    }
}

if (-not $connected) {
    Write-Host " No se pudo conectar a Postgres después de $maxRetries intentos" -ForegroundColor Red
    exit 1
}

Write-Host " Postgres está listo" -ForegroundColor Green

# ===============================
# Verificar si tabla existe
# ===============================
Write-Host "`n Verificando tabla 'jobs'..." -ForegroundColor Yellow

$tableExists = docker exec -i postgres psql -U $DB_USER -d $DB_NAME -t -c $CHECK_TABLE_SQL
$tableExists = $tableExists.Trim()

if ($tableExists -eq "t") {
    Write-Host " La tabla 'jobs' ya existe, no se realizaron cambios" -ForegroundColor Green
} else {
    Write-Host " La tabla 'jobs' no existe. Creando..." -ForegroundColor Yellow

    $output = $CREATE_SQL | docker exec -i postgres psql -U $DB_USER -d $DB_NAME 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host " Tabla 'jobs' creada correctamente" -ForegroundColor Green
    } else {
        Write-Host " Error al crear la tabla:" -ForegroundColor Red
        Write-Host $output -ForegroundColor Red
        exit 1
    }
}

# ===============================
# Verificar estructura resultante
# ===============================
Write-Host "`n Estructura de la tabla 'jobs':" -ForegroundColor Yellow

docker exec postgres psql -U $DB_USER -d $DB_NAME -c "\d jobs"

Write-Host "`n Base de datos lista para usar" -ForegroundColor Cyan