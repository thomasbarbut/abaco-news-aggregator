import { useRef, useEffect, useCallback, useState } from 'react';
import { format, isToday, isYesterday, parseISO } from 'date-fns';
import { ro } from 'date-fns/locale';
import type { Article } from '@/types';
import ArticleCard from './ArticleCard';
import ArticleCardSkeleton from './ArticleCardSkeleton';
import ArticleArchiveModal from './ArticleArchiveModal';
import { Loader2 } from 'lucide-react';

interface ArticleGroup {
  label: string;
  articles: Article[];
}

function groupArticlesByDate(articles: Article[]): ArticleGroup[] {
  const groups: Map<string, Article[]> = new Map();

  for (const article of articles) {
    let label: string;
    try {
      const date = parseISO(article.published_at);
      if (isToday(date)) {
        label = 'Astăzi';
      } else if (isYesterday(date)) {
        label = 'Ieri';
      } else {
        label = format(date, 'EEEE, d MMMM yyyy', { locale: ro });
        // Capitalize first letter
        label = label.charAt(0).toUpperCase() + label.slice(1);
      }
    } catch {
      label = 'Necunoscut';
    }

    if (!groups.has(label)) {
      groups.set(label, []);
    }
    groups.get(label)!.push(article);
  }

  return Array.from(groups.entries()).map(([label, articles]) => ({ label, articles }));
}

interface ArticleListProps {
  articles: Article[];
  isLoading: boolean;
  isFetchingNextPage: boolean;
  hasNextPage: boolean;
  onLoadMore: () => void;
}

export default function ArticleList({
  articles,
  isLoading,
  isFetchingNextPage,
  hasNextPage,
  onLoadMore,
}: ArticleListProps) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [archiveArticleId, setArchiveArticleId] = useState<string | null>(null);

  // IntersectionObserver for infinite scroll
  const observerCallback = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const entry = entries[0];
      if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
        onLoadMore();
      }
    },
    [hasNextPage, isFetchingNextPage, onLoadMore],
  );

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(observerCallback, {
      rootMargin: '200px',
      threshold: 0,
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [observerCallback]);

  // Initial loading state
  if (isLoading) {
    return (
      <div>
        {Array.from({ length: 8 }).map((_, i) => (
          <ArticleCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
        <div className="w-16 h-16 rounded-full bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center mb-4">
          <svg
            className="w-8 h-8 text-brand-300 dark:text-brand-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
            />
          </svg>
        </div>
        <h3 className="font-serif font-bold text-xl text-gray-800 dark:text-gray-200 mb-2">
          Niciun articol găsit
        </h3>
        <p className="text-gray-500 dark:text-gray-400 text-sm max-w-xs">
          Încearcă să modifici filtrele sau revin mai târziu pentru știri noi.
        </p>
      </div>
    );
  }

  const groups = groupArticlesByDate(articles);
  let globalIndex = 0;

  return (
    <div>
      {groups.map(({ label, articles: groupArticles }) => (
        <section key={label}>
          {/* Date group header */}
          <div className="sticky top-0 z-10 flex items-center gap-3 px-5 py-2 bg-surface-light/95 dark:bg-surface-dark/95 backdrop-blur-sm border-b border-gray-100 dark:border-gray-800">
            <div className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
            <span className="text-xs font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 whitespace-nowrap">
              {label}
            </span>
            <div className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
          </div>

          {groupArticles.map((article) => {
            const idx = globalIndex++;
            return (
              <ArticleCard
                key={article.id}
                article={article}
                index={idx}
                onOpenArchive={setArchiveArticleId}
              />
            );
          })}
        </section>
      ))}

      <ArticleArchiveModal
        articleId={archiveArticleId}
        onClose={() => setArchiveArticleId(null)}
      />

      {/* Infinite scroll sentinel */}
      <div ref={sentinelRef} className="h-4" />

      {/* Loading more indicator */}
      {isFetchingNextPage && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-brand-400" />
          <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">Se încarcă mai multe…</span>
        </div>
      )}

      {/* End of feed */}
      {!hasNextPage && articles.length > 0 && (
        <div className="flex items-center justify-center py-10 gap-3">
          <div className="h-px w-16 bg-gray-200 dark:bg-gray-700" />
          <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">
            Ai ajuns la capătul feed-ului
          </span>
          <div className="h-px w-16 bg-gray-200 dark:bg-gray-700" />
        </div>
      )}
    </div>
  );
}
