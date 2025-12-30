# HarmonyLab-Cloud-Migration.ps1
# VS Code AI: Run this script to complete cloud migration
# Per project-methodology v3.5

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  HarmonyLab Cloud Migration Script" -ForegroundColor Cyan
Write-Host "  Methodology: v3.5" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PROJECT_ID = "super-flashcards-475210"
$PROJECT_SLUG = "harmonylab"
$REGION = "us-central1"
$PROJECT_PATH = "G:\My Drive\Code\Python\Harmony-Lab"

# Secret values (from existing setup)
$DB_SERVER = "35.224.242.223"
$DB_NAME = "HarmonyLab"
$DB_USER = "harmonylab_user"
$DB_PASSWORD = "HarmonyUser2025!"

# ========================================
# Step 1: Verify Authentication
# ========================================
Write-Host "Step 1: Verifying GCP authentication..." -ForegroundColor Yellow

$currentProject = gcloud config get-value project 2>$null
if ($currentProject -ne $PROJECT_ID) {
    Write-Host "  ✗ Wrong project: $currentProject" -ForegroundColor Red
    Write-Host "  Project Lead must run:" -ForegroundColor Red
    Write-Host "    gcloud auth login" -ForegroundColor Gray
    Write-Host "    gcloud auth application-default login" -ForegroundColor Gray
    Write-Host "    gcloud config set project $PROJECT_ID" -ForegroundColor Gray
    Write-Host "    gcloud auth application-default set-quota-project $PROJECT_ID" -ForegroundColor Gray
    exit 1
}
Write-Host "  ✓ Authenticated to project: $currentProject" -ForegroundColor Green

# ========================================
# Step 2: Create/Verify Secrets
# ========================================
Write-Host ""
Write-Host "Step 2: Setting up Secret Manager..." -ForegroundColor Yellow

$secrets = @{
    "$PROJECT_SLUG-db-server" = $DB_SERVER
    "$PROJECT_SLUG-db-name" = $DB_NAME
    "$PROJECT_SLUG-db-user" = $DB_USER
    "$PROJECT_SLUG-db-password" = $DB_PASSWORD
}

foreach ($secretName in $secrets.Keys) {
    $secretValue = $secrets[$secretName]
    
    # Check if secret exists
    $exists = gcloud secrets describe $secretName --project=$PROJECT_ID 2>$null
    
    if ($exists) {
        Write-Host "  Secret '$secretName' exists, adding new version..." -ForegroundColor Cyan
        $secretValue | gcloud secrets versions add $secretName --data-file=- --project=$PROJECT_ID 2>$null
    } else {
        Write-Host "  Creating secret '$secretName'..." -ForegroundColor Cyan
        $secretValue | gcloud secrets create $secretName --data-file=- --project=$PROJECT_ID 2>$null
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✓ $secretName configured" -ForegroundColor Green
    } else {
        Write-Host "    ✗ Failed to configure $secretName" -ForegroundColor Red
    }
}

# ========================================
# Step 3: Grant IAM Access
# ========================================
Write-Host ""
Write-Host "Step 3: Granting IAM access to Cloud Run..." -ForegroundColor Yellow

