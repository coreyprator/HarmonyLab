# [HarmonyLab] 🔵 Cache Clear + Version Bump Required

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔵 HarmonyLab
> **Task**: cache-clear-version-bump
> **Timestamp**: 2026-02-07T18:00:00Z
> **Priority**: HIGH

---

## Actions Required

### 1. Clear Analysis Cache (All Songs)

Run this SQL to force re-analysis with the new jazz-style Roman numerals:

```sql
UPDATE SongAnalysis SET analysis_json = NULL;
```

Or if using PostgreSQL:
```sql
UPDATE song_analysis SET analysis_json = NULL;
```

### 2. Bump Version Number

**Project Methodology 🟢 Requirement**: Version must be bumped after fixes.

Current: v1.3.0
New: **v1.3.1** (patch for cache fix)

Update in:
- `app/config.py` or `config/settings.py` (VERSION constant)
- `frontend/index.html` (if version displayed)
- `frontend/song.html` (nav bar version badge)

### 3. Redeploy

After version bump:
```bash
# Backend
gcloud run deploy harmonylab --source . --region us-central1

# Frontend  
gcloud run deploy harmonylab-frontend --source frontend/ --region us-central1
```

### 4. Verify

After deployment:
1. Check health endpoint shows v1.3.1
2. Visit a song that was NOT manually refreshed
3. Confirm Roman numerals are jazz-style (not figured bass)
4. Confirm nav bar shows v1.3.1

---

## Definition of Done

- [ ] SongAnalysis cache cleared
- [ ] Version bumped to v1.3.1
- [ ] Both services redeployed
- [ ] Version verified on health endpoint
- [ ] Roman numerals verified (without manual refresh)
- [ ] Sent completion report via handoff bridge

---

*Sent via Handoff Bridge per project-methodology policy*
