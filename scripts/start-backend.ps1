# TruthLens Backend Environment Setup

$ErrorActionPreference = "Stop"

# Use Java 21 for TruthLens
$env:JAVA_HOME = "C:\Program Files\Java\jdk-21"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

# Load persistent TruthLens environment variables
$env:TRUTHLENS_DB_URL = [Environment]::GetEnvironmentVariable("TRUTHLENS_DB_URL", "User")
$env:TRUTHLENS_DB_USERNAME = [Environment]::GetEnvironmentVariable("TRUTHLENS_DB_USERNAME", "User")
$env:TRUTHLENS_DB_PASSWORD = [Environment]::GetEnvironmentVariable("TRUTHLENS_DB_PASSWORD", "User")
$env:TRUTHLENS_JWT_SECRET = [Environment]::GetEnvironmentVariable("TRUTHLENS_JWT_SECRET", "User")
$env:TRUTHLENS_AI_SERVICE_URL = [Environment]::GetEnvironmentVariable("TRUTHLENS_AI_SERVICE_URL", "User")

# Validate required configuration
if (-not $env:TRUTHLENS_DB_URL) {
    throw "TRUTHLENS_DB_URL is not configured."
}

if (-not $env:TRUTHLENS_DB_USERNAME) {
    throw "TRUTHLENS_DB_USERNAME is not configured."
}

if (-not $env:TRUTHLENS_DB_PASSWORD) {
    throw "TRUTHLENS_DB_PASSWORD is not configured."
}

if (-not $env:TRUTHLENS_JWT_SECRET) {
    throw "TRUTHLENS_JWT_SECRET is not configured."
}

# Move to backend directory
Set-Location "$PSScriptRoot\..\backend"

Write-Host "TruthLens Backend environment configured." -ForegroundColor Cyan
Write-Host "Java: $env:JAVA_HOME" -ForegroundColor Green
Write-Host "Backend directory: $PWD" -ForegroundColor Green
Write-Host "Environment variables loaded successfully." -ForegroundColor Green
Write-Host ""
Write-Host "Run the backend manually with:" -ForegroundColor Yellow
Write-Host "mvn spring-boot:run" -ForegroundColor White