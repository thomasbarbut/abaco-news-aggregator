import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import apiClient from '@/lib/api';
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
  const { data: users = [], isLoading, refetch } = useAdminUsers();
  const { mutate: updateRole, isPending } = useUpdateUserRole();

  // Entra ID search + invite
  const [entraQuery, setEntraQuery] = useState('');
  const [entraResults, setEntraResults] = useState<any[]>([]);
  const [entraConfigured, setEntraConfigured] = useState<boolean | null>(null);
  const [entraMsg, setEntraMsg] = useState<string>('');
  const [searching, setSearching] = useState(false);
  const [adding, setAdding] = useState<string | null>(null);

  const searchEntra = async () => {
    setSearching(true);
    try {
      const { data } = await apiClient.get('/admin/users/entra/search', {
        params: { q: entraQuery, top: 20 },
      });
      setEntraConfigured(data.configured);
      setEntraResults(data.users || []);
      setEntraMsg(data.message || '');
    } catch (e: any) {
      setEntraMsg(`Eroare: ${e?.message || 'unknown'}`);
      setEntraResults([]);
    } finally {
      setSearching(false);
    }
  };

  const addFromEntra = async (u: any) => {
    setAdding(u.id);
    try {
      await apiClient.post('/admin/users', {
        microsoft_id: u.id,
        email: u.mail || u.userPrincipalName,
        name: u.displayName,
        role: 'user',
      });
      refetch();
      setEntraResults((prev) => prev.filter((x) => x.id !== u.id));
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Adăugarea a eșuat');
    } finally {
      setAdding(null);
    }
  };

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
    <div className="p-6 space-y-6">
      {/* ── Entra search + invite ── */}
      <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-5">
        <h3 className="text-base font-semibold text-gray-800 dark:text-gray-200 mb-3">
          Adaugă utilizatori din Microsoft Entra ID
        </h3>
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={entraQuery}
            onChange={(e) => setEntraQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') searchEntra(); }}
            placeholder="Caută după nume sau email (lasă gol pentru primii 20)"
            className="flex-1 h-10 px-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
          />
          <button
            onClick={searchEntra}
            disabled={searching}
            className="h-10 px-4 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold disabled:opacity-50"
          >
            {searching ? 'Caut…' : 'Caută'}
          </button>
        </div>

        {entraConfigured === false && (
          <div className="text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 whitespace-pre-wrap">
            {entraMsg}
          </div>
        )}

        {entraResults.length > 0 && (
          <div className="divide-y divide-gray-100 dark:divide-gray-800 border border-gray-100 dark:border-gray-800 rounded-lg mt-2">
            {entraResults.map((u) => (
              <div key={u.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-800 dark:text-gray-200 truncate">{u.displayName}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {u.mail || u.userPrincipalName}{u.jobTitle ? ` · ${u.jobTitle}` : ''}
                  </div>
                </div>
                <button
                  onClick={() => addFromEntra(u)}
                  disabled={adding === u.id}
                  className="h-8 px-3 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {adding === u.id ? 'Adaug…' : 'Adaugă'}
                </button>
              </div>
            ))}
          </div>
        )}

        {entraConfigured === true && entraResults.length === 0 && !searching && (
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            Nicio potrivire. Încearcă alt termen sau lasă gol.
          </div>
        )}
      </div>

      {/* ── Local users table ── */}
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
  // Derive active tab from URL pathname so the sidebar NavLinks work.
  // (Previously activeTab was useState-only and clicking the sidebar links
  //  in AdminLayout only changed the URL, leaving the tab unchanged.)
  const location = useLocation();
  const navigate = useNavigate();
  const tabFromPath: Tab =
    location.pathname.endsWith('/sources') ? 'sources' :
    location.pathname.endsWith('/logs')    ? 'logs' :
    location.pathname.endsWith('/users')   ? 'users' :
    'dashboard';
  const activeTab = tabFromPath;
  const setActiveTab = (t: Tab) => {
    const path = t === 'dashboard' ? '/admin' : `/admin/${t}`;
    navigate(path);
  };

  // Poll sync status every 2s so the user sees "Sync în curs..." live
  const [syncStatus, setSyncStatus] = useState<{
    in_progress: boolean; started_at: number | null; source_id: string | null;
    last_finished_at: number | null; last_result: any;
  } | null>(null);
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const { data } = await apiClient.get('/admin/sync/status');
        if (alive) setSyncStatus(data);
      } catch {}
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  // Auto-sync config (interval + enabled)
  const [syncCfg, setSyncCfg] = useState<{interval_minutes: number; enabled: boolean} | null>(null);
  const [editIntv, setEditIntv] = useState<string>('');
  const [savingCfg, setSavingCfg] = useState(false);
  const loadCfg = async () => {
    try {
      const { data } = await apiClient.get('/admin/sync/config');
      setSyncCfg(data);
      setEditIntv(String(data.interval_minutes));
    } catch {}
  };
  useEffect(() => { loadCfg(); }, []);
  const saveCfg = async (patch: {interval_minutes?: number; enabled?: boolean}) => {
    setSavingCfg(true);
    try {
      const { data } = await apiClient.patch('/admin/sync/config', patch);
      setSyncCfg(data);
      setEditIntv(String(data.interval_minutes));
    } catch (e) {
      console.warn('saveCfg failed', e);
    } finally {
      setSavingCfg(false);
    }
  };

  const elapsedSec =
    syncStatus?.in_progress && syncStatus.started_at
      ? Math.round((Date.now() / 1000) - syncStatus.started_at)
      : 0;

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

        {/* Live sync-in-progress banner */}
        {syncStatus?.in_progress && (
          <div className="mt-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800">
            <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
            <div className="flex-1">
              <div className="text-sm font-semibold text-brand-700 dark:text-brand-300">
                Sincronizare în curs ({elapsedSec}s)
              </div>
              <div className="text-xs text-brand-600 dark:text-brand-400">
                {syncStatus.source_id ? `Sursa: ${syncStatus.source_id.slice(0,8)}…` : 'Toate sursele active'}
              </div>
            </div>
          </div>
        )}

        {/* Auto-sync configuration */}
        {syncCfg && (
          <div className="mt-4 flex flex-wrap items-center gap-3 px-4 py-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={syncCfg.enabled}
                  disabled={savingCfg}
                  onChange={(e) => saveCfg({ enabled: e.target.checked })}
                />
                <div className="w-9 h-5 bg-gray-300 dark:bg-gray-600 peer-checked:bg-brand-500 rounded-full transition-colors peer-disabled:opacity-50">
                  <div className={`w-4 h-4 bg-white rounded-full shadow transform transition-transform ${syncCfg.enabled ? 'translate-x-4' : 'translate-x-0.5'} mt-0.5`} />
                </div>
              </label>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
                Sincronizare automată
              </span>
            </div>
            <span className="text-gray-300 dark:text-gray-600">|</span>
            <span className="text-sm text-gray-600 dark:text-gray-400">la fiecare</span>
            <input
              type="number"
              min={1}
              max={1440}
              value={editIntv}
              disabled={savingCfg || !syncCfg.enabled}
              onChange={(e) => setEditIntv(e.target.value)}
              className="w-16 h-8 px-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm text-center"
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">minute</span>
            <button
              type="button"
              disabled={savingCfg || !syncCfg.enabled || Number(editIntv) === syncCfg.interval_minutes}
              onClick={() => saveCfg({ interval_minutes: Number(editIntv) })}
              className="h-8 px-3 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Salvează
            </button>
            {syncStatus?.last_finished_at && (
              <span className="ml-auto text-xs text-gray-500 dark:text-gray-400">
                Ultima rulare: acum {Math.round((Date.now()/1000) - syncStatus.last_finished_at)}s
              </span>
            )}
          </div>
        )}
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
