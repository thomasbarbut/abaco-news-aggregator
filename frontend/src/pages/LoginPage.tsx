import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Newspaper } from 'lucide-react';
import apiClient, { setStoredToken } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import type { User } from '@/types';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setToken, setUser, isAuthenticated } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExchanging, setIsExchanging] = useState(false);

  const from = (location.state as { from?: Location })?.from?.pathname ?? '/';

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  // Handle OAuth callback: exchange code for token
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code  = params.get('code');
    const state = params.get('state');

    if (!code || !state || isExchanging) return;

    setIsExchanging(true);
    setIsLoading(true);

    (async () => {
      try {
        const { data } = await apiClient.get<{ access_token: string; token_type: string; expires_in: number }>(
          `/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
        );
        setToken(data.access_token);
        setStoredToken(data.access_token);

        // Fetch user info
        const { data: me } = await apiClient.get<User>('/auth/me');
        setUser(me);
        navigate('/', { replace: true });
      } catch {
        setError('Autentificarea a eșuat. Te rugăm să încerci din nou.');
        setIsLoading(false);
        setIsExchanging(false);
      }
    })();
  }, [location.search, isExchanging, setToken, setUser, navigate]);

  // Username / parolă state
  const [adminUser, setAdminUser] = useState('');
  const [adminPass, setAdminPass] = useState('');
  const handleAdminLogin = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.post<{ access_token: string }>(
        '/auth/login',
        { username: adminUser, password: adminPass },
      );
      setToken(data.access_token);
      setStoredToken(data.access_token);
      const { data: me } = await apiClient.get<User>('/auth/me');
      setUser(me);
      navigate('/', { replace: true });
    } catch {
      setError('Utilizator sau parolă greșite.');
      setIsLoading(false);
    }
  }, [adminUser, adminPass, navigate, setToken, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-surface-light dark:bg-surface-dark">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-sm"
      >
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-10">
          <div className="w-9 h-9 rounded-lg bg-brand-500 flex items-center justify-center">
            <Newspaper className="w-5 h-5 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <span className="font-serif font-bold text-brand-500 dark:text-brand-300 text-xl">ABACO</span>
            <span className="text-accent-500 font-medium ml-1">News</span>
          </div>
        </div>

        {/* Error */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 text-red-700 dark:text-red-400 text-sm text-center"
          >
            {error}
          </motion.div>
        )}

        <form onSubmit={handleAdminLogin} className="space-y-3">
          <input
            type="text"
            autoComplete="username"
            autoFocus
            value={adminUser}
            onChange={(e) => setAdminUser(e.target.value)}
            placeholder="Utilizator"
            className="w-full h-12 px-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-base focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <input
            type="password"
            autoComplete="current-password"
            value={adminPass}
            onChange={(e) => setAdminPass(e.target.value)}
            placeholder="Parolă"
            className="w-full h-12 px-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-base focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-12 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-semibold text-sm transition-colors disabled:opacity-60"
          >
            {isLoading ? 'Se autentifică…' : 'Conectare'}
          </button>
        </form>
      </motion.div>
    </div>
  );
}
