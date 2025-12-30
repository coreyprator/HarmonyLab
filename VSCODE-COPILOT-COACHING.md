# VS Code Copilot Coaching: HarmonyLab Cloud Migration

**Date**: 2025-12-28  
**From**: Claude (Architect)  
**To**: VS Code Copilot  
**Reference**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.5  
**Status**: CORRECTIVE ACTION - Your recommendations violated methodology

---

## What You Got Wrong

Your "Three-Phase Approach" recommendation has several critical violations of the project methodology:

### ❌ Violation 1: Manual Secret Creation

**Your Recommendation (WRONG):**
```
Your role (manual GCP tasks):
  Create the 2 secrets in Secret Manager:
    gcloud secrets create harmonylab-db-user --data-file=- # (then paste: harmonylab_user)
    gcloud secrets create harmonylab-db-password --data-file=-# (then paste: HarmonyUser2025!)
```

**Methodology v3.5 (CORRECT):**
Per `PROJECT_KICKOFF_TEMPLATE.md` lines 100-101 and 188-197:

| Task | Project Lead | Claude | VS Code AI |
|------|:------------:|:------:|:----------:|
| Store secrets in Secret Manager | | | ✅ |
| Run gcloud commands | | | ✅ |

**Correct Automation:**
```powershell
# VS Code AI runs these - NOT Project Lead
echo -n "35.224.242.223" | gcloud secrets create harmonylab-db-server --data-file=- --project=super-flashcards-475210
echo -n "HarmonyLab" | gcloud secrets create harmonylab-db-name --data-file=- --project=super-flashcards-475210
echo -n "harmonylab_user" | gcloud secrets create harmonylab-db-user --data-file=- --project=super-flashcards-475210
echo -n "HarmonyUser2025!" | gcloud secrets create harmonylab-db-password --data-file=- --project=super-flashcards-475210

# Grant Cloud Run access
$SA = "super-flashcards-475210@appspot.gserviceaccount.com"
foreach ($secret in @("harmonylab-db-server", "harmonylab-db-name", "harmonylab-db-user", "harmonylab-db-password")) {
    gcloud secrets add-iam-policy-binding $secret `
        --member="serviceAccount:$SA" `
        --role="roles/secretmanager.secretAccessor" `
        --project=super-flashcards-475210
}
```

**Why this matters**: The methodology explicitly assigns secret creation to VS Code AI because it should be automated and repeatable, not manual copy-paste.

---

### ❌ Violation 2: Incomplete Responsibility Understanding

**Your Recommendation (WRONG):**
```
You (Corey):
  Manual GCP/cloud tasks
  Test endpoints after I build them
```

**Methodology v3.5 (CORRECT):**
Per `PROJECT_KICKOFF_TEMPLATE.md` lines 86-108:

| Task | Project Lead (Corey) | Claude | VS Code AI |
|------|:--------------------:|:------:|:----------:|
| Create GitHub repository | ✅ | | |
| Create GCP project (if new) | ✅ | | |
| Create OAuth credentials | ✅ | | |
| Provide API keys | ✅ | | |
| Design system architecture | | ✅ | |
| Create database schema | | ✅ | |
| **Create database & user in SQL** | | | ✅ |
| **Store secrets in Secret Manager** | | | ✅ |
| **Run gcloud commands** | | | ✅ |
| **Initialize git repository** | | | ✅ |
| **Create GitHub Actions workflow** | | | ✅ |
| **Push to GitHub** | | | ✅ |
| **Debug deployment issues** | | | ✅ |

**The ONLY authentication-related manual task for Corey**:
Per `LESSONS_LEARNED.md` LL-002, the authentication order must be followed manually ONCE at session start:
```powershell
gcloud auth login                    # Browser/Passkey - ONCE per session
gcloud auth application-default login
gcloud config set project super-flashcards-475210
gcloud auth application-default set-quota-project super-flashcards-475210
```

After authentication, **YOU (VS Code AI) run all gcloud commands**.

---

### ❌ Violation 3: Vague "Help Debug" Instead of Ownership

**Your Recommendation (WRONG):**
```
My role (Claude):
  Review/fix any Dockerfile or GitHub Actions issues
  Help debug deployment errors
```

**Methodology v3.5 (CORRECT):**
Per the responsibility matrix:
- **Claude (Architect)**: Designs system, creates schema, designs API endpoints, generates code FILES, creates documentation (TEST_PLAN.md, UI_DESIGN.md, USER_GUIDE.md)
- **VS Code AI (Coder)**: IMPLEMENTS and DEBUGS. You don't "help debug" — you OWN debugging.

---

## The Correct Approach

### Phase 0: Authentication (Corey does ONCE)

Corey runs these commands ONE TIME at session start:
```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project super-flashcards-475210
gcloud auth application-default set-quota-project super-flashcards-475210

