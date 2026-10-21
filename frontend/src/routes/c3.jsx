import { Route } from 'react-router-dom';
import ModelHealth from '../pages/c3/ModelHealth';
import LiveMonitoring from '../pages/c3/LiveMonitoring';
import ModelHistory from '../pages/c3/ModelHistory';
import Results from '../pages/c3/Results';
import ExternalContext from '../pages/c3/ExternalContext';

// Component 3 (Naweed).
export const nav = [
  { to: '/c3', label: 'Model health', end: true },
  { to: '/c3/live', label: 'Live monitoring' },
  { to: '/c3/context', label: 'External context' },
  { to: '/c3/history', label: 'Versions & approvals' },
  { to: '/c3/results', label: 'Experiment results' },
];

export const routes = (
  <Route path="c3">
    <Route index element={<ModelHealth />} />
    <Route path="live" element={<LiveMonitoring />} />
    <Route path="context" element={<ExternalContext />} />
    <Route path="history" element={<ModelHistory />} />
    <Route path="results" element={<Results />} />
  </Route>
);
