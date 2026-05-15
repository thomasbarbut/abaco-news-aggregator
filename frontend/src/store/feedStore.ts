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

const DEFAULT_FILTERS: ArticleFilter = {
  page: 1,
  page_size: 20,
  is_read: false,  // Default: only show unread articles
};

export const useFeedStore = create<FeedState>()(
  persist(
    (set) => ({
      filters: DEFAULT_FILTERS,
      hideRead: true,  // Default: hide read articles
      sidebarOpen: true,
      darkMode: false,

      setFilters: (incoming) =>
        set((state) => ({
          filters: { ...state.filters, ...incoming, page: 1 },
        })),

      resetFilters: () =>
        set({ filters: DEFAULT_FILTERS }),

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
