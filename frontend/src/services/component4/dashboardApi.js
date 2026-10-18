import { apiRequest } from './httpClient';

export function getDashboardStatus() {
  return apiRequest('/forecast/dashboard/status');
}

export function getDashboardManifest() {
  return apiRequest('/forecast/dashboard/manifest');
}

export function getDashboardMetadata() {
  return apiRequest('/forecast/dashboard/metadata');
}

export function getDashboardSummaryBySelectedMonth({ year, month, district }) {
  return apiRequest('/forecast/dashboard/summary/by-selected-month', {
    params: { year, month, district },
  });
}
