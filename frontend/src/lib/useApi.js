import { useCallback, useEffect, useState } from 'react';
import { apiRequest } from '../services/component4/httpClient';

/** GET a backend path; returns { data, error, loading, reload }. Pass path = null to skip. */
export function useApi(path, params) {
  const key = path ? `${path}?${JSON.stringify(params || {})}` : null;
  const [state, setState] = useState({ data: null, error: null, loading: !!path });

  const load = useCallback(async () => {
    if (!path) return;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await apiRequest(path, { params });
      setState({ data, error: null, loading: false });
    } catch (error) {
      setState({ data: null, error, loading: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    load();
  }, [load]);

  return { ...state, reload: load };
}

export const post = (path, body, params) => apiRequest(path, { method: 'POST', body, params });