# Verify
gcloud config get-value project
# Should output: super-flashcards-475210
```

If any command prompts for password, Corey stops and re-runs `gcloud auth login`.

---

### Phase 1: VS Code AI Tasks (YOU DO THIS)

**You execute these commands in the terminal:**

#### 1.1 Check Authentication (Don't Assume)
```powershell
gcloud config get-value project
# Must output: super-flashcards-475210
# If not, tell Corey to run Phase 0
```

#### 1.2 Check If Secrets Already Exist
```powershell
gcloud secrets list --filter="name:harmonylab" --project=super-flashcards-475210
```

If secrets DON'T exist, create them:
```powershell
# Create all secrets (automated - no manual paste)
echo -n "35.224.242.223" | gcloud secrets create harmonylab-db-server --data-file=- --project=super-flashcards-475210
echo -n "HarmonyLab" | gcloud secrets create harmonylab-db-name --data-file=- --project=super-flashcards-475210
echo -n "harmonylab_user" | gcloud secrets create harmonylab-db-user --data-file=- --project=super-flashcards-475210
echo -n "HarmonyUser2025!" | gcloud secrets create harmonylab-db-password --data-file=- --project=super-flashcards-475210
```

If secrets already exist, update them if needed:
```powershell
echo -n "NEW_VALUE" | gcloud secrets versions add harmonylab-db-password --data-file=- --project=super-flashcards-475210
```

#### 1.3 Grant IAM Access
```powershell
$PROJECT_NUMBER = (gcloud projects describe super-flashcards-475210 --format="value(projectNumber)")
$SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

foreach ($secret in @("harmonylab-db-server", "harmonylab-db-name", "harmonylab-db-user", "harmonylab-db-password")) {
    gcloud secrets add-iam-policy-binding $secret `
        --member="serviceAccount:$SA" `
        --role="roles/secretmanager.secretAccessor" `
        --project=super-flashcards-475210
}
```

#### 1.4 Verify Dockerfile Exists
Check `G:\My Drive\Code\Python\Harmony-Lab\Dockerfile`

If missing, create it:
```dockerfile
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
```

#### 1.5 Verify GitHub Actions Workflow
Check `.github/workflows/deploy.yml`

If missing or incomplete, create it per methodology template.

#### 1.6 Update config/settings.py
Must load from Secret Manager or environment (Cloud Run injects from secrets):

```python
import os
from functools import lru_cache

class Settings:
    @property
    def db_server(self) -> str:
        return os.getenv("DB_SERVER", "35.224.242.223")
    
    @property
    def db_name(self) -> str:
        return os.getenv("DB_NAME", "HarmonyLab")
    
    @property
    def db_user(self) -> str:
        return os.getenv("DB_USER", "harmonylab_user")
    
    @property
    def db_password(self) -> str:
        return os.getenv("DB_PASSWORD", "")
    
    @property
    def db_driver(self) -> str:
        return "ODBC Driver 17 for SQL Server"
    
    @property
    def port(self) -> int:
        return int(os.getenv("PORT", "8080"))

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

#### 1.7 Push and Deploy
```powershell
cd "G:\My Drive\Code\Python\Harmony-Lab"
git add .
git commit -m "Cloud migration: Dockerfile, GitHub Actions, Secret Manager config"
git push origin main
```

#### 1.8 Verify Deployment
```powershell
# Wait for GitHub Actions to complete, then:
$URL = gcloud run services describe harmonylab --region=us-central1 --format="value(status.url)" --project=super-flashcards-475210

curl "$URL/health"
```

---

## Summary: What You (VS Code AI) Must Do

| Step | Command/Action | Owner |
|------|----------------|-------|
| 1 | Verify `gcloud config get-value project` returns correct project | VS Code AI |
| 2 | Check if secrets exist: `gcloud secrets list --filter="harmonylab"` | VS Code AI |
| 3 | Create/update secrets using `echo -n | gcloud secrets create` | VS Code AI |
| 4 | Grant IAM bindings to Cloud Run service account | VS Code AI |
| 5 | Verify/create Dockerfile | VS Code AI |
| 6 | Verify/create GitHub Actions workflow | VS Code AI |
| 7 | Update config/settings.py for env vars | VS Code AI |
| 8 | Git commit and push | VS Code AI |
| 9 | Verify deployment with curl to Cloud Run URL | VS Code AI |

**The ONLY thing Corey does**: Run `gcloud auth login` once at session start if not already authenticated.

---

## Reference Documents in Project

The methodology files are now available at:
`G:\My Drive\Code\Python\Harmony-Lab\project-methodology-main.zip`

Key files:
- `PROJECT_KICKOFF_TEMPLATE.md` - Responsibility matrix, secret automation
- `SPRINT_1_CHECKLIST.md` - Deployment verification steps
- `DEPLOYMENT_CHECKLIST.md` - Post-deployment verification
- `LESSONS_LEARNED.md` - Common issues (LL-002 about auth order)

**Use these as your primary reference for any methodology questions.**

---

## Corrective Action Checklist

- [ ] Read `PROJECT_KICKOFF_TEMPLATE.md` responsibility matrix
- [ ] Understand that VS Code AI runs gcloud commands, not Project Lead
- [ ] Use automated `echo -n | gcloud secrets create` pattern
- [ ] Stop asking Corey to "paste" values manually
- [ ] Own debugging instead of offering to "help"
- [ ] Verify authentication before running commands
- [ ] Follow the NO LOCALHOST workflow: Write → Push → Deploy → Test on Cloud Run

---

**This is a coaching document. Apply these corrections immediately to the HarmonyLab migration.**
