import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { auth } from '../api/endpoints';
import { invalidateCsrf } from '../api/client';

interface AuthState {
  authenticated: boolean;
  authEnabled:   boolean;
  loading:       boolean;
}

interface AuthContextValue extends AuthState {
  login:   (username: string, password: string) => Promise<void>;
  logout:  () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    authenticated: false,
    authEnabled:   true,
    loading:       true,
  });

  const refresh = useCallback(async () => {
    try {
      const data = await auth.me();
      setState({ authenticated: data.authenticated, authEnabled: data.auth_enabled, loading: false });
    } catch {
      setState((s) => ({ ...s, loading: false }));
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    await auth.login(username, password);
    await refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await auth.logout();
    invalidateCsrf();
    setState((s) => ({ ...s, authenticated: false }));
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}
