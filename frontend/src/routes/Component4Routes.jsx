import { Route } from 'react-router-dom';
import DashboardPage from '../pages/component4/DashboardPage';
import ForecastPage from '../pages/component4/ForecastPage';
import ExplainableAIPage from '../pages/component4/ExplainableAIPage';
import ResourcePlanningPage from '../pages/component4/ResourcePlanningPage';
import GISPriorityMapPage from '../pages/component4/GISPriorityMapPage';
import TrendAnalysisPage from '../pages/component4/TrendAnalysisPage';
import DistrictDetailsPage from '../pages/component4/DistrictDetailsPage';
import NotificationsPage from '../pages/component4/NotificationsPage';

/**
 * Component 4 child routes (relative paths, for nesting under the MainLayout
 * route). React Router only accepts <Route> / <Fragment> elements as route
 * children, so call it as a function inside <Routes>:
 * `{Component4Routes()}` - not `<Component4Routes />`.
 */
export default function Component4Routes() {
  return (
    <>
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="forecast" element={<ForecastPage />} />
      <Route path="explainable-ai" element={<ExplainableAIPage />} />
      <Route path="resource-planning" element={<ResourcePlanningPage />} />
      <Route path="gis-map" element={<GISPriorityMapPage />} />
      <Route path="trend-analysis" element={<TrendAnalysisPage />} />
      <Route path="district-details" element={<DistrictDetailsPage />} />
      <Route path="early-warning" element={<NotificationsPage />} />
    </>
  );
}
