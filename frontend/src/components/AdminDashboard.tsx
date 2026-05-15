import { motion } from 'framer-motion';
import { format, parseISO } from 'date-fns';
import { ro } from 'date-fns/locale';
import {
  FileText,
  TrendingUp,
  Radio,
  AlertTriangle,
  RefreshCw,
  Database,
  Zap,
  Clock,
} from 'lucide-react';
import { useAdminStats, useTriggerSync } from '@/api/admin';
import { cn } from '@/lib/utils';

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  description?: string;
  accent?: boolean;
  delay?: number;
}

function StatCard({ icon: Icon, label, value, description, accent, delay = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className={cn(
        'p-5 rounded-2xl border',
        accent
          ? 'bg-brand-500 border-brand-400 text-white'
          : 'bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-800',
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div
          className={cn(
            'w-10 h-10 rounded-xl flex items-center justify-center',
            accent ? 'bg-white/20' : 'bg-brand-50 dark:bg-brand-900/20',
          )}
        >
          <Icon
            className={cn(
              'w-5 h-5',
              accent ? 'text-white' : 'text-brand-500 dark:text-brand-400',
            )}
          />
        </div>
      </div>
      <p
        className={cn(
          'text-3xl font-bold font-mono tabular-nums leading-none mb-1',
          accent ? 'text-white' : 'text-gray-900 dark:text-white',
        )}
      >
        {typeof value === 'number' ? value.toLocaleString('ro-RO') : value}
      </p>
      <p
        className={cn(
          'text-sm font-medium',
          accent ? 'text-blue-200' : 'text-gray-500 dark:text-gray-400',
        )}
      >
        {label}
      </p>
      {description && (
        <p className={cn('text-xs mt-1', accent ? 'text-blue-300' : 'text-gray-400 dark:text-gray-500')}>
          {description}
        </p>
      )}
    </motion.div>
  );
}

interface HealthDotProps {
  healthy: boolean;
  label: string;
}

function HealthDot({ healthy, label }: HealthDotProps) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          'w-2.5 h-2.5 rounded-full',
          healthy ? 'bg-emerald-400' : 'bg-red-400 animate-pulse-dot',
        )}
      />
      <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
      <span
        className={cn(
          'text-xs font-medium px-1.5 py-0.5 rounded-full',
          healthy
            ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400'
            : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400',
        )}
      >
        {healthy ? 'OK' : 'Eroare'}
      </span>
    </div>
  );
}

export default function AdminDashboard() {
  const { data: stats, isLoading, isError, refetch } = useAdminStats();
  const { mutate: triggerSync, isPending: isSyncing } = useTriggerSync();

  if (isLoading) {
    return (
      <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton h-36 rounded-2xl" />
        ))}
      </div>
    );
  }

  if (isError || !stats) {
    return (
      <div className="p-6 text-center text-gray-500 dark:text-gray-400">
        Nu s-au putut încărca statisticile.{' '}
        <button onClick={() => refetch()} className="text-accent-500 hover:underline">
          Reîncarcă
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FileText}
          label="Total articole"
          value={stats.total_articles}
          accent
          delay={0}
        />
        <StatCard
          icon={TrendingUp}
          label="Articole azi"
          value={stats.articles_today}
          description="Publicate în ultimele 24h"
          delay={0.05}
        />
        <StatCard
          icon={Radio}
          label="Surse active"
          value={stats.active_sources}
          description="Surse în sincronizare"
          delay={0.1}
        />
        <StatCard
          icon={AlertTriangle}
          label="Sincronizări eșuate"
          value={stats.failed_syncs}
          description="Necesită atenție"
          delay={0.15}
        />
      </div>

      {/* Health & actions row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Health indicators */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="p-5 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900"
        >
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-brand-400" />
            Stare sistem
          </h3>
          <div className="space-y-3">
            <HealthDot healthy={stats.redis_healthy} label="Redis Cache" />
            <HealthDot healthy={stats.db_healthy}    label="Baza de date" />
          </div>
        </motion.div>

        {/* Sync action */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.25 }}
          className="p-5 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900"
        >
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
            <RefreshCw className="w-4 h-4 text-brand-400" />
            Sincronizare manuală
          </h3>
          {stats.last_sync_at && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mb-4 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              Ultima sincronizare:{' '}
              {format(parseISO(stats.last_sync_at), "d MMM yyyy 'la' HH:mm", { locale: ro })}
            </p>
          )}
          <button
            onClick={() => triggerSync()}
            disabled={isSyncing}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all',
              isSyncing
                ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
                : 'bg-brand-500 text-white hover:bg-brand-600 shadow-sm hover:shadow-md active:scale-95',
            )}
          >
            <RefreshCw className={cn('w-4 h-4', isSyncing && 'animate-spin')} />
            {isSyncing ? 'Se sincronizează…' : 'Sincronizează toate sursele'}
          </button>
        </motion.div>
      </div>

      {/* Recent sync info */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500"
      >
        <Database className="w-3.5 h-3.5" />
        Statisticile se actualizează automat la fiecare 30 de secunde.
      </motion.div>
    </div>
  );
}
