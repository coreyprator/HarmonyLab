/**
 * HarmonyLab Authentication Module
 * Handles Google OAuth, token management, and auth state.
 * Based on Super-Flashcards pattern.
 */

class Auth {
    constructor() {
        this.accessToken = null;
        this.user = this.getStoredUser();
        this._refreshTimer = null;

        // Recover access token from localStorage
        const stored = localStorage.getItem('harmonylab_token');
        if (stored && !this._isExpired(stored)) {
            this.accessToken = stored;
            this._scheduleRefresh(stored);
        }

        // Handle OAuth callback
        this.handleOAuthCallback();

        // Try cookie-based recovery if no token
        if (!this.accessToken && !this._isOAuthCallback()) {
            console.log('No stored token - attempting cookie-based recovery');
            this.refreshToken();
        }

        // Re-verify on app resume
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                if (this.accessToken) {
                    this._checkAndRefresh();
                } else {
                    this.refreshToken();
                }
            }
        });
    }

    _isOAuthCallback() {
        const params = new URLSearchParams(window.location.search);
        return params.get('auth') === 'success' && params.get('token');
    }

    _decodePayload(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const json = decodeURIComponent(
                atob(base64)
                    .split('')
                    .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                    .join('')
            );
            return JSON.parse(json);
        } catch {
            return null;
        }
    }

    _isExpired(token) {
        const payload = this._decodePayload(token);
        if (!payload || !payload.exp) return true;
        return payload.exp * 1000 < Date.now() + 60000;
    }

    _scheduleRefresh(token) {
        if (this._refreshTimer) clearTimeout(this._refreshTimer);

        const payload = this._decodePayload(token);
        if (!payload || !payload.exp) return;

        const expiresAt = payload.exp * 1000;
        const refreshIn = Math.max(expiresAt - Date.now() - 60000, 5000);

        console.log(`Token refresh scheduled in ${Math.round(refreshIn / 1000)}s`);
        this._refreshTimer = setTimeout(() => this.refreshToken(), refreshIn);
    }

    async _checkAndRefresh() {
        if (!this.accessToken) return;
        if (this._isExpired(this.accessToken)) {
            console.log('Token expired, refreshing...');
            await this.refreshToken();
        }
    }

    async refreshToken() {
        try {
            const response = await fetch('/api/v1/auth/refresh', {
                method: 'POST',
                credentials: 'include',
            });

            if (response.ok) {
                const data = await response.json();
                this.accessToken = data.access_token;
                localStorage.setItem('harmonylab_token', data.access_token);
                this._scheduleRefresh(data.access_token);
                window.HLDebug?.emit('auth:token-refreshed', {});
                console.log('Token refreshed successfully');
                return true;
            } else {
                console.warn('Refresh failed:', response.status);
                window.HLDebug?.emit('auth:token-refresh-failed', { status: response.status });
                this.clearAuth();
                return false;
            }
        } catch (error) {
            console.error('Token refresh error:', error);
            return false;
        }
    }

    handleOAuthCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');
        const authSuccess = urlParams.get('auth');

        if (token && authSuccess === 'success') {
            console.log('OAuth callback detected - storing token');

            const payload = this._decodePayload(token);
            if (payload) {
                const user = {
                    id: payload.user_id,
                    email: payload.email,
                };

                this.setAuth(token, user);
                window.HLDebug?.emit('auth:login-success', { email: user.email });
                console.log('Token stored from OAuth callback');

                // Clean URL
                window.history.replaceState({}, document.title, window.location.pathname);

                // Fetch full user profile
                this.verifyToken();
            }
        }
    }

    getStoredUser() {
        const userStr = localStorage.getItem('harmonylab_user');
        if (userStr) {
            try {
                return JSON.parse(userStr);
            } catch {
                return null;
            }
        }
        return null;
    }

    isAuthenticated() {
        return !!this.accessToken;
    }

    getUser() {
        return this.user;
    }

    getUserId() {
        return this.user?.id || null;
    }

    getToken() {
        return this.accessToken;
    }

    setAuth(token, user) {
        this.accessToken = token;
        this.user = user;
        localStorage.setItem('harmonylab_token', token);
        localStorage.setItem('harmonylab_user', JSON.stringify(user));
        this._scheduleRefresh(token);
    }

    clearAuth() {
        if (this._refreshTimer) clearTimeout(this._refreshTimer);
        this.accessToken = null;
        this.user = null;
        localStorage.removeItem('harmonylab_token');
        localStorage.removeItem('harmonylab_user');
    }

    async logout() {
        try {
            await fetch('/api/v1/auth/logout', {
                method: 'POST',
                headers: this.getAuthHeaders(),
                credentials: 'include',
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.clearAuth();
            window.location.href = '/login.html';
        }
    }

    /**
     * Check if user is authenticated. Returns true/false.
     * Use this at page load to gate access.
     */
    async checkAuth() {
        // First check for stored token
        const token = localStorage.getItem('harmonylab_token');
        if (!token) {
            // No token - try cookie-based refresh
            const refreshed = await this.refreshToken();
            return refreshed;
        }

        // Token exists - validate it
        try {
            const response = await fetch('/api/v1/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                // Token valid
                this.accessToken = token;
                const user = await response.json();
                this.user = user;
                localStorage.setItem('harmonylab_user', JSON.stringify(user));
                return true;
            }

            if (response.status === 401) {
                // Token expired - try refresh
                window.HLDebug?.emit('auth:401', { url: '/api/v1/auth/me' });
                const refreshed = await this.refreshToken();
                return refreshed;
            }

            // 5xx or other transient error — don't clear auth if local token is still valid.
            // This prevents logout when the backend restarts (e.g., after a cold start
            // triggered by a heavy import operation).
            if (!this._isExpired(token)) {
                console.warn('Auth check got', response.status, '— trusting non-expired local token');
                this.accessToken = token;
                return true;
            }

            this.clearAuth();
            return false;
        } catch (error) {
            // Network error — trust local token if not expired rather than forcing logout
            console.error('Auth check error:', error);
            if (!this._isExpired(token)) {
                console.warn('Auth check network error — trusting non-expired local token');
                this.accessToken = token;
                return true;
            }
            return false;
        }
    }

    getAuthHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        if (this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }
        return headers;
    }

    async verifyToken() {
        if (!this.accessToken) return false;

        try {
            const response = await fetch('/api/v1/auth/me', {
                headers: this.getAuthHeaders()
            });

            if (response.ok) {
                const user = await response.json();
                this.user = user;
                localStorage.setItem('harmonylab_user', JSON.stringify(user));
                this.updateAuthUI();
                return true;
            } else if (response.status === 401) {
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    return await this.verifyToken();
                }
                this.clearAuth();
                return false;
            } else {
                this.clearAuth();
                return false;
            }
        } catch (error) {
            console.error('Token verification error:', error);
            return false;
        }
    }

    async requireAuth() {
        if (!this.accessToken) {
            const refreshed = await this.refreshToken();
            if (!refreshed) {
                window.location.href = '/index.html?login=required';
                return false;
            }
        }

        const isValid = await this.verifyToken();
        if (!isValid) {
            window.location.href = '/index.html?login=required';
            return false;
        }
        return true;
    }

    updateAuthUI() {
        const authContainer = document.getElementById('auth-container');
        if (!authContainer) return;

        if (this.isAuthenticated() && this.user) {
            authContainer.innerHTML = `
                <div class="user-profile">
                    ${this.user.avatar_url ? `<img src="${this.user.avatar_url}" alt="" class="user-avatar">` : ''}
                    <span class="user-name">${this.user.display_name || this.user.email}</span>
                    <button onclick="auth.logout()" class="btn btn-sm">Logout</button>
                </div>
            `;
        } else {
            authContainer.innerHTML = `
                <a href="/api/v1/auth/google/login" class="btn btn-primary">
                    Sign in with Google
                </a>
            `;
        }
    }

    getGoogleLoginUrl() {
        return '/api/v1/auth/google/login';
    }

    // REQ-016: Fetch debug_mode preference and enable HLDebug if set
    async applyDebugModePreference() {
        try {
            const token = this.getToken();
            if (!token) return;
            const resp = await fetch('/api/v1/preferences', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (!resp.ok) return;
            const prefs = await resp.json();
            if (prefs.debug_mode && window.HLDebug) {
                window.HLDebug.enabled = true;
                const panel = document.getElementById('debug-panel');
                if (panel) panel.style.display = 'block';
                console.log('[HLDebug] enabled via debug_mode preference');
            }
        } catch (e) { /* non-blocking */ }
    }
}

