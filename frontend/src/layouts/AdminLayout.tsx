import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Radio,
  FileText,
  Users,
  ArrowLeft,
  Newspaper,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const adminNavItems = [
  { to: '/admin',          label: 'Dashboard',   icon: BarChart3, end: true },
  { to: '/admin/sources',  label: 'Surse',        icon: Radio },
  { to: '/admin/logs',     label: 'Jurnale sync', icon: FileText },
  { to: '/admin/users',    label: 'Utilizatori',  icon: Users },
];

export default function AdminLayout() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col bg-surface-light dark:bg-surface-dark">
      {/* Admin top bar */}
      <header className="sticky top-0 z-40 h-14 flex items-center gap-4 px-4 bg-brand-500 shadow-md">
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-7 h-7 rounded bg-accent-500 flex items-center justify-center">
            <Newspaper className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <span className="font-serif font-bold text-white text-lg tracking-tight">
            ABACO <span className="text-accent-400 text-sm font-sans font-medium">Admin</span>
          </span>
        </div>
        <button
          onClick={() => navigate('/')}
          className="ml-auto flex items-center gap-1.5 text-white/70 hover:text-white text-sm font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Înapoi la feed</span>
        </button>
      </header>

      <div className="flex flex-1">
        {/* Admin sidebar */}
        <aside className="w-56 shrink-0 bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 flex flex-col pt-4 pb-6">
          <div className="px-3 mb-2">
            <p className="text-2xs font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 px-3">
              Navigare
            </p>
          </div>
          <nav className="flex flex-col gap-0.5 px-3">
            {adminNavItems.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                    isActive
                      ? 'bg-brand-500 text-white shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white',
                  )
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto px-6">
            <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
              <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
                <Settings className="w-3.5 h-3.5" />
                <span>v1.0.0</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Admin content */}
        <main className="flex-1 overflow-y-auto min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
