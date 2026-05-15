import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Newspaper, Shield, Zap, Globe } from 'lucide-react';
import apiClient, { setStoredToken } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import type { User } from '@/types';

interface MicrosoftIconProps {
  className?: string;
}

function MicrosoftIcon({ className }: MicrosoftIconProps) {
  return (
    <svg className={className} viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="9" height="9" fill="#F25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
      <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
    </svg>
  );
}

const features = [
  { icon: Zap,    label: 'Actualizare în timp real',  desc: 'Știri sincronizate automat din surse de top' },
  { icon: Globe,  label: 'Surse verificate',           desc: 'Business, juridic și startup din România' },
  { icon: Shield, label: 'Acces securizat',             desc: 'Autentificare prin Microsoft Entra ID' },
];

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

  const handleLogin = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<{ auth_url: string; state: string }>('/auth/login');
      // Save state for CSRF protection
      sessionStorage.setItem('oauth_state', data.state);
      window.location.href = data.auth_url;
    } catch {
      setError('Nu s-a putut iniția autentificarea. Verifică conexiunea la internet.');
      setIsLoading(false);
    }
  }, []);

  // ── Local-dev admin/admin login ─────────────────────────────────────────
  const [adminUser, setAdminUser] = useState('admin');
  const [adminPass, setAdminPass] = useState('admin');
  const handleAdminLogin = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.post<{ access_token: string }>(
        '/auth/admin-login',
        { username: adminUser, password: adminPass },
      );
      setToken(data.access_token);
      setStoredToken(data.access_token);
      const { data: me } = await apiClient.get<User>('/auth/me');
      setUser(me);
      navigate('/', { replace: true });
    } catch {
      setError('Login admin a eșuat (folosește admin / admin în dev).');
      setIsLoading(false);
    }
  }, [adminUser, adminPass, navigate, setToken, setUser]);

  return (
    <div className="min-h-screen flex">
      {/* ── Left panel: branding ────────────────────────────────────── */}
      <div className="hidden lg:flex flex-col w-[480px] shrink-0 bg-brand-500 relative overflow-hidden">
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-96 h-96 rounded-full bg-brand-400/30 -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-80 h-80 rounded-full bg-accent-500/20 translate-y-1/2 -translate-x-1/2" />
        <div className="absolute top-1/3 left-1/4 w-48 h-48 rounded-full bg-brand-300/10 blur-2xl" />

        {/* Grid pattern overlay */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        <div className="relative z-10 flex flex-col h-full p-10">
          {/* Logo */}
          <motion.div
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-3"
          >
            <div className="w-10 h-10 rounded-xl bg-accent-500 flex items-center justify-center shadow-lg">
              <Newspaper className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <h1 className="font-serif font-bold text-white text-2xl leading-none">ABACO</h1>
              <p className="text-accent-400 text-xs font-medium tracking-widest uppercase">News</p>
            </div>
          </motion.div>

          {/* Hero text */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="mt-16"
          >
            <h2 className="font-serif text-4xl font-bold text-white leading-tight text-balance">
              Toate știrile de business<br />
              <span className="text-accent-400">într-un singur loc</span>
            </h2>
            <p className="mt-4 text-blue-200 text-base leading-relaxed max-w-sm">
              Agregator inteligent de știri pentru antreprenori, juriști și startup-uri din România.
            </p>
          </motion.div>

          {/* Features */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="mt-12 flex flex-col gap-5"
          >
            {features.map(({ icon: Icon, label, desc }, i) => (
              <motion.div
                key={label}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.35 + i * 0.1 }}
                className="flex items-start gap-4"
              >
                <div className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="w-4 h-4 text-accent-400" />
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">{label}</p>
                  <p className="text-blue-300 text-xs mt-0.5">{desc}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Footer */}
          <div className="mt-auto text-blue-400 text-xs">
            © {new Date().getFullYear()} ABACO. Toate drepturile rezervate.
          </div>
        </div>
      </div>

      {/* ── Right panel: login form ──────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-6 bg-surface-light dark:bg-surface-dark">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="w-full max-w-sm"
        >
          {/* Mobile logo */}
          <div className="flex lg:hidden items-center gap-3 mb-10">
            <div className="w-9 h-9 rounded-lg bg-brand-500 flex items-center justify-center">
              <Newspaper className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <span className="font-serif font-bold text-brand-500 dark:text-brand-300 text-xl">ABACO</span>
              <span className="text-accent-500 font-medium ml-1">News</span>
            </div>
          </div>

          <h2 className="font-serif text-3xl font-bold text-gray-900 dark:text-white mb-1">
            Bun venit
          </h2>
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-8">
            Autentifică-te cu contul tău Microsoft pentru a accesa platforma.
          </p>

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 text-red-700 dark:text-red-400 text-sm"
            >
              {error}
            </motion.div>
          )}

          {/* Local-dev admin login form */}
          <form onSubmit={handleAdminLogin} className="mb-6 space-y-3">
            <div className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold">
              Dev login (admin / admin)
            </div>
            <input
              type="text"
              value={adminUser}
              onChange={(e) => setAdminUser(e.target.value)}
              placeholder="username"
              className="w-full h-11 px-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <input
              type="password"
              value={adminPass}
              onChange={(e) => setAdminPass(e.target.value)}
              placeholder="password"
              className="w-full h-11 px-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-11 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-semibold text-sm transition-colors disabled:opacity-60"
            >
              {isLoading ? 'Se autentifică…' : 'Login as admin'}
            </button>
          </form>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200 dark:border-gray-700" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-3 bg-surface-light dark:bg-surface-dark text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">sau</span>
            </div>
          </div>

          {/* Sign in button */}
          <button
            onClick={handleLogin}
            disabled={isLoading}
            className={`
              w-full flex items-center justify-center gap-3 h-12 rounded-xl
              bg-white dark:bg-gray-800
              border border-gray-200 dark:border-gray-700
              text-gray-800 dark:text-white font-semibold text-sm
              shadow-sm hover:shadow-md
              hover:border-brand-300 dark:hover:border-brand-600
              transition-all duration-200
              disabled:opacity-60 disabled:cursor-not-allowed
              focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2
            `}
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                <span>Se autentifică…</span>
              </>
            ) : (
              <>
                <MicrosoftIcon className="w-5 h-5" />
                <span>Continuă cu Microsoft</span>
              </>
            )}
          </button>

          <p className="mt-8 text-center text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
            Prin autentificare, accepți{' '}
            <a href="#" className="underline hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
              Termenii și Condițiile
            </a>{' '}
            și{' '}
            <a href="#" className="underline hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
              Politica de confidențialitate
            </a>
            .
          </p>
        </motion.div>
      </div>
    </div>
  );
}