// BUG-028 Defect A: HLDebug initialized here so it is available on EVERY authenticated page.
// Previously only in song.html; moved to auth.js which loads on all pages.
// Canonical debug name: window.HLDebug — see PROJECT_KNOWLEDGE.md for what it shows.
(function () {
    var ENABLED =
        new URLSearchParams(window.location.search).get('debug') === '1' ||
        localStorage.getItem('hl-debug') === '1';
    var _events = [];

    function _push(tag, data) {
        _events.push({ t: new Date().toISOString(), tag: tag, data: data });
        if (_events.length > 20) _events.shift();
        try {
            document.dispatchEvent(new CustomEvent('hldebugevent', {
                detail: { tag: tag, data: data, t: _events[_events.length - 1].t }
            }));
        } catch (e) { /* non-blocking */ }
    }

    window.HLDebug = {
        enabled: ENABLED,
        _events: _events,
        // BUG-028 Defect B: accept both (tag, payload) AND (tag, event, payload)
        log: function (component, eventOrData, data) {
            if (!this.enabled) return;
            var tag, payload;
            if (typeof eventOrData === 'object' && eventOrData !== null && data === undefined) {
                tag = component;
                payload = eventOrData;
            } else {
                tag = component + ' | ' + eventOrData;
                payload = data;
            }
            console.log('[HLDebug]', tag, payload !== undefined ? payload : '');
            _push(tag, payload);
        },
        emit: function (tag, data) {
            if (!this.enabled) return;
            console.log('[HLDebug]', tag, data !== undefined ? data : '');
            _push(tag, data);
        }
    };

    if (ENABLED) {
        console.log('[HLDebug] active — initialized in auth.js (BUG-028 fix)');
    }
}());

