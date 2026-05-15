import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api';
import type { AdminStats, SyncLog, User, PaginatedResponse, NewsSource } from '@/types';
import { sourceKeys } from './sources';

export const adminKeys = {
  stats:   ['admin', 'stats']  as const,
  logs:    ['admin', 'logs']   as const,
  users:   ['admin', 'users']  as const,
};

// ── Admin Sources (all, including disabled) ──────────────────────────────
export function useAdminSources() {
  return useQuery({
    queryKey: ['admin', 'sources'],
    queryFn: async () => {
      const { data } = await apiClient.get<NewsSource[]>('/admin/sources');
      return data;
    },
  });
}

// ── Admin Stats ───────────────────────────────────────────────────────────
export function useAdminStats() {
  return useQuery({
    queryKey: adminKeys.stats,
    queryFn: async () => {
      const { data } = await apiClient.get<AdminStats>('/admin/stats');
      return data;
    },
    refetchInterval: 30_000, // poll every 30s
  });
}

// ── Sync Logs ─────────────────────────────────────────────────────────────
interface SyncLogFilters {
  page?: number;
  page_size?: number;
}

export function useSyncLogs(filters: SyncLogFilters = {}) {
  return useQuery({
    queryKey: [...adminKeys.logs, filters],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<SyncLog>>('/admin/logs', {
        params: { page: filters.page ?? 1, page_size: filters.page_size ?? 50 },
      });
      return data;
    },
  });
}

// ── Admin Users ───────────────────────────────────────────────────────────
export function useAdminUsers() {
  return useQuery({
    queryKey: adminKeys.users,
    queryFn: async () => {
      const { data } = await apiClient.get<User[]>('/admin/users');
      return data;
    },
  });
}

// ── Trigger sync (all or specific source) ────────────────────────────────
export function useTriggerSync() {
  const queryClient = useQueryClient();
  return useMutation<{ message: string }, Error, string | undefined>({
    mutationFn: async (sourceId) => {
      // Backend expects JSON body {source_id: string|null}
      const { data } = await apiClient.post<{ message: string }>(
        '/admin/sync',
        { source_id: sourceId ?? null },
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.stats });
      queryClient.invalidateQueries({ queryKey: adminKeys.logs });
    },
  });
}

// ── Update source (enable/disable) ───────────────────────────────────────
export function useUpdateSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: Partial<NewsSource> & { id: string }) => {
      const { data } = await apiClient.patch<NewsSource>(`/admin/sources/${id}`, patch);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
    },
  });
}

// ── Update user role ──────────────────────────────────────────────────────
export function useUpdateUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, role }: { id: string; role: 'admin' | 'user' }) => {
      const { data } = await apiClient.patch<User>(`/admin/users/${id}/role`, { role });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.users });
    },
  });
}
