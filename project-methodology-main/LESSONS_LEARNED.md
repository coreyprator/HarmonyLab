# Lessons Learned Log

This document captures issues encountered during project development, their root causes, and the fixes applied to the methodology.

## Format

Each entry includes:
- **Date**: When the issue was encountered
- **Project**: Which project surfaced the issue
- **Issue**: What went wrong
- **Root Cause**: Why it happened
- **Fix Applied**: How the methodology was updated
- **Template Section**: Where the fix lives

---

## 2024-12 Lessons (v3.5)

### LL-001: VS Code AI Didn't Create Database User

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | VS Code AI generated code expecting database user, but never created the user in SQL Server |
| Root Cause | Responsibility for database user creation was not explicitly assigned |
| Fix Applied | Added "Create database & user in SQL" to VS Code AI responsibilities in the Responsibility Matrix |
| Template Section | Phase 1: Responsibility Matrix |

**Impact**: Deployment failed with authentication errors. Required manual intervention to create the database user.

---

### LL-002: Password Prompt Blocking GCP Commands

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | `gcloud config set project` prompted for password, blocking automated workflows |
| Root Cause | Authentication order was wrong—project was set before browser auth completed |
| Fix Applied | Created Phase 0 with explicit authentication order. Added warning about password prompts. |
| Template Section | Phase 0: Pre-Kickoff Setup, Section 0.1 |

**Impact**: VS Code AI couldn't proceed with gcloud commands. User had to manually intervene with authentication.

**Key Learning**: The correct order is:
1. `gcloud auth login` (browser/Passkey)
2. `gcloud auth application-default login`
3. `gcloud config set project` (should NOT prompt)
4. `gcloud auth application-default set-quota-project`

---

### LL-003: Wrong GCP Project Selected

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Commands ran against wrong GCP project, creating resources in unexpected location |
| Root Cause | Project was not verified at the start of the session |
| Fix Applied | Added project verification step after authentication |
| Template Section | Phase 0: Pre-Kickoff Setup, Section 0.2 |

**Impact**: Had to clean up resources from wrong project and recreate in correct project.

---

### LL-004: "Project Does Not Exist" Errors

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | HarmonyLab (planning) |
| Issue | Kickoff document referenced GCP project that hadn't been created yet |
| Root Cause | Decision to use new vs. existing project wasn't made upfront |
| Fix Applied | Added pre-kickoff questions about GCP project choice |
| Template Section | Pre-Kickoff Checklist (separate document) |

**Impact**: Wasted time debugging "project not found" errors that were actually planning issues.

---

### LL-005: SQL Scripts Failed in Cloud SQL Studio

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | SQL scripts with GO statements failed in Cloud SQL Studio |
| Root Cause | Cloud SQL Studio doesn't support GO batch separator |
| Fix Applied | Added SQL Execution Environment section specifying which tool to use |
| Template Section | Phase 0: Pre-Kickoff Setup, Section 0.3 |

**Impact**: Schema creation failed. Had to re-run scripts in SSMS.

**Key Learning**: 
- SSMS/sqlcmd: Full T-SQL support including GO
- Cloud SQL Studio: Single statements only

---

### LL-006: VS Code AI Ran Localhost Server

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | VS Code AI started local development server with `uvicorn` instead of deploying to Cloud Run |
| Root Cause | Default developer workflow is local-first; cloud-first not documented |
| Fix Applied | Added "NO LOCALHOST SERVERS" section with cloud-first workflow diagram |
| Template Section | Phase 0: Pre-Kickoff Setup, Section 0.4 |

**Impact**: Testing was done against localhost, then failed on Cloud Run due to environment differences.

**Key Learning**: The workflow is always: Write → Push → Deploy → Test on Cloud Run URL

---

### LL-007: Git Repository Not Initialized

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | VS Code AI generated code but didn't initialize git or push to GitHub |
| Root Cause | Git initialization wasn't in the task list |
| Fix Applied | Added git init, remote add, commit, push to VS Code AI responsibilities |
| Template Section | Phase 1: Responsibility Matrix |

**Impact**: Code sat locally; GitHub Actions never triggered.

---

### LL-008: No Test Plan Created

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Sprint 1 completed but no tests existed and no plan for what to test |
| Root Cause | TEST_PLAN.md wasn't a required deliverable |
| Fix Applied | Added TEST_PLAN.md to Claude's required deliverables; added to Sprint 1 DoD |
| Template Section | Phase 1: Responsibility Matrix, Phase 3: Sprint 1 DoD |

**Impact**: Sprint 2 started without clarity on what needed testing.

---

### LL-009: No UI Design Document

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Frontend development started without any UI design specification |
| Root Cause | UI_DESIGN.md wasn't a required deliverable |
| Fix Applied | Added UI_DESIGN.md to Claude's required deliverables |
| Template Section | Phase 1: Responsibility Matrix |

**Impact**: Frontend had to be reworked multiple times due to unclear requirements.

---

### LL-010: Users Confused by Application

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Users didn't understand how to use the application |
| Root Cause | No user documentation existed |
| Fix Applied | Added USER_GUIDE.md to Claude's required deliverables |
| Template Section | Phase 1: Responsibility Matrix |

**Impact**: Support burden on developer; users abandoned application.

---

### LL-011: Technical Errors Exposed to Users

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Users saw errors like `NoneType has no attribute 'id'` |
| Root Cause | No guidelines for user-friendly error messages |
| Fix Applied | Added Testing Philosophy section with error message guidelines |
| Template Section | Phase 4: Sprint 2, Section 4.1 |

**Impact**: Users confused by technical errors; poor user experience.

**Key Learning**:
- Happy path errors: User-friendly messages
- System errors: Can bubble up (users have AI to explain)

---

### LL-012: Help Content Embedded in Application

| Field | Value |
|-------|-------|
| Date | 2024-12-27 |
| Project | ArtForge |
| Issue | Help documentation was embedded in React components |
| Root Cause | No strategy defined for help content |
| Fix Applied | Changed to external link strategy—help links to GitHub docs |
| Template Section | Phase 4: Sprint 2, Section 4.2 |

**Impact**: Every documentation fix required a full redeploy.

**Key Learning**: External help links allow doc updates without app deployment.

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Lessons | 12 |
| Template Sections Updated | 8 |
| New Sections Added | 4 |
| Projects Contributing | ArtForge (primary), HarmonyLab (planning) |

## How to Add New Lessons

1. Create entry with the next LL number (e.g., LL-013)
2. Fill in all fields in the table format
3. Add Impact and Key Learning sections if significant
4. Update the Summary Statistics
5. Update the relevant template section
6. Increment version in CHANGELOG.md
