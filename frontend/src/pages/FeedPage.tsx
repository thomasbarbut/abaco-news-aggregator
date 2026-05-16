import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useArticles, useFeedSyncStatus, useFeedTriggerSync } from '@/api/articles';
import { useFeedStore } from '@/store/feedStore';
import ArticleList from '@/components/ArticleList';
import apiClient from '@/lib/api';
import type { Article } from '@/types';

export default function FeedPage() {
  const { filters } = useFeedStore();

  // Omit page from filters for the infinite query (page is managed internally)
  const queryFilters = useMemo(() => {
    const { page: _page, ...rest } = filters;
    return rest;
  }, [filters]);

  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    error,
  } = useArticles(queryFilters);

  const allArticles = useMemo<Article[]>(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data],
  );

  const handleLoadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
        <div className="w-12 h-12 rounded-full bg-red-50 dark:bg-red-900/20 flex items-center justify-center mb-4">
          <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="font-serif font-bold text-xl text-gray-800 dark:text-gray-200 mb-2">
          Eroare la încărcare
        </h3>
        <p className="text-gray-500 dark:text-gray-400 text-sm max-w-xs">
          Nu s-au putut încărca articolele. Verifică conexiunea și încearcă din nou.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-6 px-4 py-2 rounded-lg bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition-colors"
        >
          Reîncarcă
        </button>
      </div>
    );
  }

  // Tabs: All news | Newsletters. Driven by filters.category.
  // Newsletter tab also drops the date filter — newsletters land weekly,
  // not daily, so the default "yesterday onwards" filter would hide most.
  const { setFilters } = useFeedStore();
  const todayLocal = (() => {
    const d = new Date(); d.setDate(d.getDate() - 1);
    const y = d.getFullYear(), m = String(d.getMonth()+1).padStart(2,'0'), day = String(d.getDate()).padStart(2,'0');
    return `${y}-${m}-${day}`;
  })();
  const tabs: { id: string; label: string; onClick: () => void }[] = [
    { id: 'news',       label: 'Știri',       onClick: () => setFilters({ category: undefined, date_from: todayLocal }) },
    { id: 'newsletter', label: 'Newsletter',  onClick: () => setFilters({ category: 'newsletter', date_from: undefined, date_to: undefined }) },
  ];
  const activeTabId = filters.category === 'newsletter' ? 'newsletter' : 'news';

  // Per-tab unread counts. For the Știri count, always apply the default
  // date_from (yesterday) so the badge matches what the news tab would
  // show. Newsletter count is unaffected by date (newsletters land weekly).
  const newsCountDateFrom = activeTabId === 'news' ? (filters.date_from || todayLocal) : todayLocal;
  const newsCountDateTo = activeTabId === 'news' ? filters.date_to : undefined;
  const { data: unread } = useQuery<{ news: number; newsletter: number }>({
    queryKey: ['articles', 'unread-counts', newsCountDateFrom, newsCountDateTo],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (newsCountDateFrom) params.set('date_from', newsCountDateFrom);
      if (newsCountDateTo)   params.set('date_to',   newsCountDateTo);
      const qs = params.toString();
      return (await apiClient.get('/articles/unread-counts' + (qs ? '?' + qs : ''))).data;
    },
    staleTime: 10_000,
    refetchOnWindowFocus: true,
  });

  // Manual sync + error indicator for the feed. When a running sync
  // transitions to done, refresh the article list and unread counts so the
  // new content appears without a manual reload.
  const queryClient = useQueryClient();
  const { data: syncStatus } = useFeedSyncStatus();
  const { mutate: triggerSync } = useFeedTriggerSync();
  const isSyncing = !!syncStatus?.in_progress;
  const wasSyncingRef = useRef(false);
  useEffect(() => {
    if (wasSyncingRef.current && !isSyncing) {
      queryClient.invalidateQueries({ queryKey: ['articles', 'list'] });
      queryClient.invalidateQueries({ queryKey: ['articles', 'unread-counts'] });
    }
    wasSyncingRef.current = isSyncing;
  }, [isSyncing, queryClient]);
  const failed = syncStatus?.failed_sources ?? [];
  const hasErrors = failed.length > 0;
  const errorTitle = hasErrors
    ? `Surse cu erori la ultima sincronizare:\n• ${failed.join('\n• ')}`
    : '';

  return (
    <div className="max-w-3xl mx-auto">
      {/* Tabs: news / newsletter */}
      <div className="sticky top-0 z-10 flex items-center gap-1 px-3 sm:px-5 pt-2 pb-1 bg-surface-light/95 dark:bg-surface-dark/95 backdrop-blur-sm border-b border-gray-100 dark:border-gray-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={t.onClick}
            className={
              'h-9 px-4 rounded-t-lg text-sm font-semibold transition-colors border-b-2 -mb-px ' +
              (activeTabId === t.id
                ? 'border-brand-500 text-brand-600 dark:text-brand-400 bg-white/60 dark:bg-gray-900/40'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200')
            }
          >
            {t.label}
            {unread && unread[t.id as 'news' | 'newsletter'] > 0 && (
              <span className="ml-1.5 text-xs opacity-80">({unread[t.id as 'news' | 'newsletter']})</span>
            )}
          </button>
        ))}
        <span className="ml-auto flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
          {!isLoading && data ? `${data.pages[0]?.total.toLocaleString('ro-RO') ?? 0} articole` : ''}
          {hasErrors && (
            <span
              title={errorTitle}
              aria-label={errorTitle}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 font-medium"
            >
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M4.93 19h14.14c1.54 0 2.5-1.67 1.73-3L13.73 4c-.77-1.33-2.7-1.33-3.46 0L3.2 16c-.77 1.33.19 3 1.73 3z" />
              </svg>
              {failed.length}
            </span>
          )}
          <button
            type="button"
            onClick={() => !isSyncing && triggerSync()}
            disabled={isSyncing}
            title={isSyncing ? 'Sincronizare în curs…' : 'Sincronizează sursele'}
            aria-label="Sincronizează sursele"
            className={
              'inline-flex items-center justify-center h-7 w-7 rounded-full transition-colors ' +
              (isSyncing
                ? 'text-brand-500 dark:text-brand-400 cursor-wait'
                : 'text-gray-500 hover:text-brand-600 dark:text-gray-400 dark:hover:text-brand-400 hover:bg-gray-100 dark:hover:bg-gray-800')
            }
          >
            <svg
              className={'w-4 h-4 ' + (isSyncing ? 'animate-spin' : '')}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v6h6M20 20v-6h-6M20 8a8 8 0 0 0-14.93-2M4 16a8 8 0 0 0 14.93 2" />
            </svg>
          </button>
        </span>
      </div>

      <ArticleList
        articles={allArticles}
        isLoading={isLoading}
        isFetchingNextPage={isFetchingNextPage}
        hasNextPage={!!hasNextPage}
        onLoadMore={handleLoadMore}
      />
    </div>
  );
}
