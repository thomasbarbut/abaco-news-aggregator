import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { ro } from 'date-fns/locale';
import { ExternalLink, BookOpen } from 'lucide-react';
import type { Article } from '@/types';
import SourceBadge from './SourceBadge';
import { cn } from '@/lib/utils';

interface ArticleCardProps {
  article: Article;
  index?: number;
}

function RelativeTime({ dateStr }: { dateStr: string }) {
  try {
    const date = parseISO(dateStr);
    return (
      <time
        dateTime={dateStr}
        title={date.toLocaleString('ro-RO')}
        className="text-gray-400 dark:text-gray-500 text-xs tabular-nums"
      >
        {formatDistanceToNow(date, { addSuffix: true, locale: ro })}
      </time>
    );
  } catch {
    return null;
  }
}

export default function ArticleCard({ article, index = 0 }: ArticleCardProps) {
  const navigate = useNavigate();

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      navigate(`/article/${article.id}`);
    },
    [navigate, article.id],
  );

  const handleOriginalClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.04, 0.4) }}
      onClick={handleClick}
      className={cn(
        'group relative flex gap-4 px-5 py-4 cursor-pointer',
        'border-b border-gray-100 dark:border-gray-800/80',
        'hover:bg-gray-50/80 dark:hover:bg-gray-800/40',
        'transition-colors duration-150',
        article.is_read && 'opacity-60',
      )}
    >
      {/* Read indicator */}
      {!article.is_read && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-accent-500 rounded-r-full" />
      )}

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Meta row */}
        <div className="flex items-center gap-2 flex-wrap mb-1.5">
          <SourceBadge name={article.source.name} />
          {article.category && (
            <span className="text-2xs text-gray-400 dark:text-gray-500 font-medium">
              {article.category}
            </span>
          )}
          <RelativeTime dateStr={article.published_at} />
          {article.is_read && (
            <span className="ml-auto flex items-center gap-1 text-2xs text-gray-400 dark:text-gray-500">
              <BookOpen className="w-3 h-3" />
              Citit
            </span>
          )}
        </div>

        {/* Title */}
        <h2
          className={cn(
            'font-serif font-bold leading-snug mb-1.5 text-balance',
            'text-gray-900 dark:text-white',
            'group-hover:text-brand-500 dark:group-hover:text-brand-300',
            'transition-colors duration-150',
            article.image_url ? 'text-base' : 'text-[15px]',
          )}
        >
          {article.title}
        </h2>

        {/* Summary */}
        {article.summary && (
          <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed line-clamp-2">
            {article.summary}
          </p>
        )}

        {/* Tags */}
        {article.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {article.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="text-2xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Author & external link */}
        <div className="mt-2 flex items-center justify-between">
          {article.author && (
            <span className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[180px]">
              {article.author}
            </span>
          )}
          <a
            href={article.original_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleOriginalClick}
            className={cn(
              'ml-auto flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500',
              'hover:text-accent-500 dark:hover:text-accent-400 transition-colors',
              'opacity-0 group-hover:opacity-100',
            )}
          >
            <ExternalLink className="w-3 h-3" />
            Original
          </a>
        </div>
      </div>

      {/* Thumbnail */}
      {article.image_url && (
        <div className="shrink-0 w-24 h-20 sm:w-32 sm:h-24 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800">
          <img
            src={article.image_url}
            alt=""
            loading="lazy"
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
      )}
    </motion.article>
  );
}
