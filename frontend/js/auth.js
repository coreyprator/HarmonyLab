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
                console.log('Token refreshed successfully');
                return true;
            } else {
                console.warn('Refresh failed:', response.status);
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
                const refreshed = await this.refreshToken();
                return refreshed;
            }

            // Other error
            this.clearAuth();
            return false;
        } catch (error) {
            console.error('Auth check error:', error);
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
}

// Create global auth instance
window.auth = new Auth();

// Update UI on load
document.addEventListener('DOMContentLoaded', () => {
    if (window.auth.isAuthenticated()) {
        window.auth.updateAuthUI();
    } else {
        window.auth.updateAuthUI();
    }
});
