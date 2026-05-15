import { useState } from 'react';
import { Activity, Database, RefreshCw, Users, FileText, Server } from 'lucide-react';
import { useAdminStats, useSyncLogs, useTriggerSync, useAdminSources, useAdminUsers, useUpdateUserRole } from '@/api/admin';
import { format, parseISO } from 'date-fns';
import { ro } from 'date-fns/locale';
import type { NewsSource, SyncLog } from '@/types';

type Tab = 'dashboard' | 'sources' | 'logs' | 'users';

// ── Stats cards ───────────────────────────────────────────────────────────
function StatsGrid() {
  const { data: stats, isLoading } = useAdminStats();
  const triggerSync = useTriggerSync();

  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6 animate-pulse">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Total articole</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total_articles.toLocaleString()}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Articole azi</p>
          <p className="text-2xl font-bold text-blue-600">{stats.articles_today}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Surse active</p>
          <p className="text-2xl font-bold text-green-600">{stats.active_sources}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-4">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Sync-uri eşuate</p>
          <p className="text-2xl font-bold text-red-500">{stats.failed_syncs}</p>
        </div>
      </div>

      <div className="flex items-center gap-6 mb-6 p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${stats.db_healthy ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-600 dark:text-gray-300">PostgreSQL</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${stats.redis_healthy ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-600 dark:text-gray-300">Redis</span>
        </div>
        {stats.last_sync_at && (
          <span className="text-xs text-gray-400 ml-auto">
            Ultimul sync: {format(parseISO(stats.last_sync_at), 'dd MMM, HH:mm', { locale: ro })}
          </span>
        )}
        <button
          onClick={() => triggerSync.mutate(undefined)}
          disabled={triggerSync.isPending}
          className="ml-auto inline-flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${triggerSync.isPending ? 'animate-spin' : ''}`} />
          Sync all
        </button>
      </div>
    </>
  );
}

// ── Sources table ─────────────────────────────────────────────────────────
function SourcesTab() {
  const { data: sources, isLoading } = useAdminSources();
  const triggerSync = useTriggerSync();

  if (isLoading) return <div className="text-center py-8 text-gray-400">Se încarcă...</div>;

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-100 dark:border-gray-700">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 dark:bg-gray-700/50 text-left">
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Sursă</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Tip</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Ultimul sync</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Acțiuni</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
          {sources?.map((source: NewsSource) => (
            <tr key={source.id} className="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
              <td className="px-4 py-3">
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{source.name}</p>
                  <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-xs text-gray-400 hover:text-blue-500">
                    {source.url}
                  </a>
                </div>
              </td>
              <td className="px-4 py-3">
                <span className={`text-xs px-2 py-0.5 rounded-full ${source.source_type === 'rss' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'}`}>
                  {source.source_type.toUpperCase()}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className={`inline-flex items-center gap-1.5 text-xs ${source.sync_status === 'ok' ? 'text-green-600' : source.sync_status === 'error' ? 'text-red-500' : 'text-gray-400'}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${source.sync_status === 'ok' ? 'bg-green-500' : source.sync_status === 'error' ? 'bg-red-500' : 'bg-gray-300'}`} />
                  {source.sync_status}
                </span>
              </td>
              <td className="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">
                {source.last_sync_at ? format(parseISO(source.last_sync_at), 'dd MMM HH:mm', { locale: ro }) : '—'}
              </td>
              <td className="px-4 py-3">
                <button
                  onClick={() => triggerSync.mutate(source.id)}
                  disabled={triggerSync.isPending}
                  className="text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50"
                >
                  Sync
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Sync logs ─────────────────────────────────────────────────────────────
function LogsTab() {
  const { data, isLoading } = useSyncLogs({});
  const logs = data?.items ?? [];

  if (isLoading) return <div className="text-center py-8 text-gray-400">Se încarcă...</div>;

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-100 dark:border-gray-700">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 dark:bg-gray-700/50 text-left">
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Sursă</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Articole adăugate</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Durată</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Eroare</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
          {logs.map((log: SyncLog) => {
            const duration = log.completed_at
              ? Math.round((new Date(log.completed_at).getTime() - new Date(log.started_at).getTime()) / 1000)
              : null;
            return (
              <tr key={log.id} className="bg-white dark:bg-gray-800">
                <td className="px-4 py-3 text-gray-900 dark:text-white">{log.source?.name ?? '—'}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${log.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : log.status === 'error' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'}`}>
                    {log.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{log.articles_added}</td>
                <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">
                  {duration !== null ? `${duration}s` : '—'}
                </td>
                <td className="px-4 py-3 text-xs text-red-500 max-w-xs truncate" title={log.error_message ?? undefined}>
                  {log.error_message ?? '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Users table ───────────────────────────────────────────────────────────
function UsersTab() {
  const { data: users, isLoading } = useAdminUsers();
  const updateRole = useUpdateUserRole();

  if (isLoading) return <div className="text-center py-8 text-gray-400">Se încarcă...</div>;

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-100 dark:border-gray-700">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 dark:bg-gray-700/50 text-left">
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Utilizator</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Email</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Rol</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Ultimul login</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
          {users?.map((user: any) => (
            <tr key={user.id} className="bg-white dark:bg-gray-800">
              <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{user.name}</td>
              <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{user.email}</td>
              <td className="px-4 py-3">
                <select
                  value={user.role}
                  onChange={(e) => updateRole.mutate({ id: user.id, role: e.target.value as 'admin' | 'user' })}
                  className="text-xs border border-gray-200 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </td>
              <td className="px-4 py-3 text-xs text-gray-400">
                {user.last_login ? format(parseISO(user.last_login), 'dd MMM yyyy HH:mm', { locale: ro }) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main admin page ───────────────────────────────────────────────────────
export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');

  const tabs: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
    { id: 'dashboard', label: 'Dashboard', icon: <Activity className="w-4 h-4" /> },
    { id: 'sources', label: 'Surse', icon: <Server className="w-4 h-4" /> },
    { id: 'logs', label: 'Loguri sync', icon: <FileText className="w-4 h-4" /> },
    { id: 'users', label: 'Utilizatori', icon: <Users className="w-4 h-4" /> },
  ];

  return (
    <div className="max-w-screen-xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Panou de administrare</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Monitorizare, configurare și management al platformei ABACO News
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-gray-200 dark:border-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'dashboard' && <StatsGrid />}
      {activeTab === 'sources' && <SourcesTab />}
      {activeTab === 'logs' && <LogsTab />}
      {activeTab === 'users' && <UsersTab />}
    </div>
  );
}
