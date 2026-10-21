import { useCallback, useEffect, useRef, useState } from 'react';
import { getMapBoundaries } from '../../services/component4/mapApi';

/**
 * Runs an async fetcher whenever `deps` change. Stale responses are ignored
 * through a cleanup flag. `reload()` re-runs the fetcher manually.
 * Pass `{ enabled: false }` to skip fetching (e.g. waiting for Forecast selection).
 */
export default function useC4Data(fetcher, deps = [], { enabled = true } = {}) {
  const fetcherRef = useRef(fetcher);
  const [state, setState] = useState({ data: null, loading: enabled, error: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, loading: false, error: null });
      return undefined;
    }

    let cancelled = false;
    setState((prev) => ({ data: prev.data, loading: true, error: null }));

    (async () => {
      try {
        const data = await fetcherRef.current();
        if (!cancelled) setState({ data, loading: false, error: null });
      } catch (error) {
        if (!cancelled) setState({ data: null, loading: false, error });
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, enabled]);

  const reload = useCallback(() => setTick((t) => t + 1), []);

  return { ...state, reload };
}

let boundariesPromise = null;

function loadBoundariesOnce() {
  if (!boundariesPromise) {
    boundariesPromise = getMapBoundaries().catch((error) => {
      boundariesPromise = null;
      throw error;
    });
  }
  return boundariesPromise;
}

/** District boundary GeoJSON (large file) is fetched once and shared. */
export function useBoundaries() {
  const [state, setState] = useState({
    boundaries: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    loadBoundariesOnce()
      .then((boundaries) => {
        if (!cancelled) setState({ boundaries, loading: false, error: null });
      })
      .catch((error) => {
        if (!cancelled) setState({ boundaries: null, loading: false, error });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
