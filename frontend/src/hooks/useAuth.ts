import { useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useMe } from '@/api/auth';
import { getStoredToken } from '@/lib/api';

export function useAuth() {
  const { user, token, isAuthenticated, isLoading, setUser, setToken, setLoading, logout } =
    useAuthStore();

  const storedToken = getStoredToken();

  const {
    data: me,
    isLoading: isMeLoading,
    isError: isMeError,
  } = useMe();

  // On mount: if there's a token in localStorage but not in the store, sync it
  useEffect(() => {
    if (storedToken && !token) {
      setToken(storedToken);
    }
  }, [storedToken, token, setToken]);

  // Sync user from /auth/me response
  useEffect(() => {
    if (me) {
      setUser(me);
    }
  }, [me, setUser]);

  // If /auth/me failed and we had a token, the token is invalid
  useEffect(() => {
    if (isMeError && storedToken) {
      logout();
    }
  }, [isMeError, storedToken, logout]);

  // Reflect loading state
  useEffect(() => {
    if (!isMeLoading) {
      setLoading(false);
    }
  }, [isMeLoading, setLoading]);

  return {
    user,
    token,
    isAuthenticated: isAuthenticated || !!me,
    isLoading: isLoading && isMeLoading,
    isAdmin: user?.role === 'admin' || me?.role === 'admin',
    logout,
    setToken,
    setUser,
  };
}
