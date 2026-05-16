import { useCallback, useMemo } from 'react';
import { useArticles } from '@/api/articles';
import { useFeedStore } from '@/store/feedStore';
import ArticleList from '@/components/ArticleList';
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
  const { setFilters } = useFeedStore();
  const tabs: { id: string; label: string; category: string | undefined }[] = [
    { id: 'news',       label: 'Știri',       category: undefined  },
    { id: 'newsletter', label: 'Newsletter',  category: 'newsletter' },
  ];
  const activeTabId = filters.category === 'newsletter' ? 'newsletter' : 'news';

  return (
    <div className="max-w-3xl mx-auto">
      {/* Tabs: news / newsletter */}
      <div className="sticky top-0 z-10 flex items-center gap-1 px-3 sm:px-5 pt-2 pb-1 bg-surface-light/95 dark:bg-surface-dark/95 backdrop-blur-sm border-b border-gray-100 dark:border-gray-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setFilters({ category: t.category })}
            className={
              'h-9 px-4 rounded-t-lg text-sm font-semibold transition-colors border-b-2 -mb-px ' +
              (activeTabId === t.id
                ? 'border-brand-500 text-brand-600 dark:text-brand-400 bg-white/60 dark:bg-gray-900/40'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200')
            }
          >
            {t.label}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">
          {!isLoading && data ? `${data.pages[0]?.total.toLocaleString('ro-RO') ?? 0} articole` : ''}
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