// Create global auth instance
window.auth = new Auth();

// BUG-028: Route change emit wiring (page load + hash change)
(function () {
    if (!window.HLDebug) return;
    window.HLDebug.emit('route:load', { url: window.location.href });
    window.addEventListener('hashchange', function () {
        window.HLDebug.emit('route:hashchange', { hash: window.location.hash });
    });
}()); 

// HL-011: Fetch version from backend and update nav on all pages
(async () => {
    try {
        const r = await fetch('/health');
        const d = await r.json();
        if (d.version) {
            document.querySelectorAll('.nav-version').forEach(el => {
                el.textContent = 'v' + d.version;
            });
        }
    } catch (e) {}
})();

// Update UI on load
document.addEventListener('DOMContentLoaded', () => {
    if (window.auth.isAuthenticated()) {
        window.auth.updateAuthUI();
        // REQ-016: Apply debug_mode preference from server
        window.auth.applyDebugModePreference();
    } else {
        window.auth.updateAuthUI();
    }
});

// HL-v1.8.5: Global toast notification system — Standard B: 10s for errors, close button
window.showToast = function(message, type = 'error') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = [
            'position:fixed', 'bottom:20px', 'right:20px', 'z-index:9999',
            'display:flex', 'flex-direction:column', 'gap:8px',
            'max-width:400px', 'pointer-events:none'
        ].join(';');
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bg = type === 'error' ? '#c0392b' : type === 'success' ? '#27ae60' : '#2980b9';
    toast.style.cssText = [
        'background:' + bg, 'color:#fff', 'padding:12px 16px',
        'border-radius:6px', 'font-size:0.9rem', 'line-height:1.4',
        'box-shadow:0 2px 8px rgba(0,0,0,0.3)', 'pointer-events:auto',
        'opacity:1', 'transition:opacity 0.3s',
        'display:flex', 'align-items:flex-start', 'gap:10px'
    ].join(';');

    const msgSpan = document.createElement('span');
    msgSpan.style.cssText = 'flex:1;';
    msgSpan.textContent = message;

    const closeBtn = document.createElement('button');
    closeBtn.textContent = '\u00d7';
    closeBtn.title = 'Dismiss';
    closeBtn.style.cssText = [
        'background:none', 'border:none', 'color:#fff', 'cursor:pointer',
        'font-size:18px', 'line-height:1', 'padding:0', 'flex-shrink:0', 'opacity:0.8'
    ].join(';');
    closeBtn.onclick = () => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 320); };

    toast.appendChild(msgSpan);
    toast.appendChild(closeBtn);

    // Standard B: errors stay 10 seconds; other types stay 4 seconds
    const duration = type === 'error' ? 10000 : 4000;
    if (type === 'error') console.error('[HarmonyLab Error]', message);

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 320);
    }, duration);
};

// Standard A: Helper to log full API error response body to console
// Usage: await window.logFetchError(response, 'GET', url);
window.logFetchError = async function(response, method, url) {
    let errorBody = '';
    try {
        const clone = response.clone();
        errorBody = JSON.stringify(await clone.json());
    } catch {
        try { errorBody = await response.clone().text(); } catch { errorBody = '(unreadable)'; }
    }
    console.error(`[API Error] ${method || 'GET'} ${url}`, {
        status: response.status,
        statusText: response.statusText,
        body: errorBody
    });
    window.HLDebug?.emit('fetch:error', { method: method || 'GET', url: url, status: response.status });
};
