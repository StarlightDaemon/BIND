import { apiFetch } from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Magnet {
  info_hash:      string;
  title:          string;
  hash:           string;
  date:           string;
  magnet:         string;
  collected_date: string;
}

export interface DashboardData {
  magnets:        Magnet[];
  magnet_count:   number;
  display_count:  number;
  system_status:  'online' | 'offline' | 'unknown';
  status_message: string;
}

export interface MagnetsData {
  magnets:     Magnet[];
  query:       string;
  page:        number;
  total_pages: number;
  total_count: number;
}

export interface DbStats {
  total:        number;
  today:        number;
  last_7_days:  number;
  last_30_days: number;
  last_date:    string | null;
}

export interface ScrapeRun {
  run_at:    string;
  result:    'success' | 'failure' | 'empty';
  new_items: number;
  duration:  number;
}

export interface DailyStat {
  date:  string;
  count: number;
}

export interface MetricsData {
  stats:        DbStats;
  runs:         ScrapeRun[];
  success_rate: number | null;
  daily_counts: DailyStat[];
  now:          string;
}

export interface SettingsConfig {
  ABB_URL:                   string;
  SCRAPE_INTERVAL:           string;
  BIND_PROXY:                string;
  BASE_URL:                  string;
  CIRCUIT_BREAKER_THRESHOLD: string;
  CIRCUIT_BREAKER_COOLDOWN:  string;
  BIND_PROXIES:              string;
  BIND_JOB_TIMEOUT:          string;
  BIND_IP_FILTER:            string;
  BIND_AUTH_ENABLED:         string;
}

export interface SettingsData {
  config:        SettingsConfig;
  trackers_text: string;
}

export interface LogsData {
  logs:        string[];
  current_log: string;
  log_file:    string;
  line_count:  number;
}

export interface StatsData {
  system_status:  'online' | 'offline' | 'unknown';
  status_message: string;
  magnet_count:   number;
  recent_magnets: Magnet[];
  server_time:    string;
}

export interface ApiResult {
  ok:      boolean;
  message: string;
}

export interface MeData {
  authenticated: boolean;
  auth_enabled:  boolean;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const auth = {
  me:     () => apiFetch<MeData>('/api/me'),
  login:  (username: string, password: string) =>
    apiFetch<{ ok: boolean }>('/api/login', {
      method: 'POST',
      body:   JSON.stringify({ username, password }),
    }),
  logout: () => apiFetch<{ ok: boolean }>('/api/logout', { method: 'POST' }),
};

// ── Setup ─────────────────────────────────────────────────────────────────────

export const setup = {
  status: () => apiFetch<{ setup_complete: boolean }>('/api/setup/status'),
  create: (username: string, password: string, confirm_password: string) =>
    apiFetch<{ ok: boolean }>('/api/setup', {
      method: 'POST',
      body:   JSON.stringify({ username, password, confirm_password }),
    }),
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

export const dashboard = {
  get:          () => apiFetch<DashboardData>('/api/dashboard'),
  stats:        () => apiFetch<StatsData>('/api/stats'),
  triggerScrape: () => apiFetch<ApiResult>('/api/trigger-scrape', { method: 'POST' }),
};

// ── Magnets ───────────────────────────────────────────────────────────────────

export const magnets = {
  list: (query?: string, page?: number) => {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (page && page > 1) params.set('page', String(page));
    const qs = params.toString();
    return apiFetch<MagnetsData>(`/api/magnets${qs ? `?${qs}` : ''}`);
  },
};

// ── Metrics ───────────────────────────────────────────────────────────────────

export const metrics = {
  get: () => apiFetch<MetricsData>('/api/metrics'),
};

// ── Settings ──────────────────────────────────────────────────────────────────

export const settings = {
  get:      () => apiFetch<SettingsData>('/api/settings'),
  save:     (config: Partial<SettingsConfig>) =>
    apiFetch<ApiResult>('/api/settings', { method: 'POST', body: JSON.stringify(config) }),
  trackers: (trackers: string) =>
    apiFetch<ApiResult>('/api/settings/trackers', {
      method: 'POST',
      body:   JSON.stringify({ trackers }),
    }),
  password: (current_password: string, new_password: string, confirm_new_password: string) =>
    apiFetch<ApiResult>('/api/settings/password', {
      method: 'POST',
      body:   JSON.stringify({ current_password, new_password, confirm_new_password }),
    }),
};

// ── Logs ──────────────────────────────────────────────────────────────────────

export const logs = {
  get: (log: 'security' | 'daemon') =>
    apiFetch<LogsData>(`/api/logs?log=${log}`),
};
