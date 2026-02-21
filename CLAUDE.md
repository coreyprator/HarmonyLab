# CLAUDE.md - HarmonyLab AI Instructions

---

## ⚠️ Handoff Bridge — MANDATORY

ALL responses to Claude.ai/Corey MUST use the handoff bridge.
Create file → Run handoff_send.py → Provide URL.
NO EXCEPTIONS. See project-methodology/CLAUDE.md for details.

---

## Handoff Lifecycle Protocol

### Receiving Handoffs
1. Note the ID (HO-XXXX) from the handoff header
2. Archive handoff: `handoffs/archive/HO-XXXX_request.md`
3. Delete from inbox (garbage collect)

### Completion Response Format

Every completion MUST include this exact format:

| Field | Value |
|-------|-------|
| ID | HO-XXXX (from original request) |
| Project | [Icon] [Name] |
| Task | [Brief description] |
| Status | COMPLETE / PARTIAL / BLOCKED |
| Commit | [hash] |
| Handoff | [Full GCS URL] |

### Summary Section
After the table, include:
- Brief description of what was done
- Files changed (list)
- Inbox cleanup confirmation

### Git Commit Format
Include ID in commit message:
```
feat: [description] (HO-XXXX)
fix: [description] (HO-XXXX)
```

### Garbage Collection Checklist
After processing handoff:
- [ ] Deleted from inbox: `handoffs/inbox/*.md`
- [ ] Archived to: `handoffs/archive/`
- [ ] Reminded Corey about Downloads folder cleanup

---

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

### Definition of Done (MANDATORY for ALL Tasks)

Before sending a completion handoff, ALL items must be checked:

**Code**:
- [ ] Code changes complete
- [ ] Tests pass (if applicable)

**Git (MANDATORY)**:
- [ ] All changes staged: `git add [files]`
- [ ] Committed: `git commit -m "type: description (vX.X.X)"`
- [ ] Pushed: `git push origin main`

**Deployment (MANDATORY)**:
- [ ] Backend deployed: `gcloud run deploy harmonylab --source . --region us-central1`
- [ ] Frontend deployed: `gcloud run deploy harmonylab-frontend --source ./frontend --region us-central1`
- [ ] Health check passes: `curl https://harmonylab.rentyourcio.com/health`
- [ ] Version matches: Response shows new version

**UAT (MANDATORY for features)**:
- [ ] Claude.ai creates UAT checklist
- [ ] Corey executes UAT
- [ ] UAT results submitted to Claude.ai
- [ ] UAT PASSED (all critical tests green)
- [ ] UAT results stored in MetaPM

**Handoff (MANDATORY)**:
- [ ] Handoff created with deployment verification
- [ ] Uploaded to GCS
- [ ] URL provided

⚠️ "Next steps: Deploy" is NOT acceptable. Deploy first, then send handoff.
⚠️ A feature is NOT complete until UAT passes.

### Before ANY Handoff (LL-030, LL-049)
1. ✅ Git commit and push (MANDATORY)
2. ✅ Deploy code (you own deployment)
3. ✅ Run tests: `pytest tests/ -v`
4. ✅ Verify deployment with PINEAPPLE test
5. ✅ Include test output in handoff
6. ❌ Never say "complete" without proof

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

## 🔒 Security Requirements

### API Keys & Secrets

**NEVER**:
- Hardcode API keys, passwords, or secrets in code
- Include secrets in handoff documents
- Log secrets to console or files
- Commit secrets to git (even in .gitignore'd files)
- Share secrets in chat responses

**ALWAYS**:
- Use GCP Secret Manager for all secrets
- Reference secrets by name, not value: `gcloud secrets versions access latest --secret="secret-name"`
- Use environment variables injected at runtime
- Mask secrets in logs: `key=***REDACTED***`

### If a Secret is Accidentally Exposed

1. **Rotate immediately** — Generate new secret, update in Secret Manager
2. **Notify Corey** — Security incident
3. **Audit** — Check git history, handoff docs, logs for exposure
4. **Document** — Add to lessons learned

### Pre-Commit Checks

Before any commit, verify:
- [ ] No API keys in code
- [ ] No secrets in comments
- [ ] No credentials in test files
- [ ] No keys in handoff documents

---

## Communication Protocol

All responses to Claude.ai or Corey **MUST** use the Handoff Bridge.
See `project-methodology/CLAUDE.md` for full policy.

---

**Last Updated**: 2026-02-07
**Methodology Version**: 3.14
