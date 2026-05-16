import { useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQueryClient } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import { ro } from 'date-fns/locale';
import { X, ExternalLink, Loader2 } from 'lucide-react';
import { useArticle } from '@/api/articles';

interface ArticleArchiveModalProps {
  articleId: string | null;
  onClose: () => void;
}

export default function ArticleArchiveModal({ articleId, onClose }: ArticleArchiveModalProps) {
  const enabled = !!articleId;
  const queryClient = useQueryClient();
  const { data: article, isLoading } = useArticle(articleId ?? '');

  // Fetching the detail auto-marks the article as read on the server; sync
  // the feed list + unread counts when the modal closes so the change shows.
  const handleClose = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['articles', 'list'] });
    queryClient.invalidateQueries({ queryKey: ['articles', 'unread-counts'] });
    onClose();
  }, [onClose, queryClient]);

  // Close on Escape; lock body scroll while open.
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [enabled, handleClose]);

  return (
    <AnimatePresence>
      {enabled && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-6"
          onClick={handleClose}
        >
          <motion.div
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="relative w-full sm:max-w-3xl max-h-[92vh] bg-white dark:bg-gray-900 sm:rounded-2xl rounded-t-2xl shadow-2xl overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-start gap-3 px-5 py-3 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
              <div className="flex-1 min-w-0">
                {article && (
                  <>
                    <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-0.5">
                      <span className="font-semibold">{article.source?.name}</span>
                      <span>•</span>
                      <span>
                        {format(parseISO(article.published_at), "d MMM yyyy 'la' HH:mm", { locale: ro })}
                      </span>
                    </div>
                    <h2 className="font-serif font-bold text-lg sm:text-xl leading-snug text-gray-900 dark:text-white">
                      {article.title}
                    </h2>
                  </>
                )}
                {!article && isLoading && (
                  <div className="h-6 w-2/3 bg-gray-100 dark:bg-gray-800 rounded animate-pulse" />
                )}
              </div>
              <button
                type="button"
                onClick={handleClose}
                aria-label="Închide"
                className="shrink-0 h-9 w-9 rounded-full flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body — scrollable */}
            <div className="flex-1 overflow-y-auto px-5 sm:px-8 py-5">
              {isLoading && (
                <div className="flex items-center justify-center py-16 text-gray-400">
                  <Loader2 className="w-6 h-6 animate-spin" />
                </div>
              )}

              {article && !isLoading && (
                <>
                  {article.content_html ? (
                    <div
                      className="article-content max-w-none"
                      dangerouslySetInnerHTML={{ __html: article.content_html }}
                    />
                  ) : article.content ? (
                    <div className="whitespace-pre-wrap leading-relaxed text-gray-800 dark:text-gray-200">
                      {article.content}
                    </div>
                  ) : (
                    <div className="py-12 text-center text-gray-500 dark:text-gray-400">
                      <p className="mb-2">Acest articol nu are o versiune arhivată.</p>
                      <p className="text-sm">
                        Probabil a fost adăugat înainte ca arhivarea să fie activă, sau pagina sursă a blocat accesul.
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            {article && (
              <div className="sticky bottom-0 z-10 flex items-center justify-between gap-3 px-5 py-3 border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900">
                <span className="text-xs text-gray-400 dark:text-gray-500 truncate">
                  Arhivă locală • {new URL(article.original_url).hostname}
                </span>
                <a
                  href={article.original_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20"
                >
                  <ExternalLink className="w-4 h-4" />
                  Originalul
                </a>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
