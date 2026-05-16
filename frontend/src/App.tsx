import { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';
import { useFeedStore } from '@/store/feedStore';
import apiClient from '@/lib/api';
import AppLayout from '@/layouts/AppLayout';
import AdminLayout from '@/layouts/AdminLayout';
import LoginPage from '@/pages/LoginPage';
import FeedPage from '@/pages/FeedPage';
import ArticlePage from '@/pages/ArticlePage';
import AdminPage from '@/pages/AdminPage';

// (Removed dev auto-login — username/password is the only auth path now.)

// ── Auth guard ────────────────────────────────────────────────────────────
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface-light dark:bg-surface-dark flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-3 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500 font-sans">Se încarcă…</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

// ── Admin guard ───────────────────────────────────────────────────────────
function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { isAdmin, isLoading } = useAuth();

  if (isLoading) return null;
  if (!isAdmin) return <Navigate to="/" replace />;

  return <>{children}</>;
}

// ── App ───────────────────────────────────────────────────────────────────
export default function App() {
  const { darkMode } = useFeedStore();

  // Apply dark mode class on initial render from persisted store
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected feed + article */}
      <Route
        path="/"
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<FeedPage />} />
        <Route path="article/:id" element={<ArticlePage />} />
      </Route>

      {/* Protected admin — AdminPage reads the tab from URL pathname */}
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <RequireAdmin>
              <AdminLayout />
            </RequireAdmin>
          </RequireAuth>
        }
      >
        <Route index          element={<AdminPage />} />
        <Route path="sources" element={<AdminPage />} />
        <Route path="logs"    element={<AdminPage />} />
        <Route path="users"   element={<AdminPage />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
