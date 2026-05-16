import {
  useInfiniteQuery,
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';
import apiClient from '@/lib/api';
import type { Article, ArticleFilter, PaginatedResponse } from '@/types';

// ── Keys ──────────────────────────────────────────────────────────────────
export const articleKeys = {
  all: ['articles'] as const,
  lists: () => [...articleKeys.all, 'list'] as const,
  list: (filters: ArticleFilter) => [...articleKeys.lists(), filters] as const,
  details: () => [...articleKeys.all, 'detail'] as const,
  detail: (id: string) => [...articleKeys.details(), id] as const,
};

// ── Infinite article list ─────────────────────────────────────────────────
export function useArticles(filters: Omit<ArticleFilter, 'page'>) {
  return useInfiniteQuery({
    queryKey: articleKeys.list(filters),
    queryFn: async ({ pageParam = 1 }) => {
      const params: Record<string, unknown> = {
        page: pageParam,
        page_size: filters.page_size ?? 20,
      };
      if (filters.source_ids?.length) params.source_ids = filters.source_ids.join(',');
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to)   params.date_to   = filters.date_to;
      if (filters.category)  params.category  = filters.category;
      if (filters.is_read !== undefined) params.is_read = filters.is_read;
      if (filters.search)    params.search    = filters.search;

      const { data } = await apiClient.get<PaginatedResponse<Article>>('/articles', { params });
      return data;
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      const totalPages = Math.ceil(lastPage.total / lastPage.page_size);
      return lastPage.page < totalPages ? lastPage.page + 1 : undefined;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// ── Single article ────────────────────────────────────────────────────────
export function useArticle(id: string) {
  return useQuery({
    queryKey: articleKeys.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.get<Article>(`/articles/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

// ── Feed-side sync (any authenticated user) ───────────────────────────────
export interface FeedSyncStatus {
  in_progress: boolean;
  last_finished_at: number | null; // Unix seconds
  failed_sources: string[];
}

export function useFeedSyncStatus() {
  return useQuery<FeedSyncStatus>({
    queryKey: ['articles', 'sync-status'],
    queryFn: async () => {
      const { data } = await apiClient.get<FeedSyncStatus>('/articles/sync-status');
      return data;
    },
    // While a sync is running we poll faster so the spinner clears promptly.
    refetchInterval: (query) => (query.state.data?.in_progress ? 3_000 : 30_000),
    refetchOnWindowFocus: true,
    staleTime: 5_000,
  });
}

export function useFeedTriggerSync() {
  const queryClient = useQueryClient();
  return useMutation<{ message: string; in_progress?: boolean }, Error, void>({
    mutationFn: async () => {
      const { data } = await apiClient.post<{ message: string; in_progress?: boolean }>(
        '/articles/sync',
      );
      return data;
    },
    onSuccess: () => {
      // Optimistic: mark as in_progress so the spinner shows immediately
      // without waiting for the next poll tick.
      queryClient.setQueryData<FeedSyncStatus | undefined>(
        ['articles', 'sync-status'],
        (old) =>
          old
            ? { ...old, in_progress: true }
            : { in_progress: true, last_finished_at: null, failed_sources: [] },
      );
      // Then re-fetch shortly after to confirm.
      queryClient.invalidateQueries({ queryKey: ['articles', 'sync-status'] });
    },
  });
}

// ── Mark as read ──────────────────────────────────────────────────────────
export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.post(`/articles/${id}/read`);
      return id;
    },
    onSuccess: (id) => {
      // Update the detail cache
      queryClient.setQueryData<Article>(articleKeys.detail(id), (old) =>
        old ? { ...old, is_read: true } : old,
      );
      // Invalidate list so read state refreshes
      queryClient.invalidateQueries({ queryKey: articleKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ['articles', 'unread-counts'] });
    },
  });
}

// ── Mark as unread ────────────────────────────────────────────────────────
export function useMarkUnread() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.post(`/articles/${id}/unread`);
      return id;
    },
    onSuccess: (id) => {
      queryClient.setQueryData<Article>(articleKeys.detail(id), (old) =>
        old ? { ...old, is_read: false } : old,
      );
      queryClient.invalidateQueries({ queryKey: articleKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ['articles', 'unread-counts'] });
    },
  });
}
