import axios, { type InternalAxiosRequestConfig, type AxiosError } from 'axios';

const TOKEN_KEY = 'abaco_access_token';

export const getStoredToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setStoredToken = (token: string): void => localStorage.setItem(TOKEN_KEY, token);
export const clearStoredToken = (): void => localStorage.removeItem(TOKEN_KEY);

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request interceptor: attach Authorization header ──────────────────────
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getStoredToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Response interceptor: handle 401 ─────────────────────────────────────
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshComplete(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // On 401: token is invalid/expired. Clear it and bounce to /login.
    // We don't auto-refresh because the backend's /auth/refresh needs a
    // refresh_token in the body and the frontend doesn't store one.
    // Also clear the Zustand persisted auth state — otherwise LoginPage's
    // useEffect sees isAuthenticated=true (from persisted localStorage) and
    // navigates back to '/' immediately, causing an infinite loop.
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      clearStoredToken();
      try {
        localStorage.removeItem('abaco-auth');  // Zustand persist key
      } catch {}
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    return Promise.reject(error);
  },
);

export default apiClient;
