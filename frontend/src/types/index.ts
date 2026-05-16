export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}

export interface NewsSource {
  id: string;
  name: string;
  url: string;
  source_type: 'rss' | 'playwright';
  enabled: boolean;
  last_sync_at: string | null;
  sync_status: 'ok' | 'error' | 'pending';
}

export interface Article {
  id: string;
  source_id: string;
  source: NewsSource;
  title: string;
  slug: string;
  summary: string | null;
  // Full body is returned only on the detail endpoint; list responses omit it
  // and surface `has_archive` instead so the UI can show a "view archive" CTA
  // without dragging tens of KB of HTML through every list payload.
  content?: string | null;
  content_html?: string | null;
  has_archive?: boolean;
  original_url: string;
  image_url: string | null;
  author: string | null;
  published_at: string;
  category: string | null;
  tags: string[];
  language: string;
  is_read: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface SyncLog {
  id: string;
  source_id: string;
  source: NewsSource;
  status: 'success' | 'error' | 'partial';
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  articles_added: number;
}

export interface AdminStats {
  total_articles: number;
  articles_today: number;
  active_sources: number;
  failed_syncs: number;
  last_sync_at: string | null;
  redis_healthy: boolean;
  db_healthy: boolean;
}

export interface ArticleFilter {
  source_ids?: string[];
  date_from?: string;
  date_to?: string;
  category?: string;
  is_read?: boolean;
  search?: string;
  page?: number;
  page_size?: number;
}
