# [HarmonyLab] 🔵 v1.4.1 Auth Bug Fix — Unauthenticated Access

> **From**: Claude.ai (Architect)
> **To**: Claude Code (Command Center)
> **Project**: 🔵 HarmonyLab
> **Task**: auth-redirect-fix
> **Timestamp**: 2026-02-07T20:30:00Z
> **Priority**: HIGH — Security Issue
> **Type**: Bug Fix

---

## 🔴 Issue

**Unauthenticated users can see app content.**

Current behavior:
- Home page shows songs list (Corcovado, etc.) without login
- No redirect to login page
- "Sign in with Google" button visible but app content is exposed

Expected behavior:
- Unauthenticated users should see ONLY the login page
- All app content (songs, quiz, progress) requires authentication
- Redirect to login on any page if not authenticated

---

## 🟢 Project Methodology Violation

**This should have been caught before handoff.**

Per project methodology, CC must verify:
- [ ] Auth-protected pages actually require auth
- [ ] Unauthenticated access is blocked
- [ ] Redirect to login works

This was not tested.

---

## Required Fix

### 1. Create Login Page (`frontend/login.html`)

Dedicated login page with:
- HarmonyLab branding
- "Sign in with Google" button
- No access to app content

```html
<!DOCTYPE html>
<html>
<head>
    <title>HarmonyLab - Sign In</title>
    <!-- Same styles as app -->
</head>
<body>
    <div class="login-container">
        <h1>HarmonyLab</h1>
        <p>Jazz chord progression training</p>
        <button onclick="signInWithGoogle()">Sign in with Google</button>
    </div>
    <script src="js/auth.js"></script>
</body>
</html>
```

### 2. Add Auth Check to ALL Pages

Every page (index.html, song.html, quiz.html, progress.html) must:

```javascript
// At top of page load
document.addEventListener('DOMContentLoaded', async () => {
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        window.location.href = '/login.html';
        return;
    }
    // ... rest of page initialization
});
```

### 3. Update auth.js

Add `checkAuth()` function that:
1. Checks for valid token in localStorage
2. Validates token with `/api/v1/auth/me`
3. Returns true/false
4. Handles token refresh if needed

```javascript
async function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) return false;
    
    try {
        const response = await fetch('/api/v1/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) return true;
        
        // Try refresh
        const refreshed = await refreshToken();
        return refreshed;
    } catch {
        return false;
    }
}
```

### 4. Hide Content Until Auth Confirmed

Prevent flash of content before redirect:

```html
<body style="display: none;">
    <!-- content -->
</body>

<script>
document.addEventListener('DOMContentLoaded', async () => {
    if (await checkAuth()) {
        document.body.style.display = 'block';
    } else {
        window.location.href = '/login.html';
    }
});
</script>
```

---

## Testing Checklist (REQUIRED Before Handoff)

| Test | Expected | Verified |
|------|----------|----------|
| Visit `/` not logged in | Redirect to `/login.html` | [ ] |
| Visit `/song.html?id=1` not logged in | Redirect to `/login.html` | [ ] |
| Visit `/quiz.html` not logged in | Redirect to `/login.html` | [ ] |
| Visit `/progress.html` not logged in | Redirect to `/login.html` | [ ] |
| No flash of content before redirect | Content hidden until auth check | [ ] |
| Login page shows sign-in button | Button visible and styled | [ ] |
| After login, redirect to home | Returns to `/` with content | [ ] |

**Do NOT send completion handoff until ALL tests pass.**

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `frontend/login.html` | **CREATE** — Dedicated login page |
| `frontend/index.html` | **MODIFY** — Add auth check + redirect |
| `frontend/song.html` | **MODIFY** — Add auth check + redirect |
| `frontend/quiz.html` | **MODIFY** — Add auth check + redirect |
| `frontend/progress.html` | **MODIFY** — Add auth check + redirect |
| `frontend/js/auth.js` | **MODIFY** — Add checkAuth() function |

---

## Do NOT Change

- Backend auth endpoints (working correctly)
- Version number (stay at 1.4.1 — this is a bug fix)
- Google OAuth configuration (Corey's task)

---

## Definition of Done

- [ ] Login page created
- [ ] All app pages redirect to login if not authenticated
- [ ] No content visible before auth check completes
- [ ] ALL 7 tests above pass
- [ ] Deployed and verified
- [ ] Handoff sent with test results

---

*Bug fix request from Claude.ai (Architect)*
*Test thoroughly before handoff — this was missed the first time*
