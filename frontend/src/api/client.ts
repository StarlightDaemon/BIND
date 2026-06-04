let _csrfToken: string | null = null;

async function getCsrfToken(): Promise<string> {
  if (_csrfToken) return _csrfToken;
  const res = await fetch('/api/csrf-token');
  if (!res.ok) throw new Error('Failed to fetch CSRF token');
  const data = await res.json() as { csrf_token: string };
  _csrfToken = data.csrf_token;
  return _csrfToken;
}

export function invalidateCsrf(): void {
  _csrfToken = null;
}

type FetchOptions = Omit<RequestInit, 'headers'> & { headers?: Record<string, string> };

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const method = (options.method ?? 'GET').toUpperCase();
  if (method !== 'GET' && method !== 'HEAD') {
    headers['X-CSRF-Token'] = await getCsrfToken();
  }

  const res = await fetch(path, { ...options, headers });

  if (res.status === 401) {
    invalidateCsrf();
    throw new ApiError(401, 'Authentication required');
  }
  if (res.status === 403) {
    invalidateCsrf();
    throw new ApiError(403, 'Forbidden');
  }
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json() as { error?: string; message?: string };
      message = body.error ?? body.message ?? message;
    } catch { /* ignore parse errors */ }
    throw new ApiError(res.status, message);
  }

  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}
