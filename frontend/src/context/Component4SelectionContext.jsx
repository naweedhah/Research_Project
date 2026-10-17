import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { getDistricts } from '../services/component4/forecastApi';

const STORAGE_KEY = 'component4_selection';
const Component4SelectionContext = createContext(null);

const MONTHS = [
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' },
];

const YEARS = [2026, 2027, 2028, 2029, 2030];

function loadSavedSelection() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // Only treat as active if confirmed on the Forecast page.
    if (
      parsed?.confirmed &&
      parsed?.district &&
      parsed?.year != null &&
      parsed?.month != null
    ) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

export function Component4SelectionProvider({ children }) {
  const saved = loadSavedSelection();
  const [hasSelection, setHasSelection] = useState(Boolean(saved));
  const [district, setDistrictState] = useState(saved?.district || 'Kandy');
  const [year, setYearState] = useState(saved?.year || 2026);
  const [month, setMonthState] = useState(saved?.month || 1);
  const [districts, setDistricts] = useState([]);
  const [districtsLoading, setDistrictsLoading] = useState(true);
  const [districtsError, setDistrictsError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setDistrictsLoading(true);
      setDistrictsError(null);
      try {
        const data = await getDistricts();
        const list = Array.isArray(data)
          ? data
          : Array.isArray(data?.districts)
            ? data.districts
            : [];
        if (cancelled) return;
        setDistricts(list);
        if (hasSelection && list.length && !list.includes(district)) {
          setDistrictState(list[0]);
        }
      } catch (err) {
        if (!cancelled) {
          setDistrictsError(err.message || 'Unable to load districts.');
        }
      } finally {
        if (!cancelled) setDistrictsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!hasSelection) return;
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ district, year, month, confirmed: true })
    );
  }, [district, year, month, hasSelection]);

  const setDistrict = useCallback((value) => {
    setDistrictState(value);
    setHasSelection(true);
  }, []);

  const setYear = useCallback((value) => {
    setYearState(Number(value));
    setHasSelection(true);
  }, []);

  const setMonth = useCallback((value) => {
    setMonthState(Number(value));
    setHasSelection(true);
  }, []);

  const confirmSelection = useCallback(() => {
    setHasSelection(true);
  }, []);

  const selection = useMemo(
    () => ({ district, year, month }),
    [district, year, month]
  );

  const monthLabel =
    MONTHS.find((m) => m.value === month)?.label || String(month);

  const value = useMemo(
    () => ({
      hasSelection,
      district,
      year,
      month,
      monthLabel,
      selection,
      districts,
      districtsLoading,
      districtsError,
      months: MONTHS,
      years: YEARS,
      setDistrict,
      setYear,
      setMonth,
      confirmSelection,
    }),
    [
      hasSelection,
      district,
      year,
      month,
      monthLabel,
      selection,
      districts,
      districtsLoading,
      districtsError,
      setDistrict,
      setYear,
      setMonth,
      confirmSelection,
    ]
  );

  return (
    <Component4SelectionContext.Provider value={value}>
      {children}
    </Component4SelectionContext.Provider>
  );
}

export function useComponent4Selection() {
  const ctx = useContext(Component4SelectionContext);
  if (!ctx) {
    throw new Error(
      'useComponent4Selection must be used within Component4SelectionProvider'
    );
  }
  return ctx;
}

export { MONTHS, YEARS };
