import { Route } from 'react-router-dom';
import Recommendations from '../pages/c2/Recommendations';

// Component 2 (Shamiq). Add C2 pages here.
export const nav = [{ to: '/c2', label: 'Recommendations', end: true }];

export const routes = <Route path="c2" element={<Recommendations />} />;
