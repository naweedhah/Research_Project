import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as authApi from '../services/component4/authApi';
import { getAccessToken } from '../services/component4/httpClient';
import { getWarningSummary } from '../services/component4/warningApi';

/* App-wide state: the signed-in user (shared /auth routes) and Component 4's warning summary for the top bar. */
const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [token, setToken] = useState(() => getAccessToken());
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(() => !!getAccessToken());
  const [warningSummary, setWarningSummary] = useState(null);

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    authApi
      .getMe()
      .then((me) => !cancelled && setUser(me))
      .catch(() => {
        authApi.logout();
        if (!cancelled) setToken(null);
      })
      .finally(() => !cancelled && setAuthLoading(false));
    return () => {
      cancelled = true;
    };
  }, [token]);

  const refreshWarnings = useCallback(async () => {
    try {
      setWarningSummary(await getWarningSummary());
    } catch {
      setWarningSummary(null);
    }
  }, []);

  useEffect(() => {
    if (token) refreshWarnings();
  }, [token, refreshWarnings]);

  const login = useCallback(async (email, password) => {
    const data = await authApi.login(email, password);
    setAuthLoading(true);
    setToken(data?.access_token || getAccessToken());
    return data;
  }, []);

  const register = useCallback((name, email, password) => authApi.register(name, email, password), []);

  const logout = useCallback(() => {
    authApi.logout();
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      isAuthenticated: !!token,
      authLoading,
      user,
      profile: { name: user?.name || 'User', email: user?.email || '', role: 'Decision support user' },
      login,
      register,
      logout,
      warningSummary,
      warningCount: warningSummary?.warning_count ?? 0,
      refreshWarnings,
    }),
    [token, authLoading, user, login, register, logout, warningSummary, refreshWarnings]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside AppProvider');
  return ctx;
}
