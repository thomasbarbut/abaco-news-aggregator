import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ArticleFilter } from '@/types';

interface FeedState {
  filters: ArticleFilter;
  hideRead: boolean;
  sidebarOpen: boolean;
  darkMode: boolean;
  setFilters: (filters: Partial<ArticleFilter>) => void;
  resetFilters: () => void;
  setHideRead: (hide: boolean) => void;
  setSidebarOpen: (open: boolean) => void;
  toggleDarkMode: () => void;
}

// YYYY-MM-DD in the user's local timezone for a given Date.
function localDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

// Computed lazily on each store init so the date is actually current.
// We use "since yesterday" (last ~24-48h) as the default rather than
// strict today, because early in a new day sources may not have
// published anything yet and a strict today filter shows an empty feed.
// The "Astăzi" preset in FilterSidebar still gives a strict today-only view.
function defaultFilters(): ArticleFilter {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return {
    page: 1,
    page_size: 20,
    is_read: false,         // hide read articles
    date_from: localDate(yesterday),
  };
}

export const useFeedStore = create<FeedState>()(
  persist(
    (set) => ({
      filters: defaultFilters(),
      hideRead: true,  // Default: hide read articles
      sidebarOpen: true,
      darkMode: false,

      setFilters: (incoming) =>
        set((state) => ({
          filters: { ...state.filters, ...incoming, page: 1 },
        })),

      resetFilters: () =>
        set({ filters: defaultFilters() }),

      setHideRead: (hideRead) =>
        set((state) => ({
          hideRead,
          filters: { ...state.filters, is_read: hideRead ? false : undefined, page: 1 },
        })),

      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),

      toggleDarkMode: () =>
        set((state) => {
          const next = !state.darkMode;
          if (next) {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
          return { darkMode: next };
        }),
    }),
    {
      name: 'abaco-feed',
      partialize: (state) => ({
        hideRead: state.hideRead,
        sidebarOpen: state.sidebarOpen,
        darkMode: state.darkMode,
      }),
    },
  ),
);
