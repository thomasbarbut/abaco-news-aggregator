import { useState, useCallback } from 'react';
import { RotateCcw, Eye, EyeOff, ChevronDown, ChevronRight, Search } from 'lucide-react';
import { useSources } from '@/api/sources';
import { useFeedStore } from '@/store/feedStore';
import { cn } from '@/lib/utils';

const CATEGORIES = [
  'Business',
  'Juridic',
  'Startup',
  'Finanțe',
  'Imobiliare',
  'Tehnologie',
  'Energie',
  'Agricultură',
];

interface FilterSidebarProps {
  onClose?: () => void;
}

export default function FilterSidebar({ onClose }: FilterSidebarProps) {
  const { data: sources = [], isLoading: sourcesLoading } = useSources();
  const { filters, setFilters, resetFilters, hideRead, setHideRead } = useFeedStore();
  const [sourcesExpanded, setSourcesExpanded] = useState(true);
  const [sourceSearch, setSourceSearch] = useState('');

  const selectedSourceIds = filters.source_ids ?? [];

  const toggleSource = useCallback(
    (id: string) => {
      const next = selectedSourceIds.includes(id)
        ? selectedSourceIds.filter((s) => s !== id)
        : [...selectedSourceIds, id];
      setFilters({ source_ids: next.length > 0 ? next : undefined });
      onClose?.();
    },
    [selectedSourceIds, setFilters, onClose],
  );

  const handleCategoryChange = useCallback(
    (cat: string) => {
      setFilters({ category: filters.category === cat ? undefined : cat });
      onClose?.();
    },
    [filters.category, setFilters, onClose],
  );

  const handleReset = useCallback(() => {
    resetFilters();
    setSourceSearch('');
    onClose?.();
  }, [resetFilters, onClose]);

  const filteredSources = sources.filter((s) =>
    s.name.toLowerCase().includes(sourceSearch.toLowerCase()),
  );

  const hasActiveFilters =
    (selectedSourceIds.length > 0) ||
    !!filters.category ||
    !!filters.date_from ||
    !!filters.date_to ||
    hideRead;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-gray-100 dark:border-gray-800">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Filtre</h2>
        {hasActiveFilters && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1 text-xs text-accent-500 hover:text-accent-600 font-medium transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            Resetează
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {/* Hide read toggle */}
        <div className="px-4 py-3">
          <button
            onClick={() => setHideRead(!hideRead)}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all',
              hideRead
                ? 'bg-brand-500 text-white shadow-sm'
                : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700',
            )}
          >
            {hideRead ? <EyeOff className="w-4 h-4 shrink-0" /> : <Eye className="w-4 h-4 shrink-0" />}
            {hideRead ? 'Ascunde citite' : 'Arată toate'}
            {hideRead && (
              <span className="ml-auto text-xs font-normal opacity-80">activ</span>
            )}
          </button>
        </div>

        {/* Category filter */}
        <div className="px-4 py-2">
          <p className="text-2xs font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-2 px-1">
            Categorie
          </p>
          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => handleCategoryChange(cat)}
                className={cn(
                  'px-2.5 py-1 rounded-lg text-xs font-medium transition-all',
                  filters.category === cat
                    ? 'bg-accent-500 text-white shadow-sm'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700',
                )}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Date range */}
        <div className="px-4 py-3">
          <p className="text-2xs font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500 mb-2 px-1">
            Interval dată
          </p>
          <div className="flex flex-col gap-2">
            <div>
              <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">De la</label>
              <input
                type="date"
                value={filters.date_from ?? ''}
                onChange={(e) => setFilters({ date_from: e.target.value || undefined })}
                className={cn(
                  'w-full h-8 px-2.5 rounded-lg text-xs',
                  'bg-gray-50 dark:bg-gray-800',
                  'border border-gray-200 dark:border-gray-700',
                  'text-gray-700 dark:text-gray-300',
                  'focus:outline-none focus:border-brand-400 dark:focus:border-brand-500',
                )}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">Până la</label>
              <input
                type="date"
                value={filters.date_to ?? ''}
                onChange={(e) => setFilters({ date_to: e.target.value || undefined })}
                className={cn(
                  'w-full h-8 px-2.5 rounded-lg text-xs',
                  'bg-gray-50 dark:bg-gray-800',
                  'border border-gray-200 dark:border-gray-700',
                  'text-gray-700 dark:text-gray-300',
                  'focus:outline-none focus:border-brand-400 dark:focus:border-brand-500',
                )}
              />
            </div>
          </div>
        </div>

        {/* Sources */}
        <div className="px-4 py-2">
          <button
            onClick={() => setSourcesExpanded(!sourcesExpanded)}
            className="w-full flex items-center gap-2 px-1 mb-2 text-2xs font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500"
          >
            {sourcesExpanded ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
            Surse
            {selectedSourceIds.length > 0 && (
              <span className="ml-auto normal-case tracking-normal font-semibold text-accent-500">
                {selectedSourceIds.length} selectate
              </span>
            )}
          </button>

          {sourcesExpanded && (
            <div className="space-y-0.5">
              {/* Source search */}
              <div className="relative mb-2">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
                <input
                  type="search"
                  value={sourceSearch}
                  onChange={(e) => setSourceSearch(e.target.value)}
                  placeholder="Caută sursă…"
                  className={cn(
                    'w-full h-7 pl-7 pr-2.5 rounded-lg text-xs',
                    'bg-gray-50 dark:bg-gray-800',
                    'border border-gray-200 dark:border-gray-700',
                    'text-gray-700 dark:text-gray-300 placeholder-gray-400',
                    'focus:outline-none focus:border-brand-400 dark:focus:border-brand-500',
                  )}
                />
              </div>

              {sourcesLoading && (
                <>
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="skeleton h-7 rounded-lg" />
                  ))}
                </>
              )}

              {filteredSources.map((source) => {
                const isSelected = selectedSourceIds.includes(source.id);
                return (
                  <label
                    key={source.id}
                    className={cn(
                      'flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer transition-all',
                      isSelected
                        ? 'bg-brand-50 dark:bg-brand-900/20'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-800',
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSource(source.id)}
                      className="w-3.5 h-3.5 rounded border-gray-300 dark:border-gray-600 accent-brand-500 cursor-pointer"
                    />
                    <span
                      className={cn(
                        'text-xs font-medium flex-1 truncate',
                        isSelected
                          ? 'text-brand-600 dark:text-brand-400'
                          : 'text-gray-700 dark:text-gray-300',
                      )}
                    >
                      {source.name}
                    </span>
                    {/* Status dot */}
                    <span
                      className={cn(
                        'w-1.5 h-1.5 rounded-full shrink-0',
                        source.sync_status === 'ok'      ? 'bg-emerald-400' :
                        source.sync_status === 'error'   ? 'bg-red-400' :
                        /* pending */                       'bg-amber-400 animate-pulse-dot',
                      )}
                      title={source.sync_status}
                    />
                  </label>
                );
              })}

              {!sourcesLoading && filteredSources.length === 0 && (
                <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-4">
                  Nicio sursă găsită
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
