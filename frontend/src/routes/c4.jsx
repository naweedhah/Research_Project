import { Outlet, Route } from 'react-router-dom';
import { Component4SelectionProvider } from '../context/Component4SelectionContext';
import DashboardPage from '../pages/component4/DashboardPage';
import ForecastPage from '../pages/component4/ForecastPage';
import ExplainableAIPage from '../pages/component4/ExplainableAIPage';
import ResourcePlanningPage from '../pages/component4/ResourcePlanningPage';
import GISPriorityMapPage from '../pages/component4/GISPriorityMapPage';
import TrendAnalysisPage from '../pages/component4/TrendAnalysisPage';
import DistrictDetailsPage from '../pages/component4/DistrictDetailsPage';
import NotificationsPage from '../pages/component4/NotificationsPage';

// Component 4 (Nimshara). Pages from her frontend; the selection (year, month, district) is shared across them.
export const nav = [
  { to: '/c4', label: 'Dashboard', end: true },
  { to: '/c4/forecast', label: 'Forecast' },
  { to: '/c4/gis-map', label: 'GIS risk map' },
  { to: '/c4/resource-planning', label: 'Resource planning' },
  { to: '/c4/early-warning', label: 'Early warning' },
  { to: '/c4/trend-analysis', label: 'Trend analysis' },
  { to: '/c4/explainable-ai', label: 'Explainable AI' },
  { to: '/c4/district-details', label: 'District details' },
];

function C4Layout() {
  return (
    <Component4SelectionProvider>
      <Outlet />
    </Component4SelectionProvider>
  );
}

export const routes = (
  <Route path="c4" element={<C4Layout />}>
    <Route index element={<DashboardPage />} />
    <Route path="forecast" element={<ForecastPage />} />
    <Route path="gis-map" element={<GISPriorityMapPage />} />
    <Route path="resource-planning" element={<ResourcePlanningPage />} />
    <Route path="early-warning" element={<NotificationsPage />} />
    <Route path="trend-analysis" element={<TrendAnalysisPage />} />
    <Route path="explainable-ai" element={<ExplainableAIPage />} />
    <Route path="district-details" element={<DistrictDetailsPage />} />
  </Route>
);
