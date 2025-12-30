# Sprint 1 Checklist: Infrastructure & API

**Goal**: Working backend deployed to Cloud Run with database connectivity and core API endpoints.

---

## Phase 1: Setup & Configuration

### GCP Authentication
- [ ] `gcloud auth login` completed (browser/Passkey)
- [ ] `gcloud auth application-default login` completed
- [ ] `gcloud config set project [PROJECT_ID]` completed (no password prompt)
- [ ] `gcloud auth application-default set-quota-project [PROJECT_ID]` completed
- [ ] Verified with `gcloud config get-value project`

### Database Setup
- [ ] Database created on Cloud SQL instance
- [ ] Database user created with secure password
- [ ] User granted db_datareader and db_datawriter roles
- [ ] Schema (tables, indexes, constraints) created
- [ ] Test data inserted (if applicable)

**SQL Execution Note**: If scripts contain GO statements, use SSMS or sqlcmd, NOT Cloud SQL Studio.

### Secret Manager
- [ ] Database connection string stored as secret
- [ ] API keys stored as secrets (if applicable)
- [ ] OAuth client secret stored (if applicable)
- [ ] IAM bindings added for Cloud Run service account

```powershell
# Verify secrets exist
gcloud secrets list --filter="name:[PROJECT_SLUG]"

# Verify IAM binding
gcloud secrets get-iam-policy [SECRET_NAME]
```

---

## Phase 2: Code Generation

### Project Structure
- [ ] `app/` directory with FastAPI application
- [ ] `app/main.py` - Application entry point
- [ ] `app/config.py` - Settings from Secret Manager
- [ ] `app/database.py` - Database connection
- [ ] `app/models.py` - Pydantic models
- [ ] `app/routers/` - API route modules
- [ ] `tests/` directory structure
- [ ] `Dockerfile` configured
- [ ] `requirements.txt` with dependencies
- [ ] `.gitignore` (Python + secrets)
- [ ] `README.md` with project overview

### API Endpoints
- [ ] `GET /health` - Health check (no auth)
- [ ] Core CRUD endpoints implemented
- [ ] Authentication middleware (if applicable)
- [ ] Error handling with appropriate status codes
- [ ] Request validation with Pydantic

### External Integrations
- [ ] API clients configured
- [ ] Credentials loaded from Secret Manager
- [ ] Error handling for API failures
- [ ] Rate limiting considered

---

## Phase 3: CI/CD Pipeline

### GitHub Actions
- [ ] `.github/workflows/deploy.yml` created
- [ ] Workload Identity Federation configured
- [ ] Triggers on push to main branch
- [ ] Builds and deploys to Cloud Run

### Initial Deployment
- [ ] Git repository initialized
- [ ] Remote added: `git remote add origin [GITHUB_URL]`
- [ ] Initial commit created
- [ ] Pushed to GitHub: `git push -u origin main`
- [ ] GitHub Actions workflow triggered
- [ ] Deployment completed successfully

```powershell
# Get Cloud Run URL
gcloud run services describe [SERVICE_NAME] --region=us-central1 --format="value(status.url)"
```

---

## Phase 4: Verification

### Health Check
```powershell
$URL = "[CLOUD_RUN_URL]"
curl "$URL/health"
# Expected: {"status": "healthy"} or similar
```

### API Endpoints
- [ ] Each endpoint returns expected response
- [ ] Authentication works (if applicable)
- [ ] Database queries execute successfully
- [ ] Error cases return appropriate status codes

### Logs Check
```powershell
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=[SERVICE_NAME]" --limit=20
```
- [ ] No unexpected errors in logs
- [ ] Database connections successful
- [ ] Secret Manager access working

---

## Phase 5: Documentation (Claude Deliverables)

These documents are created by Claude during Sprint 1:

- [ ] **TEST_PLAN.md** - What to test and how
- [ ] **UI_DESIGN.md** - Frontend specifications
- [ ] **USER_GUIDE.md** - End-user documentation

---

## Sprint 1 Definition of Done

All items must be checked for Sprint 1 to be complete:

- [ ] Database created with tables and user
- [ ] All secrets stored in Secret Manager with proper IAM
- [ ] API endpoints accessible on Cloud Run URL
- [ ] Authentication working (if applicable)
- [ ] Database CRUD operations succeed via API
- [ ] GitHub Actions deploys successfully on push to main
- [ ] TEST_PLAN.md created and reviewed
- [ ] UI_DESIGN.md created and reviewed
- [ ] USER_GUIDE.md created and reviewed

---

## Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| "Secret not found" | Check secret name, verify IAM binding |
| "Connection refused" to database | Verify Cloud SQL instance IP, check authorized networks |
| GitHub Actions fails | Check WIF_PROVIDER and WIF_SERVICE_ACCOUNT secrets |
| "Module not found" | Verify requirements.txt, rebuild container |
| CORS errors | Add CORS middleware to FastAPI |

---

## Handoff to Sprint 2

Sprint 1 is complete when:
1. All checklist items above are verified
2. Project Lead has tested core API functionality
3. TEST_PLAN.md, UI_DESIGN.md, USER_GUIDE.md are approved

Sprint 2 begins with:
- Implementing tests per TEST_PLAN.md
- Building frontend per UI_DESIGN.md
- Finalizing documentation per USER_GUIDE.md