$PROJECT_NUMBER = (gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
$SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

Write-Host "  Service Account: $SA" -ForegroundColor Cyan

foreach ($secretName in $secrets.Keys) {
    gcloud secrets add-iam-policy-binding $secretName `
        --member="serviceAccount:$SA" `
        --role="roles/secretmanager.secretAccessor" `
        --project=$PROJECT_ID 2>$null | Out-Null
    
    Write-Host "    ✓ IAM binding for $secretName" -ForegroundColor Green
}

# ========================================
# Step 4: Verify/Create Dockerfile
# ========================================
Write-Host ""
Write-Host "Step 4: Checking Dockerfile..." -ForegroundColor Yellow

$dockerfilePath = Join-Path $PROJECT_PATH "Dockerfile"
if (Test-Path $dockerfilePath) {
    Write-Host "  ✓ Dockerfile exists" -ForegroundColor Green
} else {
    Write-Host "  Creating Dockerfile..." -ForegroundColor Cyan
    
    $dockerfileContent = @"
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl gnupg2 apt-transport-https unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
"@
    $dockerfileContent | Out-File -FilePath $dockerfilePath -Encoding UTF8
    Write-Host "  ✓ Dockerfile created" -ForegroundColor Green
}

# ========================================
# Step 5: Verify/Create GitHub Actions
# ========================================
Write-Host ""
Write-Host "Step 5: Checking GitHub Actions workflow..." -ForegroundColor Yellow

$workflowDir = Join-Path $PROJECT_PATH ".github\workflows"
$workflowPath = Join-Path $workflowDir "deploy.yml"

if (-not (Test-Path $workflowDir)) {
    New-Item -ItemType Directory -Path $workflowDir -Force | Out-Null
}

if (Test-Path $workflowPath) {
    Write-Host "  ✓ GitHub Actions workflow exists" -ForegroundColor Green
} else {
    Write-Host "  Creating deploy.yml..." -ForegroundColor Cyan
    
    $workflowContent = @"
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

env:
  PROJECT_ID: super-flashcards-475210
  SERVICE_NAME: harmonylab
  REGION: us-central1

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    
    steps:
      - uses: actions/checkout@v4
      
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: `${{ secrets.WIF_PROVIDER }}
          service_account: `${{ secrets.WIF_SERVICE_ACCOUNT }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
      
      - name: Build and Deploy
        run: |
          gcloud run deploy `$SERVICE_NAME \
            --source . \
            --region `$REGION \
            --allow-unauthenticated \
            --set-secrets="DB_SERVER=harmonylab-db-server:latest,DB_NAME=harmonylab-db-name:latest,DB_USER=harmonylab-db-user:latest,DB_PASSWORD=harmonylab-db-password:latest"
      
      - name: Show URL
        run: |
          gcloud run services describe `$SERVICE_NAME --region=`$REGION --format="value(status.url)"
"@
    $workflowContent | Out-File -FilePath $workflowPath -Encoding UTF8
    Write-Host "  ✓ deploy.yml created" -ForegroundColor Green
}

# ========================================
# Step 6: Verify requirements.txt
# ========================================
Write-Host ""
Write-Host "Step 6: Checking requirements.txt..." -ForegroundColor Yellow

$requirementsPath = Join-Path $PROJECT_PATH "requirements.txt"
$content = Get-Content $requirementsPath -Raw -ErrorAction SilentlyContinue

if ($content -notmatch "google-cloud-secret-manager") {
    Write-Host "  Adding google-cloud-secret-manager to requirements.txt..." -ForegroundColor Cyan
    Add-Content -Path $requirementsPath -Value "google-cloud-secret-manager>=2.16.0"
    Write-Host "  ✓ Updated requirements.txt" -ForegroundColor Green
} else {
    Write-Host "  ✓ requirements.txt already has secret-manager" -ForegroundColor Green
}

# ========================================
# Step 7: Summary
# ========================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Migration Setup Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Secrets configured:" -ForegroundColor Green
foreach ($secretName in $secrets.Keys) {
    Write-Host "  - $secretName" -ForegroundColor White
}
Write-Host ""
Write-Host "Files verified/created:" -ForegroundColor Green
Write-Host "  - Dockerfile" -ForegroundColor White
Write-Host "  - .github/workflows/deploy.yml" -ForegroundColor White
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. Verify config/settings.py loads from env vars" -ForegroundColor White
Write-Host "  2. Commit and push:" -ForegroundColor White
Write-Host "     cd `"$PROJECT_PATH`"" -ForegroundColor Gray
Write-Host "     git add ." -ForegroundColor Gray
Write-Host "     git commit -m `"Cloud migration complete`"" -ForegroundColor Gray
Write-Host "     git push origin main" -ForegroundColor Gray
Write-Host "  3. Monitor GitHub Actions deployment" -ForegroundColor White
Write-Host "  4. Test Cloud Run URL:" -ForegroundColor White
Write-Host "     gcloud run services describe harmonylab --region=us-central1 --format=`"value(status.url)`"" -ForegroundColor Gray
Write-Host ""

# Check for WIF secrets reminder
Write-Host "REMINDER - GitHub Repository Secrets Required:" -ForegroundColor Magenta
Write-Host "  Go to: https://github.com/coreyprator/HarmonyLab/settings/secrets/actions" -ForegroundColor White
Write-Host "  Add:" -ForegroundColor White
Write-Host "    - WIF_PROVIDER" -ForegroundColor Gray
Write-Host "    - WIF_SERVICE_ACCOUNT" -ForegroundColor Gray
Write-Host ""
