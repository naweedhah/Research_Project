import { Route } from 'react-router-dom';
import RiskOverview from '../pages/c1/RiskOverview';

// Component 1 (Chanodya). Add C1 pages here.
export const nav = [{ to: '/c1', label: 'Overview', end: true }];

export const routes = <Route path="c1" element={<RiskOverview />} />;
