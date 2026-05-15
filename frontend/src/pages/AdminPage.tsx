import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { format, parseISO } from 'date-fns';
import { ro } from 'date-fns/locale';
import {
  BarChart3,
  Radio,
  FileText,
  Users,
  RefreshCw,
  ToggleLeft,
  ToggleRight,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { useSources } from '@/api/sources';
import {
  useSyncLogs,
  useAdminUsers,
  useTriggerSync,
  useUpdateSource,
  useUpdateUserRole,
} from '@/api/admin';
import AdminDashboard from '@/components/AdminDashboard';
import { cn } from '@/lib/utils';
import type { NewsSource, SyncLog, User } from '@/types';

type Tab = 'dashboard' | 'sources' | 'logs' | 'users';

const TABS: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'dashboard', label: 'Dashboard',    icon: BarChart3 },
  { id: 'sources',   label: 'Surse',         icon: Radio      },
  { id: 'logs',      label: 'Jurnale sync',  icon: FileText   },
  { id: 'users',     label: 'Utilizatori',   icon: Users      },
];

// ── Sources tab ───────────────────────────────────────────────────────────
function SourcesTab() {
  const { data: sources = [], isLoading } = useSources();
  const { mutate: triggerSync, isPending: isSyncing, variables: syncingId } = useTriggerSync();
  const { mutate: updateSource, isPending: isUpdating } = useUpdateSource();

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="skeleton h-16 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="overflow-x-auto rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
        <table className="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Sursă</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">Tip</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden lg:table-cell">Ultima sincronizare</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Activ</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Acțiuni</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
            {sources.map((source: NewsSource) => (
              <tr key={source.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                <td className="px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{source.name}</p>
                    <a href={source.url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-gray-400 dark:text-gray-500 hover:text-accent-500 transition-colors truncate max-w-[200px] block">
                      {source.url}
                    </a>
                  </div>
                </td>
                <td className="px-4 py-3 hidden md:table-cell">
                  <span className="text-xs font-mono bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded">
                    {source.source_type}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 hidden lg:table-cell">
                  {source.last_sync_at
                    ? format(parseISO(source.last_sync_at), "d MMM 'la' HH:mm", { locale: ro })
                    : '—'}
                </td>
                <td className="px-4 py-3">
                  <span className={cn(
                    'inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full',
                    source.sync_status === 'ok'    ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400' :
                    source.sync_status === 'error' ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400' :
                                                     'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400',
                  )}>
                    <span className={cn(
                      'w-1.5 h-1.5 rounded-full',
                      source.sync_status === 'ok'    ? 'bg-emerald-400' :
                      source.sync_status === 'error' ? 'bg-red-400' :
                                                       'bg-amber-400 animate-pulse-dot',
                    )} />
                    {source.sync_status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => updateSource({ id: source.id, enabled: !source.enabled })}
                    disabled={isUpdating}
                    className="transition-colors"
                    aria-label={source.enabled ? 'Dezactivează' : 'Activează'}
                  >
                    {source.enabled
                      ? <ToggleRight className="w-6 h-6 text-emerald-500 hover:text-emerald-600" />
                      : <ToggleLeft  className="w-6 h-6 text-gray-300 dark:text-gray-600 hover:text-gray-400" />}
                  </button>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => triggerSync(source.id)}
                    disabled={isSyncing && syncingId === source.id}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ml-auto',
                      isSyncing && syncingId === source.id
                        ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-wait'
                        : 'bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-900/40',
                    )}
                  >
                    <RefreshCw className={cn('w-3.5 h-3.5', isSyncing && syncingId === source.id && 'animate-spin')} />
                    Sync
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sources.length === 0 && (
          <div className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
            Nicio sursă configurată.
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sync Logs tab ─────────────────────────────────────────────────────────
function LogsTab() {
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;
  const { data, isLoading } = useSyncLogs({ page, page_size: PAGE_SIZE });
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  const StatusIcon = ({ status }: { status: SyncLog['status'] }) => {
    if (status === 'success') return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
    if (status === 'error')   return <XCircle       className="w-4 h-4 text-red-500" />;
    return <AlertCircle className="w-4 h-4 text-amber-500" />;
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-2">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="skeleton h-12 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="overflow-x-auto rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
        <table className="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Sursă</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Articole adăugate</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden lg:table-cell">Început</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden lg:table-cell">Finalizat</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Eroare</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
            {data?.items.map((log: SyncLog) => (
              <tr key={log.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                <td className="px-4 py-3">
                  <StatusIcon status={log.status} />
                </td>
                <td className="px-4 py-3 text-sm font-medium text-gray-800 dark:text-gray-200">
                  {log.source?.name ?? log.source_id}
                </td>
                <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 hidden md:table-cell">
                  <span className="font-mono font-semibold text-brand-500 dark:text-brand-400">
                    +{log.articles_added}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 hidden lg:table-cell">
                  {format(parseISO(log.started_at), "d MMM HH:mm:ss", { locale: ro })}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400 hidden lg:table-cell">
                  {log.completed_at
                    ? format(parseISO(log.completed_at), "d MMM HH:mm:ss", { locale: ro })
                    : <Loader2 className="w-3.5 h-3.5 animate-spin text-gray-400" />}
                </td>
                <td className="px-4 py-3 text-xs text-red-500 dark:text-red-400 max-w-[200px] truncate">
                  {log.error_message ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!data || data.items.length === 0) && (
          <div className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
            Niciun jurnal de sincronizare.
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <p className="text-gray-500 dark:text-gray-400">Pagina {page} din {totalPages}</p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Anterior
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Următor
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Users tab ─────────────────────────────────────────────────────────────
function UsersTab() {
  const { data: users = [], isLoading } = useAdminUsers();
  const { mutate: updateRole, isPending } = useUpdateUserRole();

  if (isLoading) {
    return (
      <div className="p-6 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton h-14 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="overflow-x-auto rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
        <table className="min-w-full divide-y divide-gray-100 dark:divide-gray-800">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Utilizator</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Email</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Rol</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
            {users.map((user: User) => (
              <tr key={user.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                <td className="px-4 py-3">
                  <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{user.name}</p>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 hidden md:table-cell">
                  {user.email}
                </td>
                <td className="px-4 py-3">
                  <select
                    value={user.role}
                    onChange={(e) => updateRole({ id: user.id, role: e.target.value as 'admin' | 'user' })}
                    disabled={isPending}
                    className={cn(
                      'text-xs font-medium px-2.5 py-1.5 rounded-lg border',
                      'bg-white dark:bg-gray-800',
                      'border-gray-200 dark:border-gray-700',
                      'text-gray-700 dark:text-gray-300',
                      'focus:outline-none focus:border-brand-400',
                      'cursor-pointer',
                    )}
                  >
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && (
          <div className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
            Niciun utilizator.
          </div>
        )}
      </div>
    </div>
  );
}

// ── AdminPage ─────────────────────────────────────────────────────────────
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');

  return (
    <div>
      {/* Page header */}
      <div className="px-6 pt-6 pb-4">
        <h1 className="font-serif text-2xl font-bold text-gray-900 dark:text-white">
          Panou de administrare
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Monitorizare, configurare și management al platformei ABACO News
        </p>
      </div>

      {/* Tab navigation */}
      <div className="px-6 border-b border-gray-100 dark:border-gray-800">
        <div className="flex gap-1">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 rounded-t-xl text-sm font-medium transition-all border-b-2',
                activeTab === id
                  ? 'border-brand-500 text-brand-500 dark:text-brand-400 bg-brand-50/50 dark:bg-brand-900/10'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50',
              )}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === 'dashboard' && <AdminDashboard />}
          {activeTab === 'sources'   && <SourcesTab />}
          {activeTab === 'logs'      && <LogsTab />}
          {activeTab === 'users'     && <UsersTab />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
