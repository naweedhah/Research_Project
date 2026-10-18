import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import * as authApi from '../services/component4/authApi';
import { getAccessToken } from '../services/component4/httpClient';
import { getWarningSummary } from '../services/component4/warningApi';

const AppContext = createContext(null);

const DEFAULT_ROLE = 'Decision Support User';

function loadOverrides(userId) {
  if (!userId) return {};
  try {
    return JSON.parse(localStorage.getItem(`fednutri_profile_${userId}`) || '{}');
  } catch {
    return {};
  }
}

export function AppProvider({ children }) {
  const [token, setToken] = useState(() => getAccessToken());
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(() => !!getAccessToken());
  const [overrides, setOverrides] = useState({});
  const [warningSummary, setWarningSummary] = useState(null);
  const [warningLoading, setWarningLoading] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState(null);

  const isAuthenticated = !!token;

  useEffect(() => {
    if (!getAccessToken()) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const me = await authApi.getMe();
        if (!cancelled) setUser(me);
      } catch {
        authApi.logout();
        if (!cancelled) {
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setAuthLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setOverrides(loadOverrides(user?.id));
  }, [user?.id]);

  const refreshWarnings = useCallback(async () => {
    setWarningLoading(true);
    try {
      const summary = await getWarningSummary();
      setWarningSummary(summary);
    } catch {
      setWarningSummary(null);
    } finally {
      setWarningLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!token) {
      setWarningSummary(null);
      return;
    }
    refreshWarnings();
  }, [token, refreshWarnings]);

  const login = useCallback(async (email, password) => {
    const response = await authApi.login(email, password);
    setToken(response.access_token);
    setUser(response.user);
    setAuthLoading(false);
    return response;
  }, []);

  const register = useCallback(
    (name, email, password) => authApi.register(name, email, password),
    []
  );

  const logout = useCallback(() => {
    authApi.logout();
    setToken(null);
    setUser(null);
    setOverrides({});
    setWarningSummary(null);
  }, []);

  const profile = useMemo(
    () => ({
      name: user?.name || '',
      email: user?.email || '',
      role: DEFAULT_ROLE,
      organization: '',
      avatar: null,
      ...overrides,
    }),
    [user, overrides]
  );

  const updateProfile = useCallback(
    (updates) => {
      setOverrides((prev) => {
        const next = { ...prev, ...updates };
        if (user?.id) {
          localStorage.setItem(`fednutri_profile_${user.id}`, JSON.stringify(next));
        }
        return next;
      });
    },
    [user?.id]
  );

  const warningCount = warningSummary?.warning_count ?? 0;

  const value = useMemo(
    () => ({
      isAuthenticated,
      authLoading,
      user,
      login,
      register,
      logout,
      profile,
      updateProfile,
      warningSummary,
      warningCount,
      warningLoading,
      refreshWarnings,
      selectedNotification,
      setSelectedNotification,
      assistantOpen,
      setAssistantOpen,
    }),
    [
      isAuthenticated,
      authLoading,
      user,
      login,
      register,
      logout,
      profile,
      updateProfile,
      warningSummary,
      warningCount,
      warningLoading,
      refreshWarnings,
      selectedNotification,
      assistantOpen,
    ]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
