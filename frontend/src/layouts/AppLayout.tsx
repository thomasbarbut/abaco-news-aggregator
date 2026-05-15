import { useState, useCallback } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Newspaper,
  Search,
  Moon,
  Sun,
  LogOut,
  ChevronLeft,
  LayoutDashboard,
  Menu,
  X,
  Rss,
  Settings,
} from 'lucide-react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Avatar from '@radix-ui/react-avatar';
import { useAuth } from '@/hooks/useAuth';
import { useLogout } from '@/api/auth';
import { useFeedStore } from '@/store/feedStore';
import { useAuthStore } from '@/store/authStore';
import FilterSidebar from '@/components/FilterSidebar';
import { cn } from '@/lib/utils';

export default function AppLayout() {
  const navigate = useNavigate();
  const { user, isAdmin, logout: storeLogout } = useAuth();
  const { darkMode, toggleDarkMode, sidebarOpen, setSidebarOpen, filters, setFilters } = useFeedStore();
  const { mutate: logoutMutation } = useLogout();
  const { logout } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchValue, setSearchValue] = useState(filters.search ?? '');

  const handleLogout = useCallback(() => {
    logoutMutation(undefined, {
      onSettled: () => {
        logout();
        navigate('/login');
      },
    });
  }, [logoutMutation, logout, navigate]);

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setFilters({ search: searchValue || undefined });
    },
    [searchValue, setFilters],
  );

  const initials = user?.name
    ? user.name
        .split(' ')
        .slice(0, 2)
        .map((n) => n[0])
        .join('')
        .toUpperCase()
    : '?';

  return (
    <div className="min-h-screen flex flex-col bg-surface-light dark:bg-surface-dark">
      {/* ── Top navigation ─────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 h-14 flex items-center gap-3 px-4 bg-brand-500 shadow-md">
        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-2 shrink-0 mr-2">
          <div className="w-7 h-7 rounded bg-accent-500 flex items-center justify-center">
            <Newspaper className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <span className="font-serif font-bold text-white text-lg tracking-tight hidden sm:block">
            ABACO<span className="text-accent-400"> News</span>
          </span>
        </NavLink>

        {/* Sidebar toggle (desktop) */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="hidden lg:flex items-center justify-center w-8 h-8 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
          aria-label={sidebarOpen ? 'Ascunde bara laterală' : 'Arată bara laterală'}
        >
          {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
        </button>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex-1 max-w-xl">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/50" />
            <input
              type="search"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              placeholder="Caută articole…"
              className={cn(
                'w-full h-9 pl-9 pr-4 rounded-lg text-sm',
                'bg-white/10 text-white placeholder-white/50',
                'border border-white/10 focus:border-white/30 focus:bg-white/15',
                'outline-none transition-all',
              )}
            />
          </div>
        </form>

        <div className="ml-auto flex items-center gap-1">
          {/* Dark mode */}
          <button
            onClick={toggleDarkMode}
            className="w-9 h-9 rounded-lg flex items-center justify-center text-white/70 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Schimbă tema"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Admin link */}
          {isAdmin && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                cn(
                  'w-9 h-9 rounded-lg flex items-center justify-center transition-colors',
                  isActive
                    ? 'bg-accent-500 text-white'
                    : 'text-white/70 hover:text-white hover:bg-white/10',
                )
              }
              aria-label="Panou de administrare"
            >
              <Settings className="w-4 h-4" />
            </NavLink>
          )}

          {/* User menu */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button className="ml-1 flex items-center gap-2 rounded-lg px-2 py-1 text-white/80 hover:bg-white/10 transition-colors outline-none">
                <Avatar.Root className="w-7 h-7 rounded-full overflow-hidden border border-white/20">
                  <Avatar.Fallback className="w-full h-full flex items-center justify-center bg-accent-500 text-white text-xs font-semibold">
                    {initials}
                  </Avatar.Fallback>
                </Avatar.Root>
                <span className="text-sm font-medium hidden sm:block max-w-[120px] truncate">
                  {user?.name?.split(' ')[0] ?? 'Utilizator'}
                </span>
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className={cn(
                  'z-50 min-w-[200px] rounded-xl shadow-xl border',
                  'bg-white dark:bg-gray-900',
                  'border-gray-100 dark:border-gray-800',
                  'p-1 mt-1',
                  'animate-fade-in',
                )}
                align="end"
                sideOffset={8}
              >
                <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-800 mb-1">
                  <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                    {user?.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{user?.email}</p>
                  {user?.role === 'admin' && (
                    <span className="mt-1 inline-flex items-center px-1.5 py-0.5 rounded text-2xs font-semibold bg-accent-100 text-accent-700 dark:bg-accent-900/40 dark:text-accent-400">
                      Admin
                    </span>
                  )}
                </div>
                {isAdmin && (
                  <DropdownMenu.Item
                    onSelect={() => navigate('/admin')}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer outline-none"
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    Administrare
                  </DropdownMenu.Item>
                )}
                <DropdownMenu.Item
                  onSelect={handleLogout}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 cursor-pointer outline-none"
                >
                  <LogOut className="w-4 h-4" />
                  Deconectare
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>

          {/* Mobile menu toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden w-9 h-9 rounded-lg flex items-center justify-center text-white/70 hover:text-white hover:bg-white/10 transition-colors ml-1"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* ── Body ──────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Desktop sidebar */}
        <AnimatePresence initial={false}>
          {sidebarOpen && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 272, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              className="hidden lg:flex flex-col shrink-0 overflow-hidden border-r border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900"
              style={{ width: 272 }}
            >
              <div className="w-[272px] flex flex-col h-full overflow-y-auto">
                <FilterSidebar />
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Mobile filter drawer */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-30 bg-black/40 lg:hidden"
                onClick={() => setMobileMenuOpen(false)}
              />
              <motion.aside
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                className="fixed left-0 top-14 bottom-0 z-40 w-72 bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 overflow-y-auto lg:hidden"
              >
                <FilterSidebar onClose={() => setMobileMenuOpen(false)} />
              </motion.aside>
            </>
          )}
        </AnimatePresence>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto min-w-0">
          <Outlet />
        </main>
      </div>

      {/* Mobile bottom nav */}
      <nav className="lg:hidden sticky bottom-0 z-40 flex items-center border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 safe-bottom">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            cn(
              'flex-1 flex flex-col items-center gap-1 py-3 text-2xs font-medium transition-colors',
              isActive
                ? 'text-brand-500 dark:text-brand-300'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200',
            )
          }
        >
          <Rss className="w-5 h-5" />
          <span>Feed</span>
        </NavLink>
        <NavLink
          to="/?search=true"
          className={({ isActive }) =>
            cn(
              'flex-1 flex flex-col items-center gap-1 py-3 text-2xs font-medium transition-colors',
              isActive
                ? 'text-brand-500 dark:text-brand-300'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200',
            )
          }
        >
          <Search className="w-5 h-5" />
          <span>Caută</span>
        </NavLink>
        {isAdmin && (
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              cn(
                'flex-1 flex flex-col items-center gap-1 py-3 text-2xs font-medium transition-colors',
                isActive
                  ? 'text-brand-500 dark:text-brand-300'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200',
              )
            }
          >
            <LayoutDashboard className="w-5 h-5" />
            <span>Admin</span>
          </NavLink>
        )}
      </nav>
    </div>
  );
}
