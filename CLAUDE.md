# CLAUDE.md - HarmonyLab AI Instructions

> ⚠️ **READ THIS ENTIRE FILE** before writing any code or running any commands.
> **DO NOT** invent or guess infrastructure values. Use EXACT values below.

---

## Project Identity

| Field | Value |
|-------|-------|
| Project Name | HarmonyLab |
| Description | Jazz chord progression training app |
| Repository | https://github.com/coreyprator/harmonylab |
| Local Path | G:\My Drive\Code\Python\harmonylab |
| Methodology | [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.14 |

---

## GCP Infrastructure (EXACT VALUES - DO NOT GUESS)

| Resource | Value |
|----------|-------|
| GCP Project ID | `super-flashcards-475210` |
| Region | `us-central1` |
| Cloud Run Service (Backend) | `harmonylab` |
| Cloud Run Service (Frontend) | `harmonylab-frontend` |
| Cloud Run URL (Backend) | `https://harmonylab-wmrla7fhwa-uc.a.run.app` |
| Cloud Run URL (Frontend) | `https://harmonylab-frontend-wmrla7fhwa-uc.a.run.app` |
| Cloud SQL Instance | `flashcards-db` |
| Cloud SQL IP | `35.224.242.223` |
| Database Name | `HarmonyLab` |

### Verification Commands
```powershell
# Always verify correct project before ANY gcloud command
gcloud config get-value project
# Must output: super-flashcards-475210

# If wrong:
gcloud config set project super-flashcards-475210
```

---

## Deployment

### Deploy Backend
```powershell
cd "G:\My Drive\Code\Python\harmonylab"
gcloud run deploy harmonylab --source . --region us-central1 --allow-unauthenticated
```

### Deploy Frontend
```powershell
cd "G:\My Drive\Code\Python\harmonylab\frontend"
gcloud run deploy harmonylab-frontend --source . --region us-central1 --allow-unauthenticated
```

### View Logs
```powershell
gcloud run logs read harmonylab --region=us-central1 --limit=50
gcloud run logs read harmonylab-frontend --region=us-central1 --limit=50
```

---

## Secret Manager

| Secret Name | Purpose |
|-------------|---------|
| `harmonylab-db-password` | Database password |
| `harmonylab-db-user` | `harmonylab_user` |
| `harmonylab-db-server` | `35.224.242.223` |
| `harmonylab-db-name` | Database name |

### Access Secret
```powershell
gcloud secrets versions access latest --secret="harmonylab-db-password"
```

---

## SQL Connectivity
```powershell
# Connect via sqlcmd
sqlcmd -S 35.224.242.223,1433 -U sqlserver -P "$(gcloud secrets versions access latest --secret='db-password')" -d HarmonyLab

# Quick test
sqlcmd -S 35.224.242.223,1433 -U sqlserver -P "$(gcloud secrets versions access latest --secret='db-password')" -d HarmonyLab -Q "SELECT TOP 5 * FROM INFORMATION_SCHEMA.TABLES"
```

---

## Compliance Directives

### Before ANY Work (LL-045)
1. ✅ Read this entire CLAUDE.md file
2. ✅ State what you learned: "Backend service is harmonylab, frontend is harmonylab-frontend, database is HarmonyLab"
3. ❌ Never invent infrastructure values

### Before ANY Handoff (LL-030, LL-049)
1. ✅ Deploy code (you own deployment)
2. ✅ Run tests: `pytest tests/ -v`
3. ✅ Verify deployment with PINEAPPLE test
4. ✅ Include test output in handoff
5. ❌ Never say "complete" without proof

### Locked Vocabulary (LL-049)
These words require proof (deployed revision + test output):
- "Complete" / "Done" / "Finished" / "Ready"
- "Implemented" / "Fixed" / "Working"
- ✅ emoji next to features

Without proof, say: "Code written. Pending deployment and testing."

### Forbidden Phrases
- ❌ "Test locally" (no localhost exists)
- ❌ "Let me know if you want me to deploy" (you own deployment)
- ❌ "Please run this command" (you run commands)

---

## PINEAPPLE Test (LL-044)

Before debugging ANY deployment issue:
1. Add `"canary": "PINEAPPLE-99999"` to /health endpoint
2. Deploy
3. Verify: `curl https://harmonylab-wmrla7fhwa-uc.a.run.app/health` shows PINEAPPLE
4. If missing → deployment failed, fix that first

---

## Architecture Notes

- **Two services**: Backend (API) and Frontend (static/UI)
- **Database**: SQL Server on Cloud SQL
- **Purpose**: Jazz chord progression training

---

**Last Updated**: 2026-01-31
**Methodology Version**: 3.14
