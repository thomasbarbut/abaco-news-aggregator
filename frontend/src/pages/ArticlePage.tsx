import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { format, parseISO } from 'date-fns';
import { ro } from 'date-fns/locale';
import {
  ArrowLeft,
  ExternalLink,
  BookOpen,
  BookMarked,
  Calendar,
  User,
  Loader2,
  Tag,
} from 'lucide-react';
import { useArticle, useMarkRead, useMarkUnread } from '@/api/articles';
import SourceBadge from '@/components/SourceBadge';
import { cn } from '@/lib/utils';

function ReadingProgressBar() {
  const [progress, setProgress] = useState(0);
  const articleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      const article = articleRef.current;
      if (!article) return;
      const rect = article.getBoundingClientRect();
      const articleHeight = article.scrollHeight;
      const viewportHeight = window.innerHeight;
      const scrolled = Math.max(0, -rect.top);
      const total = articleHeight - viewportHeight;
      if (total <= 0) { setProgress(100); return; }
      setProgress(Math.min(100, (scrolled / total) * 100));
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <>
      <div
        className="reading-progress"
        style={{ width: `${progress}%` }}
        aria-hidden="true"
      />
      <div ref={articleRef} className="sr-only" />
    </>
  );
}

export default function ArticlePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: article, isLoading, error } = useArticle(id ?? '');
  const { mutate: markRead } = useMarkRead();
  const { mutate: markUnread } = useMarkUnread();

  useEffect(() => {
    if (article && !article.is_read) {
      markRead(article.id);
    }
  }, [article?.id, article?.is_read, markRead]);

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-brand-400" />
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 text-center">
        <h2 className="font-serif text-2xl font-bold text-gray-800 dark:text-gray-200 mb-3">
          Articol negăsit
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">
          Articolul solicitat nu există sau a fost șters.
        </p>
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Înapoi la feed
        </button>
      </div>
    );
  }

  return (
    <>
      <ReadingProgressBar />
      <div className="max-w-2xl mx-auto px-4 pb-16">
        {/* Sticky action bar */}
        <motion.div
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          className="sticky top-0 z-10 -mx-4 px-4 py-3 bg-surface-light/95 dark:bg-surface-dark/95 backdrop-blur-sm border-b border-gray-100 dark:border-gray-800 flex items-center gap-3"
        >
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-brand-500 dark:hover:text-brand-300 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Înapoi
          </button>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => article.is_read ? markUnread(article.id) : markRead(article.id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                article.is_read
                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                  : 'bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400',
              )}
            >
              {article.is_read
                ? <><BookMarked className="w-3.5 h-3.5" />Marcat citit</>
                : <><BookOpen className="w-3.5 h-3.5" />Marchează citit</>}
            </button>
            <a
              href={article.original_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-500 text-white text-xs font-medium hover:bg-accent-600 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Articol original</span>
            </a>
          </div>
        </motion.div>

        {/* Article header */}
        <motion.header
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="pt-8 pb-6"
        >
          <div className="flex items-center gap-2 flex-wrap mb-4">
            <SourceBadge name={article.source.name} size="md" />
            {article.category && (
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-md">
                {article.category}
              </span>
            )}
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold leading-tight text-gray-900 dark:text-white text-balance mb-4">
            {article.title}
          </h1>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-gray-500 dark:text-gray-400">
            {article.author && (
              <span className="flex items-center gap-1.5">
                <User className="w-3.5 h-3.5" />
                {article.author}
              </span>
            )}
            <span className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />
              {format(parseISO(article.published_at), "d MMMM yyyy 'la' HH:mm", { locale: ro })}
            </span>
          </div>
        </motion.header>

        {/* Hero image */}
        {article.image_url && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="mb-8 -mx-4 sm:mx-0 sm:rounded-2xl overflow-hidden"
          >
            <img
              src={article.image_url}
              alt={article.title}
              className="w-full max-h-80 object-cover"
              onError={(e) => {
                const parent = (e.currentTarget as HTMLImageElement).parentElement;
                if (parent) parent.style.display = 'none';
              }}
            />
          </motion.div>
        )}

        {/* Summary */}
        {article.summary && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.15 }}
            className="mb-6 pl-4 border-l-4 border-accent-500"
          >
            <p className="text-base text-gray-700 dark:text-gray-300 leading-relaxed italic font-serif">
              {article.summary}
            </p>
          </motion.div>
        )}

        {/* Content */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="article-content"
        >
          {article.content ? (
            <div dangerouslySetInnerHTML={{ __html: article.content }} />
          ) : (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <p className="text-sm mb-4">Conținutul complet nu este disponibil.</p>
              <a
                href={article.original_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                Citește articolul complet
              </a>
            </div>
          )}
        </motion.div>

        {/* Tags */}
        {article.tags.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.25 }}
            className="mt-8 pt-6 border-t border-gray-100 dark:border-gray-800"
          >
            <div className="flex items-center gap-2 flex-wrap">
              <Tag className="w-3.5 h-3.5 text-gray-400" />
              {article.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-xs px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 font-medium"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </motion.div>
        )}

        {/* Source footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="mt-8 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800"
        >
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 font-medium">Sursa articolului</p>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <p className="font-semibold text-sm text-gray-800 dark:text-gray-200">{article.source.name}</p>
              <a
                href={article.source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-accent-500 hover:text-accent-600 transition-colors"
              >
                {article.source.url}
              </a>
            </div>
            <a
              href={article.original_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-500 text-white text-xs font-medium hover:bg-brand-600 transition-colors shrink-0"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Articol original
            </a>
          </div>
        </motion.div>
      </div>
    </>
  );
}
